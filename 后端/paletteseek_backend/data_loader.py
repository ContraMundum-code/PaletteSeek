"""
data_loader.py
--------------
负责从 Excel 加载 artworks_with_palette_100，
做类型清洗，并将所有字段以统一的 Python dict 格式暴露给检索模块。

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


# 需要从 Excel 读取的字段（按 PDF 说明整理）
_REQUIRED_COLS = [
    "id",
    "title",
    "artist",
    "year",
    "culture",
    "classification",
    "medium",
    "source_url",
    "image_url",
    "palette_image_path",
    "palette_image_file",
    "dominant_colors",
    "color_ratio",
    "color_tags",
    "emotion_tags",
    "style_tags",
    "use_tags",
    "color_tags_cn",
    "color_chinese_names",
    "overall_tone",
    "color_family",
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

_SHEET_NAME = "artworks_with_palette_100"


def _clean_str(val: Any) -> str:
    """将单元格值清洗为干净字符串；空值返回 ''。"""
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip()


def _parse_ratio(ratio_str: str) -> float:
    """
    将 '25.36%' 或 '0.2536' 统一转为 0~1 之间的浮点数。
    解析失败时返回 0.0。
    """
    s = str(ratio_str).strip().rstrip("%")
    try:
        val = float(s)
        # 如果是百分比格式（>1），除以100
        if val > 1:
            val = val / 100.0
        return round(val, 6)
    except ValueError:
        return 0.0


def _extract_palette_hexes_ratios(row: dict) -> tuple[list[str], list[float]]:
    """从 color_N_hex / color_N_ratio 字段提取调色盘。"""
    hexes = []
    ratios = []
    for i in range(1, 10):
        h = _clean_str(row.get(f"color_{i}_hex", ""))
        r_str = _clean_str(row.get(f"color_{i}_ratio", ""))
        if h and h != "nan":
            hexes.append(h)
            ratios.append(_parse_ratio(r_str))
    return hexes, ratios


class ArtworkDataset:
    """
    加载并缓存 artworks_with_palette_100 工作表数据。

    属性：
        records : list[dict]  -- 所有作品记录，每条都是字典
        df      : DataFrame   -- 原始 DataFrame（供需要直接操作的场合使用）

    每条 record 包含的额外预处理字段（原表没有，这里派生）：
        palette_hexes  : list[str]   -- 9 个主色 HEX（只含非空值）
        palette_ratios : list[float] -- 对应占比（0~1）
        searchable_text: str         -- 拼接后的全文搜索字段（小写）
        palette_image_filename: str  -- 仅文件名（去掉绝对路径）
    """

    def __init__(self, excel_path: str | Path, sheet_name: str = _SHEET_NAME) -> None:
        self._path = Path(excel_path)
        self._sheet = sheet_name
        self._df: pd.DataFrame | None = None
        self._records: list[dict] | None = None

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    @property
    def df(self) -> pd.DataFrame:
        if self._df is None:
            self._load()
        return self._df  # type: ignore[return-value]

    @property
    def records(self) -> list[dict]:
        if self._records is None:
            self._load()
        return self._records  # type: ignore[return-value]

    def get_by_id(self, artwork_id: int | str) -> dict | None:
        """根据 id 获取单条记录，找不到时返回 None。"""
        for rec in self.records:
            if str(rec["id"]) == str(artwork_id):
                return rec
        return None

    def reload(self) -> None:
        """强制重新从磁盘读取（文件更新后调用）。"""
        self._df = None
        self._records = None
        self._load()

    # ------------------------------------------------------------------
    # 内部加载
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self._path.exists():
            raise FileNotFoundError(f"找不到数据文件：{self._path}")

        df = pd.read_excel(
            str(self._path),
            sheet_name=self._sheet,
            dtype=str,          # 全部读成字符串，避免类型歧义
        )
        df = df.fillna("")

        # 只保留已知字段；对缺失列填空
        for col in _REQUIRED_COLS:
            if col not in df.columns:
                df[col] = ""

        self._df = df

        records = []
        for _, row in df.iterrows():
            rec: dict[str, Any] = {col: _clean_str(row.get(col, "")) for col in _REQUIRED_COLS}

            # 派生字段 1：调色盘 HEX + 占比
            hexes, ratios = _extract_palette_hexes_ratios(rec)
            rec["palette_hexes"] = hexes
            rec["palette_ratios"] = ratios

            # 派生字段 2：全文检索字段（合并所有文本）
            text_parts = [
                rec["title"],
                rec["artist"],
                rec["year"],
                rec["culture"],
                rec["classification"],
                rec["medium"],
                rec["color_tags"],
                rec["emotion_tags"],
                rec["style_tags"],
                rec["use_tags"],
                rec["color_tags_cn"],
                rec["color_chinese_names"],
                rec["overall_tone"],
                rec["color_family"],
            ]
            rec["searchable_text"] = " ".join(p for p in text_parts if p).lower()

            # 派生字段 3：只保留色卡图片文件名（去掉本机绝对路径）
            raw_path = rec.get("palette_image_path", "")
            if raw_path:
                rec["palette_image_filename"] = Path(raw_path).name
            else:
                rec["palette_image_filename"] = rec.get("palette_image_file", "")

            records.append(rec)

        self._records = records
