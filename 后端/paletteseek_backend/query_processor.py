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


# ── 内置同义词（fallback，Excel 加载优先覆盖） ───────────────────────────────

_DEFAULT_SYNONYM: dict[str, str] = {
    # 繁简常见写法
    "黃色系": "黄色系", "藍色系": "蓝色系", "綠色系": "绿色系",
    "紅色系": "红色系", "橙色系": "橙色系", "紫色系": "紫色系",
    "粉色系": "粉色系", "灰色系": "灰色系", "黑色系": "黑色系",
    "白色系": "白色系", "藍綠色系": "蓝绿色系",
    "棕色大地色系": "棕色大地色系", "黃色金色系": "黄色金色系",
    # 颜色
    "莫兰迪": "低饱和", "莫兰迪色": "低饱和", "高级灰": "低饱和",
    "大地色": "棕色大地色系", "土色": "棕色大地色系", "大地色系": "棕色大地色系",
    "奶油色": "浅色系", "脏色": "低饱和",
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


# ── 主类 ─────────────────────────────────────────────────────────────────────

class QueryProcessor:
    """
    查询预处理器。

    参数：
        excel_path : 数据.xlsx 路径，用于加载 synonym/query mapping。
    """

    def __init__(self, excel_path: str | Path | None = None) -> None:
        self._synonym: dict[str, str] = dict(_DEFAULT_SYNONYM)
        self._qmap: dict[str, dict[str, list[str]]] = {}

        if excel_path is not None:
            syn, qmap = _load_from_excel(Path(excel_path))
            self._synonym.update(syn)
            self._qmap.update(qmap)

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

        tokens, not_terms = _tokenize_query(raw_query)

        color_terms:   list[str] = []
        emotion_terms: list[str] = []
        style_terms:   list[str] = []
        use_terms:     list[str] = []
        other_terms:   list[str] = []
        debug_expansions: dict[str, dict] = {}

        for tok in tokens:
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
            if tok in _COLOR_VOCAB or tok_lower in _COLOR_VOCAB:
                color_terms.append(tok)
            elif tok in _EMOTION_VOCAB or tok_lower in _EMOTION_VOCAB:
                emotion_terms.append(tok)
            elif tok in _STYLE_VOCAB or tok_lower in _STYLE_VOCAB:
                style_terms.append(tok)
            elif tok in _USE_VOCAB or tok_lower in _USE_VOCAB:
                use_terms.append(tok)
            else:
                # 兜底：尝试部分匹配分类
                placed = False
                for vocab, bucket in [
                    (_COLOR_VOCAB,   color_terms),
                    (_EMOTION_VOCAB, emotion_terms),
                    (_STYLE_VOCAB,   style_terms),
                    (_USE_VOCAB,     use_terms),
                ]:
                    if any(tok_lower in v.lower() or v.lower() in tok_lower for v in vocab):
                        bucket.append(tok)
                        placed = True
                        break
                if not placed:
                    other_terms.append(tok_lower)

        def dedup(lst):
            return list(dict.fromkeys(lst))

        return {
            "original":      raw_query,
            "color_terms":   dedup(color_terms),
            "emotion_terms": dedup(emotion_terms),
            "style_terms":   dedup(style_terms),
            "use_terms":     dedup(use_terms),
            "other_terms":   dedup(other_terms),
            "not_terms":     dedup(not_terms),
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
