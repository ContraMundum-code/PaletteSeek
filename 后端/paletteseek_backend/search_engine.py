"""
search_engine.py
----------------
PaletteSeek 后端检索核心，提供三种检索方式：

1. keyword_search(query)         — 关键词 / 标签检索（TF-IDF）
2. color_search(hex_color)       — 颜色相似检索（Delta-E 感知距离）
3. hybrid_search(query, hex)     — 混合检索（加权综合得分）
   得分公式：
       0.4 × 颜色相似度 + 0.3 × 标签匹配度 + 0.3 × 文本相关度

使用方式：
    from search_engine import SearchEngine
    from data_loader import ArtworkDataset

    ds = ArtworkDataset("数据.xlsx")
    engine = SearchEngine(ds)

    results = engine.keyword_search("深蓝 科技感 PPT")
    results = engine.color_search("#1E3A8A")
    results = engine.hybrid_search("科技感 数据大屏", "#1E3A8A")

每条结果为 dict，包含原始 record 字段 + 检索附加字段：
    _score        : float  最终得分 (0~1)
    _color_score  : float  颜色相似度分量
    _text_score   : float  文本相关度分量
    _tag_score    : float  标签匹配度分量
    _rank         : int    排名（从 1 开始）
"""

from __future__ import annotations

import math
import re
from typing import Any

try:
    from .color_utils import (
        classify_hex_family,
        is_valid_hex,
        palette_color_similarity,
        palette_family_score,
        parse_palette_ratio,
    )
    from .data_loader import ArtworkDataset
    from .query_processor import process_query
except ImportError:
    from color_utils import (
        classify_hex_family,
        is_valid_hex,
        palette_color_similarity,
        palette_family_score,
        parse_palette_ratio,
    )
    from data_loader import ArtworkDataset
    from query_processor import process_query


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

# 混合检索权重（必须加和为 1.0）
W_COLOR = 0.40
W_TAG   = 0.30
W_TEXT  = 0.30

# 默认返回结果数量
DEFAULT_TOP_K = 10

# 标签字段（用于标签匹配度计算）
TAG_FIELDS = ["color_tags", "emotion_tags", "style_tags", "use_tags", "color_tags_cn"]


# ---------------------------------------------------------------------------
# 分词
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """
    内部文档分词：按中文标点、顿号、逗号、空格分割。
    例：
        "深蓝色、低饱和、PPT配色" → ["深蓝色", "低饱和", "ppt配色"]
    注意：查询词不走这里，走 _parse_boolean_query。
    """
    if not text:
        return []
    text = text.lower()
    tokens = re.split(r"[，、,\s/／·•\-—]+", text)
    return [t.strip() for t in tokens if t.strip()]


# ---------------------------------------------------------------------------
# 布尔查询解析
# ---------------------------------------------------------------------------
#
# 支持三种语法（大小写不敏感）：
#   AND  ：空格分隔，所有词必须命中，缺一个 → 得分为 0
#   OR   ：关键字 "or" / "或"，组内至少命中一个
#   NOT  ：关键字 "not" / "非"，命中则直接排除（得分为 0）
#
# 例：
#   "深蓝 科技感"              → AND: [深蓝, 科技感]
#   "深蓝 or 蓝紫"             → OR group: [深蓝, 蓝紫]
#   "科技感 not 暖色"          → AND: [科技感], NOT: [暖色]
#   "深蓝 科技感 or 科幻 not 黑色"
#       → AND: [深蓝], OR group: [科技感, 科幻], NOT: [黑色]
# ---------------------------------------------------------------------------

def _parse_boolean_query(query: str) -> dict:
    """
    将查询字符串解析为布尔结构。

    返回：
        {
            'and_terms' : list[str],       # 全部必须命中
            'or_groups' : list[list[str]], # 每组至少命中一个
            'not_terms' : list[str],       # 命中则排除
        }
    """
    tokens = query.lower().strip().split()
    and_terms: list[str] = []
    or_groups: list[list[str]] = []
    not_terms: list[str] = []
    current_or_group: list[str] | None = None
    last_term: str | None = None

    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in ("or", "或"):
            i += 1
            if i < len(tokens):
                nxt = tokens[i]
                if last_term is not None:
                    if current_or_group is None:
                        # 把上一个 AND 词移入新的 OR 组
                        if last_term in and_terms:
                            and_terms.remove(last_term)
                        current_or_group = [last_term, nxt]
                        or_groups.append(current_or_group)
                    else:
                        current_or_group.append(nxt)
                    last_term = nxt
                # last_term is None: OR 开头，忽略
        elif t in ("not", "非"):
            current_or_group = None
            i += 1
            if i < len(tokens):
                not_terms.append(tokens[i])
                last_term = None
        else:
            current_or_group = None   # 新 AND 词中断当前 OR 组
            and_terms.append(t)
            last_term = t
        i += 1

    return {"and_terms": and_terms, "or_groups": or_groups, "not_terms": not_terms}


