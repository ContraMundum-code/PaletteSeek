"""
palette_seek.py
---------------
PaletteSeek 后端统一入口，前端只需导入这一个模块。

典型用法（Streamlit 前端）：

    from paletteseek_backend import PaletteSeek

    # 初始化（只需一次，建议放在 @st.cache_resource 下）
    ps = PaletteSeek("数据.xlsx")

    # 关键词检索
    results = ps.keyword_search("深蓝 科技感 PPT")

    # 颜色检索
    results = ps.color_search("#1E3A8A")

    # 混合检索（推荐）
    results = ps.hybrid_search(query="科技感 数据大屏", hex_color="#1E3A8A")

    # 获取所有作品（首页展示）
    all_artworks = ps.get_all(top_k=20)

    # 筛选选项（用于前端下拉菜单）
    filter_options = ps.list_filter_options()

    # 根据 ID 获取单件作品
    artwork = ps.get_by_id(869)
"""

from __future__ import annotations

from pathlib import Path

try:
    from .data_loader import ArtworkDataset
    from .result_formatter import format_card, format_results_for_display
    from .search_engine import SearchEngine
except ImportError:
    from data_loader import ArtworkDataset
    from result_formatter import format_card, format_results_for_display
    from search_engine import SearchEngine


class PaletteSeek:
    """
    PaletteSeek 后端主类。

    参数：
        excel_path   : str | Path — 数据.xlsx 的路径
        color_cards_dir : str | Path | None
            本地色卡图片目录（解压后的 color_cards 文件夹路径）。
            若提供，get_palette_image_path() 可返回可用的本地路径。
    """

    def __init__(
        self,
        excel_path: str | Path = "数据.xlsx",
        color_cards_dir: str | Path | None = None,
    ) -> None:
        self._excel_path = Path(excel_path)
        self._color_cards_dir = Path(color_cards_dir) if color_cards_dir else None

        self._dataset = ArtworkDataset(self._excel_path)
        self._engine  = SearchEngine(self._dataset)

    # ------------------------------------------------------------------
    # 检索接口
    # ------------------------------------------------------------------

    def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[dict]:
        """
        关键词 / 标签检索。

        参数：
            query   : 用户输入关键词，如 "深蓝 PPT 稳重"
            top_k   : 返回数量（默认 10）
            filters : 精确筛选，如 {"color_family": "蓝色系"}

        返回：格式化后的卡片列表，按相关度降序。
        """
        raw = self._engine.keyword_search(query=query, top_k=top_k, filters=filters)
        return format_results_for_display(raw)

    def color_search(
        self,
        hex_color: str,
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[dict]:
        """
        颜色相似检索。

        参数：
            hex_color : HEX 色值，如 "#1E3A8A" 或 "1e3a8a"
            top_k     : 返回数量
            filters   : 精确筛选

        抛出：
            ValueError — HEX 格式不合法时
        """
        raw = self._engine.color_search(hex_color=hex_color, top_k=top_k, filters=filters)
        return format_results_for_display(raw)

    def hybrid_search(
        self,
        query: str = "",
        hex_color: str = "",
        top_k: int = 10,
        filters: dict | None = None,
        w_color: float = 0.40,
        w_tag:   float = 0.30,
        w_text:  float = 0.30,
    ) -> list[dict]:
        """
        混合检索（推荐使用）。

        参数：
            query     : 文本关键词，可为空
            hex_color : HEX 色值，可为空
            top_k     : 返回数量
            filters   : 精确筛选
            w_color / w_tag / w_text : 三项权重，默认 0.4 / 0.3 / 0.3

        注意：query 和 hex_color 至少提供一个。

        抛出：
            ValueError — 两项都为空，或 HEX 格式不合法
        """
        raw = self._engine.hybrid_search(
            query=query,
            hex_color=hex_color,
            top_k=top_k,
            filters=filters,
            w_color=w_color,
            w_tag=w_tag,
            w_text=w_text,
        )
        return format_results_for_display(raw)

    # ------------------------------------------------------------------
    # 数据接口
    # ------------------------------------------------------------------

    def get_all(self, top_k: int | None = None) -> list[dict]:
        """返回所有（或前 top_k 件）作品，用于首页展示。"""
        raw = self._engine.get_all(top_k=top_k)
        return format_results_for_display(raw)

    def get_by_id(self, artwork_id: int | str) -> dict | None:
        """
        根据作品 ID 获取单条格式化记录。
        找不到时返回 None。
        """
        rec = self._dataset.get_by_id(artwork_id)
        if rec is None:
            return None
        return format_card({**rec, "_score": 1.0, "_rank": 1, "_reason": ""})

    def list_filter_options(self) -> dict[str, list[str]]:
        """
        返回各筛选字段的可选项，用于前端下拉菜单。

        返回：
            {
                "overall_tone":   ["中明度色调", "深色调", ...],
                "color_family":   ["蓝色系", "橙色系", ...],
                "culture":        ["欧洲", "美洲", ...],
                "classification": ["Painting / Sculpture", ...],
            }
        """
        return self._engine.list_filter_options()

    # ------------------------------------------------------------------
    # 色卡图片路径工具
    # ------------------------------------------------------------------

    def get_palette_image_path(self, artwork_id: int | str) -> Path | None:
        """
        返回作品色卡图片的本地路径（Path 对象）。

        若提供了 color_cards_dir，返回 color_cards_dir/<id>_palette.png。
        若该路径存在，则返回；否则返回 None。

        前端使用方式示例（Streamlit）：
            path = ps.get_palette_image_path(record["id"])
            if path:
                st.image(str(path))
        """
        if self._color_cards_dir is None:
            return None
        filename = f"{artwork_id}_palette.png"
        p = self._color_cards_dir / filename
        return p if p.exists() else None

    # ------------------------------------------------------------------
    # 统计信息
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """
        返回数据集基本统计，供调试或首页信息展示。

        返回：
            {
                "total":          int,   作品总数
                "color_families": list,  色系列表
                "overall_tones":  list,  整体色调列表
                "data_source":    str,   数据文件路径
            }
        """
        options = self.list_filter_options()
        return {
            "total":          len(self._dataset.records),
            "color_families": options.get("color_family", []),
            "overall_tones":  options.get("overall_tone", []),
            "data_source":    str(self._excel_path),
        }
