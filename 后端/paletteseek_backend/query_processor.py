"""
query_processor.py
------------------
查询预处理：同义词标准化 + 分类拆词 + Query Mapping 按 category 展开

返回结构：
{
    "original":      str,
    "color_terms":   list[str],   # 用于匹配 color_tags / color_family / overall_tone
    "emotion_terms": list[str],   # 用于匹配 emotion_tags
    "style_terms":   list[str],   # 用于匹配 style_tags
    "use_terms":     list[str],   # 用于匹配 use_tags
    "other_terms":   list[str],   # 无法分类，走全文
    "not_terms":     list[str],   # NOT 排除词
    "debug":         dict,        # 调试信息（展开过程）
}
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    import jieba
    _JIEBA_AVAILABLE = True
except ImportError:
    jieba = None
    _JIEBA_AVAILABLE = False


# ── 内置同义词（fallback，Excel 加载优先覆盖） ───────────────────────────────

_DEFAULT_SYNONYM: dict[str, str] = {
    # 繁简常见写法
    "黃色系": "黄色系", "藍色系": "蓝色系", "綠色系": "绿色系",
    "紅色系": "红色系", "橙色系": "橙色系", "紫色系": "紫色系",
    "粉色系": "粉色系", "灰色系": "灰色系", "黑色系": "黑色系",
    "白色系": "白色系", "藍綠色系": "蓝绿色系",
    "黃色": "黄色系", "黄色": "黄色系",
    "黃色調": "黄色系", "黄色调": "黄色系", "黄调": "黄色系",
    "藍色": "蓝色系", "綠色": "绿色系", "绿色": "绿色系",
    "紅色": "红色系", "红色": "红色系",
    "橙色": "橙色系", "紫色": "紫色系", "粉色": "粉色系",
    "灰色": "灰色系", "黑色": "黑色系", "白色": "白色系",
    "棕色大地色系": "棕色大地色系", "黃色金色系": "黄色金色系",
    # 颜色
    "莫兰迪": "低饱和", "莫兰迪色": "低饱和", "高级灰": "低饱和",
    "大地色": "棕色大地色系", "土色": "棕色大地色系", "大地色系": "棕色大地色系",
    "奶油色": "浅色系", "脏色": "低饱和",
    "深藍": "蓝色系", "淺藍": "蓝色系",
    "亮色": "高饱和", "撞色": "高饱和", "明亮": "高明度", "暗沉": "低明度",
    # 情绪
    "高冷": "冷静", "酷": "冷静",
    "治愈": "治愈", "温柔": "温柔", "柔和": "温柔",
    "深邃": "神秘", "神秘感": "神秘",
    "高贵": "优雅", "典雅": "优雅", "端庄": "庄重", "严肃": "庄重",
    "活力": "活力", "生机": "活力", "热烈": "热烈",
    # 风格
    "简约": "极简主义", "简洁": "极简主义", "性冷淡风": "极简主义",
    "怀旧": "古典艺术", "老式": "古典艺术", "年代感": "古典艺术",
    "古风": "东方艺术", "中国风": "东方艺术", "中式": "东方艺术",
    "科幻": "科技视觉", "未来主义": "科技视觉",
    "赛博": "赛博朋克", "霓虹": "赛博朋克",
    "自然": "自然主题", "田园": "自然主题", "森系": "自然主题",
    "小清新": "自然主题",
    "日系": "浮世绘", "日风": "浮世绘", "和风": "浮世绘",
    "工业": "现代艺术",
    # 使用场景
    "幻灯片": "学术汇报", "演示": "学术汇报",
    "ppt": "学术汇报", "簡報": "学术汇报", "简报": "学术汇报",
    "做ppt": "学术汇报", "做PPT": "学术汇报",
    "汇报": "学术汇报", "论文": "学术汇报",
    "品牌": "品牌视觉", "logo": "品牌视觉",
    "界面": "UI设计", "app": "UI设计",
    "网站": "网页设计",
    "包装": "包装设计",
    "电影海报": "海报设计", "宣传海报": "海报设计",
    "插图": "插画创作",
    "文创": "文创设计",
    "社交": "社交媒体封面",
    # 口语复合词 → 归类
    "有质感": "高级感", "质感": "高级感", "高端": "高级感",
    "高级": "高级感", "精致": "精致", "轻奢感": "轻奢",
    "豪华": "奢华风格", "华丽": "奢华风格",
    "清爽": "清新",
    "北欧": "极简主义",
    "复古风": "复古",
    "复古风格": "复古",
    "清爽风格": "清爽",
    "有质感风": "有质感",
    "科技风": "科技感",
    "科技感": "科技感",
    "答辩PPT": "学术汇报",
    "答辩": "学术汇报",
    "PPT": "学术汇报",
    "数据大屏": "数据大屏",
    "品牌设计": "品牌视觉",
    "UI界面": "UI设计",
}

# ── 纯规则短语映射（缺省值，Excel 优先覆盖） ─────────────────────────────

_DEFAULT_QUERY_MAPPING: dict[str, dict[str, list[str]]] = {
    "复古": {
        "color": ["暖色调"],
        "emotion": ["怀旧"],
    },
    "复古风": {
        "color": ["暖色调"],
        "emotion": ["怀旧"],
    },
    "清爽": {
        "color": ["高明度"],
        "emotion": ["清爽"],
    },
    "清新": {
        "color": ["高明度"],
        "emotion": ["清新"],
    },
    "有质感": {
        "color": ["低饱和"],
        "emotion": ["高级"],
        "style": ["现代艺术"],
    },
    "高级感": {
        "color": ["低饱和"],
        "emotion": ["高级"],
    },
    "深蓝色": {
        "color": ["蓝色系", "深色调"],
    },
    "深蓝": {
        "color": ["蓝色系", "深色调"],
    },
    "蓝色": {
        "color": ["蓝色系"],
    },
    "浅蓝色": {
        "color": ["蓝色系", "浅色调", "高明度"],
    },
    "蓝绿色": {
        "color": ["蓝绿色系", "蓝绿色", "浅色调"],
    },
    "青色": {
        "color": ["蓝绿色系", "蓝绿色"],
    },
    "科技感": {
        "color": ["冷色调"],
        "emotion": ["理性"],
        "style": ["现代艺术"],
    },
    "赛博感": {
        "color": ["冷色调"],
        "emotion": ["理性"],
        "style": ["前卫艺术"],
    },
    "答辩PPT": {
        "style": ["视觉传达"],
        "emotion": ["理性"],
        "use": ["视觉灵感"],
    },
    "答辩": {
        "style": ["视觉传达"],
        "emotion": ["理性"],
        "use": ["视觉灵感"],
    },
    "PPT": {
        "style": ["视觉传达"],
        "use": ["视觉灵感"],
    },
    "数据大屏": {
        "use": ["视觉灵感"],
    },
    "海报": {
        "use": ["海报设计"],
    },
    "品牌": {
        "use": ["品牌视觉"],
    },
    "品牌视觉": {
        "use": ["品牌视觉"],
    },
    "UI": {
        "use": ["UI设计"],
    },
    "UI设计": {
        "use": ["UI设计"],
    },
    "网页": {
        "use": ["网页设计"],
    },
    "包装": {
        "use": ["包装设计"],
    },
    "文创": {
        "use": ["文创设计"],
    },
}

# ── 颜色 / 情绪 / 风格 / 场景 关键词集合（用于分类识别） ──────────────────

# 颜色词：能在 color_tags / color_family / overall_tone 中找到的词
_COLOR_VOCAB = {
    "蓝色系", "绿色系", "红色系", "红橙色系", "黄色系", "黄色金色系",
    "橙色系", "紫色系", "紫粉色系", "粉色系", "棕色系", "棕色大地色系",
    "灰色系", "黑色系", "白色系", "蓝绿色系", "黑白灰低饱和系", "多彩高对比系", "金属色系",
    "冷色调", "暖色调", "中性色调",
    "高饱和", "低饱和", "高明度", "低明度", "深色调", "浅色调",
    "浅色系", "中明度色调", "低饱和色调", "高明度色调",
    "蓝灰色", "米色系", "金色系", "黑色系", "大地色", "土地色",
    "科技感", "环保感", "装饰感",  # color_tags 里有这类
}

_EMOTION_VOCAB = {
    "科技", "冷静", "理性", "清新", "自然", "治愈", "温柔", "热烈",
    "活力", "节日", "明亮", "温暖", "精致", "神秘", "梦幻", "浪漫",
    "高级", "庄重", "克制", "稳重", "沉稳", "怀旧", "复古",
    "优雅", "安静", "冷静", "强烈", "奔放",
}

_STYLE_VOCAB = {
    "现代艺术", "抽象艺术", "科技视觉", "东方艺术", "自然主题",
    "装饰艺术", "海报风格", "现代设计", "表现主义", "古典艺术",
    "奢华风格", "极简主义", "浮世绘", "印象派", "浪漫主义",
    "幻想风格", "赛博朋克", "视觉实验", "品牌视觉",
    "历史主题", "欧洲艺术", "亚洲艺术", "科技视觉", "信息图风格",
}

_USE_VOCAB = {
    "数据大屏", "商业仪表盘", "UI设计", "网页设计",
    "环保主题", "信息图设计", "学术汇报", "艺术教育",
    "海报设计", "广告设计", "社交媒体封面", "产品宣传",
    "品牌视觉", "包装设计", "文创设计", "文化展览",
    "插画创作", "视觉灵感", "电影海报",
}

# 布尔关键字（不当搜索词处理）
_BOOL_KEYWORDS = {"and", "or", "not", "或", "非", "与"}

_STOP_WORDS = {
    "的", "地", "得", "了", "着", "过", "是", "在", "有", "和", "与",
    "或", "也", "都", "就", "要", "让", "为", "用", "给", "到", "把",
    "我", "你", "我们", "请", "帮", "找", "想", "能", "可以", "适合",
    "一种", "一个", "一款", "配色", "找个", "找一", "找一个", "想要",
    "需要", "希望", "推荐", "色卡", "时候", "用到", "使用", "做",
    "我在", "想找", "我想找", "不要", "一点", "一点的", "风格", "颜色", "色彩",
}

# 轻量前缀规整：让“适合答辩PPT / 用于海报 / 做品牌视觉”这类表达更容易命中
_PHRASE_PREFIXES = (
    "适合", "用于", "用在", "用来", "做", "给", "偏向", "偏", "适配",
    "希望", "想要", "更适合", "建议", "推荐", "适用于",
)


# ── 从 Excel 加载映射 ────────────────────────────────────────────────────────

def _load_from_excel(path: Path) -> tuple[dict[str, str], dict[str, dict[str, list[str]]]]:
    """
    从 Excel 加载：
    - synonym_mapping sheet  → {口语词: 标准词}
    - query_mapping sheet    → {口语词: {color:[..], emotion:[..], style:[..], use:[..]}}
    """
    try:
        import pandas as pd
        xl = pd.ExcelFile(str(path))
        sheets = xl.sheet_names

        synonym: dict[str, str] = {}
        if "synonym_mapping" in sheets:
            df = xl.parse("synonym_mapping", dtype=str).fillna("")
            for _, row in df.iterrows():
                src = str(row.get("口语词/同义词", "")).strip()
                dst = str(row.get("标准词", "")).strip()
                if src and dst and src.lower() not in ("nan", "none", ""):
                    synonym[src] = dst

        qmap: dict[str, dict[str, list[str]]] = {}
        if "query_mapping" in sheets:
            df = xl.parse("query_mapping", dtype=str).fillna("")
            for _, row in df.iterrows():
                phrase = str(row.get("用户搜索词/口语词", "")).strip()
                if not phrase or phrase.lower() in ("nan", "none", ""):
                    continue
                entry: dict[str, list[str]] = {}
                for col, cat in [
                    ("映射 color_tags",   "color"),
                    ("映射 emotion_tags", "emotion"),
                    ("映射 style_tags",   "style"),
                    ("映射 use_tags",     "use"),
                ]:
                    val = str(row.get(col, "")).strip()
                    if val and val.lower() not in ("nan", "none", ""):
                        entry[cat] = [t.strip() for t in re.split(r"[、,，]", val) if t.strip()]
                if entry:
                    qmap[phrase] = entry

        return synonym, qmap
    except Exception as e:
        print(f"[query_processor] Excel 加载失败: {e}")
        return {}, {}


# ── 分词工具 ─────────────────────────────────────────────────────────────────

def _tokenize_query(text: str) -> tuple[list[str], list[str]]:
    """
    将查询字符串切分成词列表，同时提取 NOT 词。
    支持：空格、顿号、逗号分隔；识别 NOT/非 关键字。
    """
    text = text.strip()
    text = re.sub(r"(?i)(?<![a-z])(and|or|not)(?![a-z])", r" \1 ", text)
    if _JIEBA_AVAILABLE and len(re.findall(r"[\u4e00-\u9fff]", text)) >= 4:
        tokens = [token.strip() for token in jieba.lcut(text, cut_all=False) if token.strip()]
    else:
        tokens = re.split(r"[，、,\s]+", text)
        tokens = [t.strip() for t in tokens if t.strip()]

    normal: list[str] = []
    not_terms: list[str] = []
    skip_next_as_not = False

    for tok in tokens:
        low = tok.lower()
        if low in ("not", "非"):
            skip_next_as_not = True
            continue
        if low in _BOOL_KEYWORDS:
            continue  # and / or 在此层不处理，分类后再处理
        if skip_next_as_not:
            not_terms.append(low)
            skip_next_as_not = False
        else:
            normal.append(tok)

    return normal, not_terms


def _mask_spans(text: str, spans: list[tuple[int, int]]) -> str:
    chars = list(text)
    for start, end in spans:
        for idx in range(start, end):
            chars[idx] = " "
    return "".join(chars)


def _is_sentence_noise(token: str) -> bool:
    token = token.strip().lower()
    if not token or token in _STOP_WORDS:
        return True
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", token)
    return len(chinese_chars) >= 4 and not any(ch.isascii() and ch.isalnum() for ch in token)


def _is_negated_match(lowered: str, start: int) -> bool:
    prefix = lowered[max(0, start - 8):start]
    return bool(re.search(r"(not\s*|非|不要|不想要|别要|別要)$", prefix))


# ── 主类 ─────────────────────────────────────────────────────────────────────

class QueryProcessor:
    """
    查询预处理器。

    参数：
        excel_path : 数据.xlsx 路径，用于加载 synonym/query mapping。
    """

    def __init__(self, excel_path: str | Path | None = None) -> None:
        self._synonym: dict[str, str] = dict(_DEFAULT_SYNONYM)
        self._qmap: dict[str, dict[str, list[str]]] = dict(_DEFAULT_QUERY_MAPPING)

        if excel_path is not None:
            syn, qmap = _load_from_excel(Path(excel_path))
            self._synonym.update(syn)
            self._qmap.update(qmap)

        if _JIEBA_AVAILABLE:
            vocab = (
                list(self._qmap)
                + list(self._synonym)
                + list(self._synonym.values())
                + list(_COLOR_VOCAB)
                + list(_EMOTION_VOCAB)
                + list(_STYLE_VOCAB)
                + list(_USE_VOCAB)
            )
            for word in vocab:
                if word and len(word) >= 2:
                    jieba.add_word(word)

    def _classify_term(
        self,
        term: str,
        color_terms: list[str],
        emotion_terms: list[str],
        style_terms: list[str],
        use_terms: list[str],
        other_terms: list[str],
    ) -> str:
        term = term.strip()
        term_lower = term.lower()
        if not term or term_lower in _STOP_WORDS or term_lower in _BOOL_KEYWORDS:
            return "stop"

        for vocab, bucket, category in [
            (_COLOR_VOCAB, color_terms, "color"),
            (_EMOTION_VOCAB, emotion_terms, "emotion"),
            (_STYLE_VOCAB, style_terms, "style"),
            (_USE_VOCAB, use_terms, "use"),
        ]:
            if term in vocab or term_lower in vocab:
                bucket.append(term)
                return category

        for vocab, bucket, category in [
            (_COLOR_VOCAB, color_terms, "color"),
            (_EMOTION_VOCAB, emotion_terms, "emotion"),
            (_STYLE_VOCAB, style_terms, "style"),
            (_USE_VOCAB, use_terms, "use"),
        ]:
            for vocab_term in sorted(vocab, key=len, reverse=True):
                if term_lower in vocab_term.lower() or vocab_term.lower() in term_lower:
                    bucket.append(vocab_term)
                    return category

        if not _is_sentence_noise(term):
            other_terms.append(term_lower)
            return "other"
        return "noise"

    def _extract_known_phrases(
        self,
        raw_query: str,
        color_terms: list[str],
        emotion_terms: list[str],
        style_terms: list[str],
        use_terms: list[str],
        other_terms: list[str],
        not_terms: list[str],
        debug_expansions: dict[str, dict],
    ) -> str:
        """先扫描连续自然句中的领域短语，再处理剩余口语片段。"""
        lowered = raw_query.lower()
        occupied = [False] * len(raw_query)
        spans: list[tuple[int, int]] = []
        phrase_candidates: dict[str, str] = {}
        for source in (
            self._qmap.keys(),
            self._synonym.keys(),
            _COLOR_VOCAB,
            _EMOTION_VOCAB,
            _STYLE_VOCAB,
            _USE_VOCAB,
        ):
            for phrase in source:
                if phrase and len(phrase.strip()) >= 2:
                    phrase_candidates.setdefault(phrase.lower(), phrase)
        phrases = sorted(phrase_candidates.values(), key=len, reverse=True)

        for phrase in phrases:
            phrase_lower = phrase.lower()
            start = lowered.find(phrase_lower)
            while start != -1:
                end = start + len(phrase_lower)
                if not any(occupied[start:end]):
                    entry = self._qmap.get(phrase) or self._qmap.get(phrase_lower)
                    std = self._synonym.get(phrase) or self._synonym.get(phrase_lower) or phrase
                    if _is_negated_match(lowered, start):
                        if entry:
                            for category in ("color", "emotion", "style", "use"):
                                not_terms.extend(entry.get(category, []))
                        else:
                            not_terms.append(std)
                        source = "negated_phrase"
                    elif entry:
                        color_terms += entry.get("color", [])
                        emotion_terms += entry.get("emotion", [])
                        style_terms += entry.get("style", [])
                        use_terms += entry.get("use", [])
                        source = "query_mapping"
                    else:
                        self._classify_term(
                            std,
                            color_terms,
                            emotion_terms,
                            style_terms,
                            use_terms,
                            other_terms,
                        )
                        source = "phrase_scan"

                    debug_expansions[phrase] = {
                        "source": source,
                        "mapped": std,
                        "expansion": entry or {},
                    }
                    for idx in range(start, end):
                        occupied[idx] = True
                    spans.append((start, end))
                start = lowered.find(phrase_lower, start + 1)

        return _mask_spans(raw_query, spans)

    def process(self, raw_query: str) -> dict:
        """
        将用户输入解析为分类查询结构。

        返回：
        {
            "original":      str,
            "color_terms":   list[str],   匹配 color_tags / color_family / overall_tone
            "emotion_terms": list[str],   匹配 emotion_tags
            "style_terms":   list[str],   匹配 style_tags
            "use_terms":     list[str],   匹配 use_tags
            "other_terms":   list[str],   全文兜底
            "not_terms":     list[str],   NOT 排除
            "debug":         dict,        展开过程（调试用）
        }
        """
        raw_query = raw_query.strip()
        empty = {
            "original": raw_query,
            "color_terms": [], "emotion_terms": [],
            "style_terms": [], "use_terms": [],
            "other_terms": [], "not_terms": [],
            "debug": {},
        }
        if not raw_query:
            return empty

        color_terms:   list[str] = []
        emotion_terms: list[str] = []
        style_terms:   list[str] = []
        use_terms:     list[str] = []
        other_terms:   list[str] = []
        not_terms:     list[str] = []
        debug_expansions: dict[str, dict] = {}

        residual_query = self._extract_known_phrases(
            raw_query,
            color_terms,
            emotion_terms,
            style_terms,
            use_terms,
            other_terms,
            not_terms,
            debug_expansions,
        )
        tokens, residual_not_terms = _tokenize_query(residual_query)
        not_terms.extend(residual_not_terms)

        for tok in tokens:
            tok = _normalize_query_token(tok)
            tok_lower = tok.lower()

            # 1. Query Mapping 优先（整词匹配，按 category 展开）
            if tok in self._qmap or tok_lower in self._qmap:
                entry = self._qmap.get(tok) or self._qmap.get(tok_lower, {})
                debug_expansions[tok] = {"source": "query_mapping", "expansion": entry}
                color_terms   += entry.get("color",   [])
                emotion_terms += entry.get("emotion", [])
                style_terms   += entry.get("style",   [])
                use_terms     += entry.get("use",     [])
                continue

            # 2. 同义词标准化
            std = self._synonym.get(tok) or self._synonym.get(tok_lower)
            if std:
                tok = std
                tok_lower = std.lower()
                debug_expansions[tok] = {"source": "synonym", "mapped": std}

            # 3. 按词典分类
            self._classify_term(
                tok,
                color_terms,
                emotion_terms,
                style_terms,
                use_terms,
                other_terms,
            )

        def dedup(lst):
            return list(dict.fromkeys(lst))

        normalized_not_terms = [_normalize_query_token(t) for t in not_terms]
        normalized_not_terms = [t for t in normalized_not_terms if t]
        if not any((color_terms, emotion_terms, style_terms, use_terms, other_terms, normalized_not_terms)):
            other_terms.append(raw_query.lower())

        return {
            "original":      raw_query,
            "color_terms":   dedup(color_terms),
            "emotion_terms": dedup(emotion_terms),
            "style_terms":   dedup(style_terms),
            "use_terms":     dedup(use_terms),
            "other_terms":   dedup(other_terms),
            "not_terms":     dedup(normalized_not_terms),
            "debug":         debug_expansions,
        }


# ── 模块级单例 ───────────────────────────────────────────────────────────────

_processor: QueryProcessor | None = None


def init_processor(excel_path: str | Path) -> None:
    global _processor
    _processor = QueryProcessor(excel_path)


def get_processor() -> QueryProcessor:
    global _processor
    if _processor is None:
        _processor = QueryProcessor()
    return _processor


def process_query(raw_query: str) -> dict:
    return get_processor().process(raw_query)


def _normalize_query_token(token: str) -> str:
    """
    轻量规整查询 token，让口语表达更容易映射到结构化词表。
    只做非常保守的前缀清洗，不引入复杂分词逻辑。
    """
    text = token.strip()
    if not text:
        return text

    changed = True
    while changed:
        changed = False
        for prefix in _PHRASE_PREFIXES:
            if text.startswith(prefix) and len(text) > len(prefix):
                text = text[len(prefix):].strip()
                changed = True
                break

    # 常见连接词后缀，便于把“适合答辩PPT的”规整成“答辩PPT”
    for suffix in ("的", "款", "类", "型"):
        if text.endswith(suffix) and len(text) > len(suffix) + 1:
            text = text[: -len(suffix)].strip()
            break

    return text