# ---------------------------------------------------------------------------
# 单词命中检测（含标签字段加权）
# ---------------------------------------------------------------------------

# 标签字段（全部用于检索，emotion_tags / style_tags / use_tags 权重更高）
_HIGH_WEIGHT_FIELDS = ["emotion_tags", "style_tags", "use_tags", "color_tags"]
_ALL_TAG_FIELDS     = ["color_tags", "emotion_tags", "style_tags", "use_tags",
                       "color_tags_cn", "color_chinese_names", "overall_tone", "color_family"]


def _build_doc_text(record: dict) -> tuple[str, str]:
    """
    返回 (tag_text, full_text)：
        tag_text  仅标签字段（emotion_tags / style_tags / use_tags / color_tags 等）
        full_text 全字段（含 title / artist / searchable_text）
    """
    tag_text = " ".join(
        record.get(f, "") for f in _ALL_TAG_FIELDS if record.get(f, "")
    ).lower()
    full_text = record.get("searchable_text", "")
    return tag_text, full_text


def _term_score(term: str, tag_text: str, full_text: str) -> float:
    """
    检测单个词在文档中的命中权重：
        标签字段命中  → 1.0
        全文命中      → 0.5
        未命中        → 0.0
    """
    if term in tag_text:
        return 1.0
    if term in full_text:
        return 0.5
    return 0.0


# ---------------------------------------------------------------------------
# 布尔得分计算
# ---------------------------------------------------------------------------

def _boolean_score(parsed: dict, record: dict) -> float:
    """
    根据解析后的布尔查询计算单条记录的得分（0~1）。

    规则：
        NOT 命中         → 直接返回 0.0（硬排除）
        AND 词缺失       → 直接返回 0.0（硬过滤）
        OR 组全未命中    → 直接返回 0.0
        通过所有过滤     → 返回各命中词权重的平均值
    """
    tag_text, full_text = _build_doc_text(record)

    # 1. NOT 硬排除
    for t in parsed["not_terms"]:
        if _term_score(t, tag_text, full_text) > 0:
            return 0.0

    scores: list[float] = []

    # 2. AND 词（全部必须命中）
    for t in parsed["and_terms"]:
        s = _term_score(t, tag_text, full_text)
        if s == 0.0:
            return 0.0   # 硬过滤
        scores.append(s)

    # 3. OR 组（每组至少命中一个）
    for group in parsed["or_groups"]:
        group_scores = [_term_score(t, tag_text, full_text) for t in group]
        best = max(group_scores)
        if best == 0.0:
            return 0.0   # 组不满足
        scores.append(best)

    # 空查询：返回中性分
    if not scores:
        return 0.5

    return sum(scores) / len(scores)


# ---------------------------------------------------------------------------
# Category-aware 评分（新核心逻辑）
# ---------------------------------------------------------------------------

def _split_field(val: str) -> list[str]:
    """将 '蓝色系、冷色调、蓝灰色' 拆成 ['蓝色系','冷色调','蓝灰色']。"""
    return [t.strip().lower() for t in re.split(r"[、，,]", val) if t.strip()]


def _field_match(query_terms: list[str], field_val: str) -> float:
    """
    AND 语义：query_terms 中每个词都必须在 field_val 的子标签里出现。
    只要缺任意一个词就返回 0.0，避免「清新」命中但「黄色系」不命中仍被放行。
    """
    if not query_terms or not field_val:
        return 0.0
    field_tokens = _split_field(field_val)
    if not field_tokens:
        return 0.0
    hits = 0
    for qt in query_terms:
        qt_lower = qt.lower()
        for ft in field_tokens:
            # 精确匹配 或 查询词是字段 token 的子串（如 "蓝色" in "蓝色系"）
            # 不允许反向（字段 token 是查询词子串），避免 "蓝" 误匹配 "蓝色系"
            if qt_lower == ft or qt_lower in ft:
                hits += 1
                break
    if hits < len(query_terms):
        return 0.0
    return hits / len(query_terms)


