"""
color_utils.py
--------------
颜色相关工具函数：
- HEX / RGB / HSV 互转
- 颜色距离计算（欧氏距离、Delta-E CIE76 近似）
- 相似度归一化
"""

from __future__ import annotations

import math
import re
from typing import Tuple


RGBTuple = Tuple[int, int, int]
LabTuple = Tuple[float, float, float]


# ---------------------------------------------------------------------------
# 格式转换
# ---------------------------------------------------------------------------

def hex_to_rgb(hex_str: str) -> RGBTuple:
    """
    将 HEX 色值转换为 (R, G, B)。
    支持 "#RRGGBB"、"RRGGBB"、"#RGB" 三种格式。
    异常时返回 (128, 128, 128)（中灰）作为兜底。
    """
    hex_str = hex_str.strip().lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join(c * 2 for c in hex_str)
    if len(hex_str) != 6 or not re.fullmatch(r"[0-9A-Fa-f]{6}", hex_str):
        return (128, 128, 128)
    r = int(hex_str[0:2], 16)
    g = int(hex_str[2:4], 16)
    b = int(hex_str[4:6], 16)
    return (r, g, b)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """(R, G, B) → '#RRGGBB'"""
    return "#{:02X}{:02X}{:02X}".format(
        max(0, min(255, r)),
        max(0, min(255, g)),
        max(0, min(255, b)),
    )


def rgb_to_hsv(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """
    (R, G, B) → (H, S, V)
    H ∈ [0, 360], S ∈ [0, 1], V ∈ [0, 1]
    """
    import colorsys
    h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    return (h * 360, s, v)


# ---------------------------------------------------------------------------
# 颜色空间转换：RGB → XYZ → CIELab
# （用于 Delta-E 计算，比 HSV 欧氏距离在感知层面更准确）
# ---------------------------------------------------------------------------

def _gamma_expand(c: float) -> float:
    """sRGB gamma 展开，用于 RGB→XYZ 转换。"""
    c /= 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def rgb_to_lab(r: int, g: int, b: int) -> LabTuple:
    """
    RGB → CIELab（D65 光源）。
    L ∈ [0, 100], a ∈ [-128, 127], b ∈ [-128, 127]
    """
    # Step 1: RGB → 线性 RGB
    rl = _gamma_expand(r)
    gl = _gamma_expand(g)
    bl = _gamma_expand(b)

    # Step 2: 线性 RGB → XYZ（D65 标准）
    x = rl * 0.4124564 + gl * 0.3575761 + bl * 0.1804375
    y = rl * 0.2126729 + gl * 0.7151522 + bl * 0.0721750
    z = rl * 0.0193339 + gl * 0.1191920 + bl * 0.9503041

    # Step 3: XYZ → Lab（D65 白点）
    xn, yn, zn = 0.95047, 1.00000, 1.08883

    def _f(t: float) -> float:
        if t > 0.008856:
            return t ** (1 / 3)
        return 7.787 * t + 16 / 116

    fx = _f(x / xn)
    fy = _f(y / yn)
    fz = _f(z / zn)

    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b_val = 200 * (fy - fz)
    return (L, a, b_val)


# ---------------------------------------------------------------------------
# 距离计算
# ---------------------------------------------------------------------------

def delta_e(hex1: str, hex2: str) -> float:
    """
    计算两个 HEX 色值之间的 Delta-E（CIE76，感知距离）。
    值越小越相似；0 = 完全相同；≥ 25 可视为完全不同。
    """
    lab1 = rgb_to_lab(*hex_to_rgb(hex1))
    lab2 = rgb_to_lab(*hex_to_rgb(hex2))
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(lab1, lab2)))


def rgb_distance(hex1: str, hex2: str) -> float:
    """
    RGB 欧氏距离，最大值约为 441.67。
    备用方法，Delta-E 优先。
    """
    r1, g1, b1 = hex_to_rgb(hex1)
    r2, g2, b2 = hex_to_rgb(hex2)
    return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)


