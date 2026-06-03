"""
PaletteSeek 后端包。
前端只需：from paletteseek_backend import PaletteSeek
"""

from .palette_seek import PaletteSeek

try:
    from .palette_report import render_palette_report, render_palette_report_from_artwork
except ImportError:
    # 综合色彩报告依赖 matplotlib，前端单页只需要 PaletteSeek 时允许该依赖缺失。
    render_palette_report = None
    render_palette_report_from_artwork = None

__all__ = ["PaletteSeek", "render_palette_report", "render_palette_report_from_artwork"]