_COLOR_FAMILY_TERMS = {
    "蓝色系", "绿色系", "红色系", "橙色系", "黄色系", "紫色系",
    "粉色系", "蓝绿色系", "棕色大地色系", "灰色系", "黑色系", "白色系",
}

_COLOR_FAMILY_ALIASES = {
    "黄色金色系": "黄色系",
    "金色系": "黄色系",
    "棕色系": "棕色大地色系",
    "大地色": "棕色大地色系",
    "土地色": "棕色大地色系",
}


def _canonical_color_family(term: str) -> str:
    term = term.strip()
    return _COLOR_FAMILY_ALIASES.get(term, term if term in _COLOR_FAMILY_TERMS else "")


def _record_dominant_family(record: dict) -> str:
    family = record.get("dominant_color_family") or record.get("color_family", "")
    canonical = _canonical_color_family(str(family))
    if canonical:
        return canonical

    hexes = record.get("palette_hexes", [])
    ratios = record.get("palette_ratios", [])
    if not hexes:
        return ""

    norm: list[float] = []
    for ratio in ratios[:len(hexes)]:
        norm.append(parse_palette_ratio(ratio))
    if len(norm) < len(hexes):
        norm += [0.0] * (len(hexes) - len(norm))
    total = sum(norm)
    if total <= 0:
        norm = [1.0 / len(hexes)] * len(hexes)
    else:
        norm = [val / total for val in norm]

    weights: dict[str, float] = {}
    order: list[str] = []
    for hex_value, ratio in zip(hexes, norm):
        try:
            fam = classify_hex_family(hex_value)
        except Exception:
            continue
        if fam not in weights:
            weights[fam] = 0.0
            order.append(fam)
        weights[fam] += ratio
    return max(order, key=lambda fam: weights[fam]) if order else ""


def _color_terms_score(terms: list[str], record: dict) -> float:
    """
    颜色标签按用户语义做硬筛选：
    - 明确色系词必须等于色卡占比最高的主色系；
    - 色调/饱和度等非主色系词继续用 palette_family_score，但每个词都要命中。
    """
    if not terms:
        return 0.0

    scores: list[float] = []
    dominant_family = _record_dominant_family(record)

    for term in terms:
        canonical = _canonical_color_family(term)
        if canonical:
            if dominant_family != canonical:
                return 0.0
            scores.append(1.0)
            continue

        score = palette_family_score(
            [term],
            record.get("palette_hexes", []),
            record.get("palette_ratios", []),
        )
        if score <= 0.0:
            return 0.0
        scores.append(score)

    return sum(scores) / len(scores)


def _category_score(query_cats: dict, record: dict) -> float:
    """
    按 category 分别评分，最终取各 category 分的平均。

    规则：
      - NOT 命中 → 直接返回 0.0
      - 用户指定了某 category（terms 非空）：
          * 该 category 字段完全不命中 → 该 category 得 0 分（拉低整体）
          * 命中 → 得 0.5~1.0（按命中率）
      - 用户未指定某 category：该 category 不参与评分
      - other_terms：走全文 _term_score 兜底（权重较低）

    最终分 = sum(category_scores) / len(active_categories)
    """
    # NOT 硬排除（文字 + 色板雙重檢查）
    tag_text, full_text = _build_doc_text(record)
    hexes  = record.get("palette_hexes", [])
    ratios = record.get("palette_ratios", [])
    for t in query_cats.get("not_terms", []):
        t_lower = t.lower()
        # 文字層面
        if _term_score(t_lower, tag_text, full_text) > 0:
            return 0.0
        # 色板層面：色系詞且在色板中佔比 > 8% → 排除
        canonical = _canonical_color_family(t)
        if canonical and hexes:
            not_ratio = palette_family_score([t], hexes, ratios)
            if not_ratio > 0.08:
                return 0.0

    category_map = [
        # (query key,          record field(s))
        ("color_terms",   ["color_tags", "color_family", "overall_tone", "color_tags_cn"]),
        ("emotion_terms", ["emotion_tags"]),
        ("style_terms",   ["style_tags"]),
        ("use_terms",     ["use_tags"]),
    ]

    cat_scores: list[float] = []

    for key, fields in category_map:
        terms = query_cats.get(key, [])
        if not terms:
            continue

        if key == "color_terms":
            # 颜色：以调色盘实际 hex + ratio 为准，占比越大权重越高
            if record.get("palette_hexes"):
                score = _color_terms_score(terms, record)
            else:
                # 无色卡数据时回退到文字匹配
                combined = " ".join(record.get(f, "") for f in fields if record.get(f, ""))
                score = _field_match(terms, combined)
        else:
            # 情绪 / 风格 / 场景：文字标签匹配
            combined = " ".join(record.get(f, "") for f in fields if record.get(f, ""))
            score = _field_match(terms, combined)

        if score == 0.0:
            return 0.0
        cat_scores.append(score)

    # other_terms 走全文，但仍遵守 AND：任意指定词缺失就排除
    other_scores: list[float] = []
    for t in query_cats.get("other_terms", []):
        s = _term_score(t.lower(), tag_text, full_text)
        if s == 0.0:
            return 0.0
        other_scores.append(s * 0.6)

    if not cat_scores and not other_scores:
        return 0.5  # 空查询

    all_scores = cat_scores + other_scores
    return sum(all_scores) / len(all_scores) if all_scores else 0.5