# ---------------------------------------------------------------------------
# 相似度计算：输入颜色 vs 一幅作品的调色盘
# ---------------------------------------------------------------------------

MAX_DELTA_E = 100.0   # Delta-E 理论上限（感知空间裁切值）


def palette_color_similarity(
    query_hex: str,
    palette_hexes: list[str],
    palette_ratios: list[float],
) -> float:
    """
    计算查询颜色与作品调色盘的相似度，返回值 ∈ [0, 1]。

    策略：
    1. 对调色盘中每个主色，计算 Delta-E；
    2. 将距离转换为相似度（1 - dist / MAX），并加权颜色占比；
    3. 同时取"最相似单色"作为额外加分（避免占比小但高度匹配的颜色被压权）。

    参数：
        query_hex     : 用户输入色 HEX，如 "#1E3A8A"
        palette_hexes : 作品主色列表（最多 9 个）
        palette_ratios: 对应占比列表（浮点，0~1 或 0~100 均可）
    """
    if not palette_hexes:
        return 0.0

    # 归一化占比
    ratios = []
    for r in palette_ratios:
        try:
            val = float(str(r).strip().rstrip("%"))
        except (ValueError, AttributeError):
            val = 0.0
        ratios.append(val)

    total = sum(ratios)
    if total <= 0:
        ratios = [1.0 / len(palette_hexes)] * len(palette_hexes)
    else:
        ratios = [r / total for r in ratios]

    weighted_sim = 0.0
    best_sim = 0.0

    for hex_c, ratio in zip(palette_hexes, ratios):
        dist = delta_e(query_hex, hex_c)
        sim = max(0.0, 1.0 - dist / MAX_DELTA_E)
        weighted_sim += sim * ratio
        if sim > best_sim:
            best_sim = sim

    # 最终相似度 = 70% 加权相似度 + 30% 最佳单色相似度
    return round(0.7 * weighted_sim + 0.3 * best_sim, 6)


def is_valid_hex(hex_str: str) -> bool:
    """检查字符串是否为有效 HEX 色值。"""
    s = hex_str.strip().lstrip("#")
    return bool(re.fullmatch(r"[0-9A-Fa-f]{6}", s))


# ---------------------------------------------------------------------------
# 色卡颜色家族分类（用于按比例加权的颜色词匹配）
# ---------------------------------------------------------------------------

def classify_hex_family(hex_str: str) -> str:
    """
    将一个 HEX 色值分类为颜色家族名称（与数据集 color_tags 词典一致）。

    返回值示例：蓝色系 / 绿色系 / 棕色大地色系 / 橙色系 / 黄色系 /
                红色系 / 紫色系 / 粉色系 / 蓝绿色系 / 灰色系 / 黑色系 / 白色系
    """
    r, g, b = hex_to_rgb(hex_str)
    hue, sat, val = rgb_to_hsv(r, g, b)
    # sat/val 从 rgb_to_hsv 出来是 0~1，转成百分比
    sat_pct = sat * 100
    val_pct = val * 100

    if val_pct < 12:
        return "黑色系"
    if val_pct > 88 and sat_pct < 10:
        return "白色系"
    if sat_pct < 12:
        return "灰色系"
    # 低亮度橙色/黃色帶有色相的深色 → 棕色系
    if sat_pct < 50 and val_pct < 38 and (hue < 70 or hue >= 330):
        return "棕色大地色系"

    h = hue
    if h < 18 or h >= 345:
        return "红色系"
    if h < 42:
        return "棕色大地色系" if val_pct < 50 else "橙色系"
    if h < 68:
        return "黄色系"
    if h < 155:
        return "绿色系"
    if h < 195:
        return "蓝绿色系"
    if h < 258:
        return "蓝色系"
    if h < 298:
        return "紫色系"
    return "粉色系"


