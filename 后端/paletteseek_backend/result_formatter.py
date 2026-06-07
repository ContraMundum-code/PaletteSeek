"""
result_formatter.py
-------------------
检索结果的展示格式化工具，主要供 Streamlit 前端调用。

提供：
- format_card(record)       → 展示用的卡片字典（精简字段）
- format_palette_hex(record) → 返回色块所需 HEX 列表
- generate_usage_suggestion(record) → 生成配色用途建议表
- format_results_for_display(results) → 批量格式化一页结果
"""

from __future__ import annotations

try:
    from .color_utils import hex_to_rgb, rgb_to_hsv
except ImportError:
    from color_utils import hex_to_rgb, rgb_to_hsv


def format_card(record: dict) -> dict:
    """
    将一条完整 record 格式化为前端卡片所需字段。

    返回字典包含：
        id, title, artist, year, culture, classification, medium
        image_url
        palette_image_filename  -- 仅文件名，前端挂静态目录后自己拼路径
        palette_hexes           -- list[str]，最多 9 个主色
        palette_ratios          -- list[float]，对应占比（0~1）
        color_names             -- list[str]，中文颜色名
        overall_tone
        color_family
        color_tags
        emotion_tags
        style_tags
        use_tags
        source_url
        _score                  -- 检索得分（0~1）
        _rank                   -- 排名
        _reason                 -- 推荐理由
        usage_suggestion        -- 配色用途建议（dict）
    """
    hexes = record.get("palette_hexes", [])
    ratios = record.get("palette_ratios", [])

    # 中文颜色名（拆成列表）
    raw_cn = record.get("color_chinese_names", "") or record.get("color_tags_cn", "")
    color_names = [n.strip() for n in raw_cn.replace("，", "、").split("、") if n.strip()]
    # 对齐 palette_hexes 长度
    color_names = color_names[:len(hexes)]

    card = {
        "id":          record.get("id", ""),
        "title":       record.get("title", ""),
        "artist":      record.get("artist", ""),
        "year":        record.get("year", ""),
        "culture":     record.get("culture", ""),
        "classification": record.get("classification", ""),
        "medium":      record.get("medium", ""),
        "image_url":   record.get("image_url", ""),
        "palette_image_filename": record.get("palette_image_filename", ""),
        "palette_hexes":  hexes,
        "palette_ratios": ratios,
        "color_names":    color_names,
        "overall_tone":   record.get("overall_tone", ""),
        "color_family":   record.get("color_family", ""),
        "color_tags":     record.get("color_tags", ""),
        "emotion_tags":   record.get("emotion_tags", ""),
        "style_tags":     record.get("style_tags", ""),
        "use_tags":       record.get("use_tags", ""),
        "source_url":     record.get("source_url", ""),
        "_score":         record.get("_score", 0.0),
        "_rank":          record.get("_rank", 0),
        "_reason":        record.get("_reason", ""),
        "_color_score":   record.get("_color_score", None),
        "_text_score":    record.get("_text_score", None),
        "_tag_score":     record.get("_tag_score", None),
        "_query_match_mode": record.get("_query_match_mode", ""),
        "usage_suggestion": generate_usage_suggestion(record),
    }
    return card


def format_palette_hex(record: dict) -> list[str]:
    """返回干净的 HEX 列表，用于前端色块渲染。"""
    return record.get("palette_hexes", [])


def generate_usage_suggestion(record: dict) -> dict[str, str]:
    """
    根据调色盘自动推导配色用途建议。

    返回：
        {
            "背景色":  "#HEX",
            "标题色":  "#HEX",
            "正文色":  "#HEX",
            "强调色":  "#HEX",
            "辅助色":  "#HEX",
        }

    规则：
    - 背景色：明度最低（最深）或最高（最浅）的颜色，取决于 overall_tone
    - 标题色：与背景色对比度最高的颜色
    - 正文色：高明度中性色（饱和度低的浅色）
    - 强调色：饱和度最高的颜色
    - 辅助色：占比第二的颜色
    """
    hexes = record.get("palette_hexes", [])
    ratios = record.get("palette_ratios", [])
    overall_tone = record.get("overall_tone", "")

    if not hexes:
        return {}

    # 计算每个颜色的 HSV
    hsv_list = [rgb_to_hsv(*hex_to_rgb(h)) for h in hexes]

    # 背景色：根据整体色调决定取最深还是最浅
    if "深色调" in overall_tone:
        bg_idx = min(range(len(hexes)), key=lambda i: hsv_list[i][2])   # 最低明度
    else:
        bg_idx = max(range(len(hexes)), key=lambda i: hsv_list[i][2])   # 最高明度
    bg_hex = hexes[bg_idx]

    # 标题色：与背景色对比最大（明度差最大）
    bg_v = hsv_list[bg_idx][2]
    title_idx = max(
        [i for i in range(len(hexes)) if i != bg_idx] or [0],
        key=lambda i: abs(hsv_list[i][2] - bg_v),
    )
    title_hex = hexes[title_idx]

    # 强调色：饱和度最高
    accent_idx = max(range(len(hexes)), key=lambda i: hsv_list[i][1])
    accent_hex = hexes[accent_idx]

    # 正文色：饱和度低且明度高
    text_idx = max(
        range(len(hexes)),
        key=lambda i: hsv_list[i][2] * (1 - hsv_list[i][1]),
    )
    text_hex = hexes[text_idx]

    # 辅助色：占比第二的颜色（如果有）
    if len(hexes) >= 2:
        second_idx = sorted(range(len(ratios)), key=lambda i: ratios[i], reverse=True)[1]
        aux_hex = hexes[second_idx]
    else:
        aux_hex = hexes[0]

    return {
        "背景色": bg_hex,
        "标题色": title_hex,
        "正文色": text_hex,
        "强调色": accent_hex,
        "辅助色": aux_hex,
    }


def format_results_for_display(results: list[dict]) -> list[dict]:
    """
    批量将检索结果转换为前端展示用的卡片列表。

    参数：
        results : 来自 SearchEngine 的原始检索结果列表

    返回：
        list[dict] — 每条都经过 format_card 处理
    """
    return [format_card(r) for r in results]