# ---------------------------------------------------------------------------
# TF-IDF 索引（用于混合检索的文本相关度分量）
# ---------------------------------------------------------------------------

def _build_tfidf_index(records: list[dict]) -> tuple[dict[str, dict[int, float]], list[int]]:
    N = len(records)
    df_count: dict[str, int] = {}
    doc_tokens: list[list[str]] = []

    for rec in records:
        tokens = _tokenize(rec.get("searchable_text", ""))
        doc_tokens.append(tokens)
        for t in set(tokens):
            df_count[t] = df_count.get(t, 0) + 1

    idf_index: dict[str, dict[int, float]] = {}
    for doc_idx, tokens in enumerate(doc_tokens):
        tf: dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        total = len(tokens) or 1
        for t, count in tf.items():
            tf_val = count / total
            df_val = df_count.get(t, 1)
            idf_val = math.log((N + 1) / (df_val + 1)) + 1
            score = tf_val * idf_val
            if t not in idf_index:
                idf_index[t] = {}
            idf_index[t][doc_idx] = score

    return idf_index, list(range(N))


def _tfidf_scores_for_terms(
    terms: list[str],
    records: list[dict],
    idf_index: dict[str, dict[int, float]],
) -> list[float]:
    """对给定词列表（已拍平，不含布尔关键字）计算 TF-IDF 相关度（0~1）。"""
    if not terms:
        return [0.0] * len(records)
    raw: dict[int, float] = {}
    for t in terms:
        if t in idf_index:
            for doc_idx, score in idf_index[t].items():
                raw[doc_idx] = raw.get(doc_idx, 0.0) + score
    mx = max(raw.values(), default=1e-9)
    result = [0.0] * len(records)
    for idx, score in raw.items():
        result[idx] = score / mx
    return result


# ---------------------------------------------------------------------------
# 主检索类
# ---------------------------------------------------------------------------

