"""
PaletteSeek 后端包。
前端只需：from paletteseek_backend import PaletteSeek
"""

from .palette_seek import PaletteSeek

try:
    from .palette_report import render_palette_report, render_palette_report_from_artwork
    __all__ = ["PaletteSeek", "render_palette_report", "render_palette_report_from_artwork"]
except ImportError:
    __all__ = ["PaletteSeek"]
