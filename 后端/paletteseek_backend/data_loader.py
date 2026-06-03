"""
data_loader.py
--------------
负责从 Excel 加载作品数据和色卡数据（合并），
并将所有字段以统一的 Python dict 格式暴露给检索模块。

数据来源：
    数据.xlsx        → 主数据（artworks_final_100），含 color_tags / emotion_tags / style_tags / use_tags
    palette_results.xlsx → 色卡数据（作品-色卡对应表），含 color_N_hex / color_N_ratio 等
    两表以 id 做 LEFT JOIN，保留主数据所有记录。

使用方式：
    from data_loader import ArtworkDataset
    ds = ArtworkDataset("数据.xlsx")
    records = ds.records   # list[dict]
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from .color_utils import classify_hex_family
except ImportError:
    from color_utils import classify_hex_family


_MAIN_SHEET   = "artworks_final_100"
_PALETTE_FILE = "palette_results.xlsx"
_PALETTE_SHEET = "作品-色卡对应表"

_MAIN_COLS = [
    "id", "title", "artist", "year", "culture", "classification",
    "medium", "source_url", "image_url",
    "color_tags", "emotion_tags", "style_tags", "use_tags",
]

_PALETTE_COLS = [
    "palette_image_file", "palette_image_path",
    "color_chinese_names", "overall_tone", "color_family", "color_tags_cn",
    "color_1_hex", "color_1_ratio", "color_1_cn",
    "color_2_hex", "color_2_ratio", "color_2_cn",
    "color_3_hex", "color_3_ratio", "color_3_cn",
    "color_4_hex", "color_4_ratio", "color_4_cn",
    "color_5_hex", "color_5_ratio", "color_5_cn",
    "color_6_hex", "color_6_ratio", "color_6_cn",
    "color_7_hex", "color_7_ratio", "color_7_cn",
    "color_8_hex", "color_8_ratio", "color_8_cn",
    "color_9_hex", "color_9_ratio", "color_9_cn",
]


def _clean_str(val: Any) -> str:
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    return "" if s.lower() in ("nan", "none", "") else s


def _parse_ratio(ratio_str: str) -> float:
    s = str(ratio_str).strip().rstrip("%")
    try:
        val = float(s)
        return round(val / 100.0 if val > 1 else val, 6)
    except ValueError:
        return 0.0


def _extract_palette(rec: dict) -> tuple[list[str], list[float]]:
    hexes, ratios = [], []
    for i in range(1, 10):
        h = _clean_str(rec.get(f"color_{i}_hex", ""))
        r = _clean_str(rec.get(f"color_{i}_ratio", ""))
        if h:
            if not h.startswith("#"):
                h = f"#{h}"
            hexes.append(h)
            ratios.append(_parse_ratio(r))
    return hexes, ratios


def _normalize_ratios(ratios: list[float], color_count: int) -> list[float]:
    normalized: list[float] = []
    for ratio in ratios[:color_count]:
        try:
            val = float(str(ratio).strip().rstrip("%"))
            normalized.append(val / 100.0 if val > 1 else val)
        except Exception:
            normalized.append(0.0)

    if len(normalized) < color_count:
        normalized += [0.0] * (color_count - len(normalized))

    total = sum(normalized)
    if total <= 0 and color_count:
        return [1.0 / color_count] * color_count
    if total <= 0:
        return []
    return [val / total for val in normalized]


def _dominant_color_family(hexes: list[str], ratios: list[float]) -> tuple[str, dict[str, float]]:
    """
    按色卡中同一色系的总占比决定主色系。

    Excel 里的 color_tags/color_family 可能有人工标错；检索时应以实际色卡
    HEX + ratio 为准，尤其是用户用「黄色系 AND 清新」这类颜色标签筛选时。
    """
    if not hexes:
        return "", {}

    norm = _normalize_ratios(ratios, len(hexes))
    weights: dict[str, float] = {}
    order: list[str] = []

    for hex_value, ratio in zip(hexes, norm):
        try:
            family = classify_hex_family(hex_value)
        except Exception:
            continue
        if family not in weights:
            weights[family] = 0.0
            order.append(family)
        weights[family] += ratio

    if not weights:
        return "", {}

    dominant = max(order, key=lambda family: weights[family])
    rounded_weights = {family: round(weight, 6) for family, weight in weights.items()}
    return dominant, rounded_weights


class ArtworkDataset:
    """
    加载并缓存作品数据（主表 + 色卡表合并）。

    属性：
        records : list[dict]   所有作品记录
        df      : DataFrame    合并后的 DataFrame

    每条 record 额外字段：
        palette_hexes           list[str]
        palette_ratios          list[float]
        searchable_text         str
        palette_image_filename  str
    """

    def __init__(
        self,
        excel_path: str | Path,
        palette_path: str | Path | None = None,
        sheet_name: str = _MAIN_SHEET,
    ) -> None:
        self._path = Path(excel_path)
        # 默认色卡文件与主文件同目录
        if palette_path is None:
            self._palette_path = self._path.parent / _PALETTE_FILE
        else:
            self._palette_path = Path(palette_path)
        self._sheet = sheet_name
        self._df: pd.DataFrame | None = None
        self._records: list[dict] | None = None

    @property
    def df(self) -> pd.DataFrame:
        if self._df is None:
            self._load()
        return self._df  # type: ignore

    @property
    def records(self) -> list[dict]:
        if self._records is None:
            self._load()
        return self._records  # type: ignore

    def get_by_id(self, artwork_id: int | str) -> dict | None:
        for rec in self.records:
            if str(rec["id"]) == str(artwork_id):
                return rec
        return None

    def reload(self) -> None:
        self._df = None
        self._records = None
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            raise FileNotFoundError(f"找不到数据文件：{self._path}")

        main_df = pd.read_excel(str(self._path), sheet_name=self._sheet, dtype=str).fillna("")

        # 补全主表缺失列
        for col in _MAIN_COLS:
            if col not in main_df.columns:
                main_df[col] = ""

        # 加载色卡表（如果存在）
        palette_df = None
        if self._palette_path.exists():
            try:
                palette_df = pd.read_excel(
                    str(self._palette_path), sheet_name=_PALETTE_SHEET, dtype=str
                ).fillna("")
                for col in _PALETTE_COLS:
                    if col not in palette_df.columns:
                        palette_df[col] = ""
                # 只保留需要的列
                keep_cols = ["id"] + [c for c in _PALETTE_COLS if c in palette_df.columns]
                palette_df = palette_df[keep_cols]
            except Exception as e:
                print(f"[data_loader] 警告：加载色卡文件失败 ({e})，色卡数据将为空")
                palette_df = None

        # 合并
        if palette_df is not None:
            merged = main_df.merge(palette_df, on="id", how="left", suffixes=("", "_pal"))
            # 合并后色卡列可能带 _pal 后缀，做修正
            for col in _PALETTE_COLS:
                if col not in merged.columns and f"{col}_pal" in merged.columns:
                    merged[col] = merged[f"{col}_pal"]
        else:
            merged = main_df
            for col in _PALETTE_COLS:
                merged[col] = ""

        merged = merged.fillna("")
        self._df = merged

        records: list[dict] = []
        all_cols = _MAIN_COLS + _PALETTE_COLS
        for _, row in merged.iterrows():
            rec: dict[str, Any] = {col: _clean_str(row.get(col, "")) for col in all_cols}

            hexes, ratios = _extract_palette(rec)
            rec["palette_hexes"] = hexes
            rec["palette_ratios"] = ratios

            dominant_family, family_weights = _dominant_color_family(hexes, ratios)
            rec["dominant_color_family"] = dominant_family
            rec["color_family_weights"] = family_weights
            if dominant_family:
                rec["original_color_tags"] = rec.get("color_tags", "")
                rec["original_color_family"] = rec.get("color_family", "")
                rec["color_tags"] = dominant_family
                rec["color_family"] = dominant_family

            text_parts = [
                rec["title"], rec["artist"], rec["year"], rec["culture"],
                rec["classification"], rec["medium"],
                rec["color_tags"], rec["emotion_tags"], rec["style_tags"], rec["use_tags"],
                rec.get("color_tags_cn", ""), rec.get("color_chinese_names", ""),
                rec.get("overall_tone", ""), rec.get("color_family", ""),
            ]
            rec["searchable_text"] = " ".join(p for p in text_parts if p).lower()

            raw_path = rec.get("palette_image_path", "")
            rec["palette_image_filename"] = Path(raw_path).name if raw_path else rec.get("palette_image_file", "")

            records.append(rec)

        self._records = records