class SearchEngine:
    """
    PaletteSeek 检索引擎。

    参数：
        dataset : ArtworkDataset — 已加载的数据集对象
    """

    def __init__(self, dataset: ArtworkDataset) -> None:
        self._dataset = dataset
        self._records = dataset.records
        # 构建 TF-IDF 索引（仅在初始化时构建一次）
        self._idf_index, _ = _build_tfidf_index(self._records)

    # ------------------------------------------------------------------
    # 1. 关键词 / 标签检索
    # ------------------------------------------------------------------

    def keyword_search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        filters: dict[str, str] | None = None,
    ) -> list[dict]:
        """
        关键词 / 标签检索，支持 AND / OR / NOT 布尔语法。

        语法（大小写不敏感）：
            AND ：空格分隔，所有词必须命中
            OR  ：关键字 "or" / "或"，如 "蓝色 or 青色"
            NOT ：关键字 "not" / "非"，如 "蓝色 not 深色调"

        检索字段覆盖：
            emotion_tags / style_tags / use_tags / color_tags
            color_tags_cn / color_chinese_names / overall_tone / color_family
            title / artist / year / searchable_text（全文）

        得分 = 0.6 × 布尔标签得分 + 0.4 × TF-IDF 文本相关度
        """
        query = query.strip()
        records = self._apply_filters(self._records, filters)
        record_set = set(id(r) for r in records)

        if not query:
            scored = [(0.5, rec) for rec in records]
            return self._format_results(scored[:top_k], score_key="keyword")

        # 分类拆词 + 同义词 / Query Mapping 展开
        processed = process_query(query)

        # TF-IDF 辅助（将所有 terms 拍平用于文本相关度）
        all_terms = (
            processed["color_terms"] + processed["emotion_terms"] +
            processed["style_terms"] + processed["use_terms"] +
            processed["other_terms"]
        )
        tfidf_arr = _tfidf_scores_for_terms(
            [t.lower() for t in all_terms], self._records, self._idf_index
        )

        scored = []
        for i, rec in enumerate(self._records):
            if id(rec) not in record_set:
                continue
            cat_s = _category_score(processed, rec)
            if cat_s == 0.0:
                continue
            tfidf_s = tfidf_arr[i]
            # 分类得分主导，TF-IDF 作为同分时的排序辅助
            combined = 0.75 * cat_s + 0.25 * tfidf_s
            result_rec = rec.copy()
            result_rec["_query_info"] = processed
            scored.append((combined, result_rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        return self._format_results(scored[:top_k], score_key="keyword")

    # ------------------------------------------------------------------
    # 2. 颜色相似检索
    # ------------------------------------------------------------------

    def color_search(
        self,
        hex_color: str,
        top_k: int = DEFAULT_TOP_K,
        filters: dict[str, str] | None = None,
    ) -> list[dict]:
        """
        按颜色 HEX 检索最相似调色盘的作品。

        参数：
            hex_color : 用户输入颜色，如 "#1E3A8A" 或 "1e3a8a"
            top_k     : 返回结果数量
            filters   : 可选精确筛选

        抛出：
            ValueError — 如果 hex_color 格式不合法
        """
        hex_color = hex_color.strip()
        if not is_valid_hex(hex_color):
            raise ValueError(f"无效的 HEX 色值：{hex_color!r}，请输入如 #1E3A8A 的格式")

        records = self._apply_filters(self._records, filters)

        scored = []
        for rec in records:
            sim = palette_color_similarity(
                hex_color,
                rec["palette_hexes"],
                rec["palette_ratios"],
            )
            scored.append((sim, rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        return self._format_results(scored[:top_k], score_key="color")

    # ------------------------------------------------------------------
    # 3. 混合检索
    # ------------------------------------------------------------------

    def hybrid_search(
        self,
        query: str = "",
        hex_color: str = "",
        top_k: int = DEFAULT_TOP_K,
        filters: dict[str, str] | None = None,
        w_color: float = W_COLOR,
        w_tag: float = W_TAG,
        w_text: float = W_TEXT,
    ) -> list[dict]:
        """
        混合检索：综合颜色相似度、标签匹配度、文本相关度。

        参数：
            query     : 文本查询，可为空（空时文本和标签分项得 0）
            hex_color : 颜色 HEX，可为空（空时颜色分项得 0）
            top_k     : 返回结果数量
            filters   : 可选精确筛选
            w_color / w_tag / w_text : 权重（必须加和为 1.0，默认 0.4/0.3/0.3）

        注意：query 和 hex_color 至少提供一个，否则抛出 ValueError。
        """
        query = query.strip()
        hex_color = hex_color.strip()

        if not query and not hex_color:
            raise ValueError("混合检索需要至少提供关键词或颜色中的一个")

        if hex_color and not is_valid_hex(hex_color):
            raise ValueError(f"无效的 HEX 色值：{hex_color!r}，请输入如 #1E3A8A 的格式")

        # 权重归一化（以防调用方传入非标准权重）
        w_sum = w_color + w_tag + w_text
        if w_sum <= 0:
            w_color, w_tag, w_text = W_COLOR, W_TAG, W_TEXT
        else:
            w_color /= w_sum
            w_tag   /= w_sum
            w_text  /= w_sum

        records = self._apply_filters(self._records, filters)

        # 分类拆词 + Query Mapping 展开
        processed = process_query(query) if query else None

        if processed:
            all_terms = (
                processed["color_terms"] + processed["emotion_terms"] +
                processed["style_terms"] + processed["use_terms"] +
                processed["other_terms"]
            )
            tfidf_arr = _tfidf_scores_for_terms(
                [t.lower() for t in all_terms], self._records, self._idf_index
            )
        else:
            tfidf_arr = None

        record_set = set(id(r) for r in records)

        scored = []
        for i, rec in enumerate(self._records):
            if id(rec) not in record_set:
                continue

            # 颜色相似度
            if hex_color:
                color_sim = palette_color_similarity(
                    hex_color,
                    rec["palette_hexes"],
                    rec["palette_ratios"],
                )
            else:
                color_sim = 0.0

            # category-aware 标签得分 + TF-IDF 文本相关度
            if processed:
                cat_s    = _category_score(processed, rec)
                if cat_s == 0.0:
                    continue
                tfidf_s  = tfidf_arr[i] if tfidf_arr is not None else 0.0
                tag_sim  = 0.75 * cat_s + 0.25 * tfidf_s
                text_sim = tfidf_s
            else:
                tag_sim  = 0.0
                text_sim = 0.0

            # 综合得分
            final_score = w_color * color_sim + w_tag * tag_sim + w_text * text_sim

            result_rec = rec.copy()
            result_rec["_color_score"] = round(color_sim, 4)
            result_rec["_text_score"]  = round(text_sim, 4)
            result_rec["_tag_score"]   = round(tag_sim, 4)
            scored.append((final_score, result_rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        return self._format_results(scored[:top_k], score_key="hybrid")

    # ------------------------------------------------------------------
    # 辅助：过滤器 & 结果格式化
    # ------------------------------------------------------------------

    def _apply_filters(
        self,
        records: list[dict],
        filters: dict[str, str] | None,
    ) -> list[dict]:
        """
        对记录列表做精确字段过滤。
        filters 格式：{"字段名": "期望值（包含匹配，不区分大小写）"}
        """
        if not filters:
            return records
        result = []
        for rec in records:
            match = True
            for field, value in filters.items():
                field_val = str(rec.get(field, "")).lower()
                if value.lower() not in field_val:
                    match = False
                    break
            if match:
                result.append(rec)
        return result

    def _format_results(
        self,
        scored: list[tuple[float, dict]],
        score_key: str = "score",
    ) -> list[dict]:
        """
        为每条结果添加 _score、_rank 字段，并生成推荐理由文字。
        """
        output = []
        for rank, (score, rec) in enumerate(scored, start=1):
            r = rec.copy()
            r["_score"]      = round(score, 4)
            r["_rank"]       = rank
            r["_score_type"] = score_key
            r["_reason"]     = _generate_reason(r)
            output.append(r)
        return output

    # ------------------------------------------------------------------
    # 便捷接口
    # ------------------------------------------------------------------

    def get_all(self, top_k: int | None = None) -> list[dict]:
        """返回所有作品（不排序），可用于首页展示。"""
        records = self._records if top_k is None else self._records[:top_k]
        return [
            {**rec, "_score": 1.0, "_rank": i + 1, "_score_type": "all", "_reason": ""}
            for i, rec in enumerate(records)
        ]

    def list_filter_options(self) -> dict[str, list[str]]:
        """
        返回各可筛选字段的可用选项（去重排序），用于前端筛选下拉。

        返回格式：
            {
                "overall_tone": ["中明度色调", "低饱和色调", ...],
                "color_family": ["蓝色系", "橙色系", ...],
                "culture"     : ["欧洲", "美洲", ...],
                "classification": ["Painting / Sculpture", ...],
            }
        """
        result: dict[str, list[str]] = {}
        for field in ("overall_tone", "color_family", "culture", "classification"):
            values = sorted(set(
                rec[field] for rec in self._records if rec.get(field, "")
            ))
            result[field] = values
        return result


# ---------------------------------------------------------------------------
# 推荐理由生成
# ---------------------------------------------------------------------------

def _generate_reason(record: dict) -> str:
    """
    根据作品字段自动生成一句话推荐理由。
    优先使用具体的颜色、色调、标签信息，尽量自然。
    """
    parts = []

    # 颜色部分
    color_names = record.get("color_chinese_names", "")
    overall_tone = record.get("overall_tone", "")
    color_family = record.get("color_family", "")

    if color_names:
        first_colors = "、".join(color_names.split("、")[:3])
        parts.append(f"主色包含{first_colors}")

    if overall_tone:
        parts.append(f"整体属于{overall_tone}")

    if color_family:
        parts.append(f"色系偏{color_family}")

    # 情绪 / 场景部分
    emotion = record.get("emotion_tags", "")
    use = record.get("use_tags", "")

    if emotion:
        first_emotion = emotion.split("、")[0].split("，")[0]
        if first_emotion:
            parts.append(f"情绪上{first_emotion}")

    if use:
        first_use = use.split("、")[0].split("，")[0]
        if first_use:
            parts.append(f"适合{first_use}场景")

    if not parts:
        return ""

    return "；".join(parts) + "。"