# 色调/饱和度描述词 → 判断函数
# 用于 _color_palette_score 的非色系词处理
_TONE_CHECKERS: dict[str, str] = {
    "暖色调": "warm", "暖色": "warm",
    "冷色调": "cool", "冷色": "cool",
    "低饱和": "low_sat", "低饱和度": "low_sat",
    "高饱和": "high_sat", "高饱和度": "high_sat",
    "深色调": "dark", "低明度": "dark",
    "高明度": "bright", "浅色调": "bright", "高明度色调": "bright",
    "中明度": "mid",
}


def palette_family_score(
    color_terms: list[str],
    palette_hexes: list[str],
    palette_ratios: list[float],
) -> float:
    """
    以调色盘中每个颜色的实际占比为权重，计算用户颜色查询词的匹配分。

    规则：
      - 对于色系词（蓝色系、棕色大地色系 等）：
          将每个 palette 颜色分类，找出与查询词匹配的颜色，
          累加其 ratio → 得分（0~1，ratio 越大得分越高）
      - 对于色调词（暖色调、冷色调、低饱和、深色调 等）：
          用调色盘加权平均的 HSV 判断，返回软性分值

    参数：
        color_terms    : 用户颜色查询词列表
        palette_hexes  : 作品 K-means 提取的主色 HEX 列表
        palette_ratios : 对应占比（0~1 或百分比均可，自动归一化）

    返回：0~1 的平均匹配分
    """
    if not color_terms or not palette_hexes:
        return 0.0

    # 归一化 ratios（先转为数值，再统一归一化，避免混合格式问题）
    raw = []
    for rv in palette_ratios:
        try:
            v = float(str(rv).strip().rstrip("%"))
            raw.append(v / 100 if v > 1 else v)
        except Exception:
            raw.append(0.0)
    total = sum(raw) or 1.0
    norm = [r / total for r in raw]

    # 每个 palette 色的 HSV 和家族
    hsv_list = []
    families = []
    for hx in palette_hexes:
        r2, g2, b2 = hex_to_rgb(hx)
        h, s, v = rgb_to_hsv(r2, g2, b2)
        hsv_list.append((h, s * 100, v * 100))   # H=0~360, S/V=0~100
        families.append(classify_hex_family(hx))

    # 调色盘加权平均
    w_sat  = sum(hsv[1] * r for hsv, r in zip(hsv_list, norm))
    w_val  = sum(hsv[2] * r for hsv, r in zip(hsv_list, norm))
    warm_w = sum(r for (h, s, v), r in zip(hsv_list, norm)
                 if (h < 90 or h > 330) and s > 15 and v > 15)
    cool_w = sum(r for (h, s, v), r in zip(hsv_list, norm)
                 if 160 < h < 280 and s > 15)

    term_scores: list[float] = []
    for qt in color_terms:
        qt_lower = qt.lower()
        tone = _TONE_CHECKERS.get(qt_lower) or _TONE_CHECKERS.get(qt)

        if tone == "warm":
            term_scores.append(min(warm_w * 1.5, 1.0))
        elif tone == "cool":
            term_scores.append(min(cool_w * 1.5, 1.0))
        elif tone == "low_sat":
            # 低饱和：平均饱和度越低越好
            term_scores.append(max(0.0, 1.0 - w_sat / 35))
        elif tone == "high_sat":
            term_scores.append(max(0.0, (w_sat - 35) / 50))
        elif tone == "dark":
            term_scores.append(max(0.0, 1.0 - w_val / 40))
        elif tone == "bright":
            term_scores.append(max(0.0, (w_val - 55) / 45))
        elif tone == "mid":
            mid_score = 1.0 - abs(w_val - 55) / 45
            term_scores.append(max(0.0, mid_score))
        else:
            # 色系词 → 精确匹配家族名，累加匹配颜色的 ratio
            # 不用子字串匹配，避免 "绿色系" 误匹配 "蓝绿色系"
            match_ratio = sum(
                r for fam, r in zip(families, norm)
                if qt_lower == fam.lower()
            )
            term_scores.append(min(match_ratio, 1.0))

    return sum(term_scores) / len(term_scores) if term_scores else 0.0
