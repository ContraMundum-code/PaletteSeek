from __future__ import annotations

import base64
from datetime import datetime
import hashlib
import html
from io import BytesIO
import json
import sys
from pathlib import Path
from typing import Any

import streamlit.components.v1 as components
import streamlit as st
from PIL import Image


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "后端"
BACKEND_PACKAGE_DIR = BACKEND_DIR / "paletteseek_backend"
EXCEL_PATH = BACKEND_PACKAGE_DIR / "数据.xlsx"
COLOR_CARDS_DIR = BACKEND_PACKAGE_DIR / "color_cards"
REPORTS_DIR = BACKEND_PACKAGE_DIR / "reports"
SUBMISSIONS_FILE = BACKEND_PACKAGE_DIR / "submissions.xlsx"
SUBMISSIONS_IMAGES_DIR = BACKEND_PACKAGE_DIR / "submissions_images"
SUBMISSION_REPORTS_DIR = BACKEND_PACKAGE_DIR / "submission_reports"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

BACKEND_IMPORT_ERROR: Exception | None = None
try:  # noqa: E402
    from paletteseek_backend import PaletteSeek
    from paletteseek_backend.color_utils import (
        classify_hex_family,
        is_valid_hex,
        palette_color_similarity,
        rgb_to_hex,
    )
    from paletteseek_backend.result_formatter import generate_usage_suggestion
except Exception as exc:  # pragma: no cover - runtime guard for missing deps
    PaletteSeek = Any  # type: ignore[assignment]

    def is_valid_hex(_: str) -> bool:
        return False

    def rgb_to_hex(r: int, g: int, b: int) -> str:
        return "#{:02X}{:02X}{:02X}".format(r, g, b)

    def classify_hex_family(_: str) -> str:
        return "未标注色系"

    def palette_color_similarity(_: str, __: list[str], ___: list[float]) -> float:
        return 0.0

    def generate_usage_suggestion(_: dict) -> dict[str, str]:
        return {}

    BACKEND_IMPORT_ERROR = exc


st.set_page_config(
    page_title="PaletteSeek",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)


APP_CSS = """
<style>
:root {
    --ps-bg: #ede7dc;
    --ps-paper: #fffdf8;
    --ps-paper-soft: #f8f3ea;
    --ps-ink: #151918;
    --ps-muted: #68716f;
    --ps-line: rgba(21, 25, 24, 0.13);
    --ps-jade: #245f5a;
    --ps-accent: #1f6f7a;
    --ps-vermilion: #b5523d;
    --ps-ochre: #c08a45;
    --ps-blueblack: #182433;
    --ps-shadow: 0 18px 48px rgba(31, 34, 31, 0.10);
    --ps-tight-shadow: 0 10px 26px rgba(31, 34, 31, 0.08);
}

html, body, [data-testid="stAppViewContainer"] {
    background:
        repeating-linear-gradient(118deg, rgba(21,25,24,0.028) 0 1px, transparent 1px 18px),
        repeating-linear-gradient(32deg, rgba(255,253,248,0.22) 0 1px, transparent 1px 26px),
        radial-gradient(ellipse at 18% 8%, rgba(36, 95, 90, 0.14), transparent 42%),
        radial-gradient(ellipse at 88% 18%, rgba(181, 82, 61, 0.11), transparent 38%),
        linear-gradient(160deg, #fbf7ed 0%, #eee5d7 42%, #e1d9cd 74%, #f7f1e7 100%);
    background-size: 220px 220px, 180px 180px, auto, auto, auto;
    color: var(--ps-ink);
    animation: psBackdropBreathe 18s ease-in-out infinite alternate;
}

#MainMenu, footer, header { visibility: hidden; }

.block-container {
    padding-top: 1.2rem;
    padding-bottom: 2.4rem;
    max-width: 1280px;
}

.ps-hero {
    position: relative;
    overflow: visible;
    border: 1px solid rgba(24, 36, 51, 0.32);
    background:
        linear-gradient(135deg, rgba(24,36,51,0.98), rgba(36,55,65,0.94)),
        linear-gradient(90deg, rgba(181,82,61,0.20), transparent 46%);
    box-shadow: 0 22px 54px rgba(24, 36, 51, 0.18);
    border-radius: 18px;
    padding: 2.05rem 2.15rem 1.55rem 2.15rem;
    margin-bottom: 0.9rem;
    animation: psHeroReveal 0.86s cubic-bezier(0.22, 0.61, 0.36, 1) both;
}

.ps-help-wrap {
    position: absolute;
    top: 1.25rem;
    right: 1.35rem;
    z-index: 20;
}

.ps-help-dot {
    width: 2rem;
    height: 2rem;
    display: inline-grid;
    place-items: center;
    border-radius: 999px;
    border: 1px solid rgba(255, 253, 248, 0.28);
    background: rgba(255, 253, 248, 0.12);
    color: rgba(255, 253, 248, 0.88);
    font-family: "Cormorant Garamond", "Georgia", serif;
    font-size: 1.25rem;
    font-weight: 900;
    cursor: help;
    transition: transform 180ms ease, background 180ms ease, box-shadow 180ms ease;
}

.ps-help-wrap:hover .ps-help-dot {
    transform: translateY(-2px) rotate(4deg);
    background: rgba(255, 253, 248, 0.20);
    box-shadow: 0 12px 28px rgba(226, 179, 110, 0.18);
}

.ps-help-panel {
    position: absolute;
    top: 2.62rem;
    right: 0;
    width: min(22rem, calc(100vw - 3rem));
    border-radius: 16px;
    border: 1px solid rgba(255, 253, 248, 0.20);
    background:
        linear-gradient(135deg, rgba(24, 36, 51, 0.94), rgba(36, 95, 90, 0.82)),
        radial-gradient(circle at 20% 10%, rgba(226, 179, 110, 0.20), transparent 34%);
    box-shadow: 0 24px 52px rgba(0, 0, 0, 0.24);
    padding: 0.92rem;
    opacity: 0;
    visibility: hidden;
    transform: translateY(-6px) scale(0.98);
    transition: opacity 180ms ease, visibility 180ms ease, transform 180ms ease;
    backdrop-filter: blur(12px) saturate(1.15);
    -webkit-backdrop-filter: blur(12px) saturate(1.15);
    pointer-events: none;
}

.ps-help-wrap:hover .ps-help-panel {
    opacity: 1;
    visibility: visible;
    transform: translateY(0) scale(1);
    pointer-events: auto;
}

.ps-help-title {
    color: #fffdf8;
    font-size: 0.82rem;
    font-weight: 900;
    letter-spacing: 0.08em;
    margin-bottom: 0.66rem;
}

.ps-help-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.58rem;
}

.ps-hero::before {
    content: "";
    position: absolute;
    inset: -34% -12% auto auto;
    width: 58%;
    height: 160%;
    pointer-events: none;
    z-index: 0;
    background:
        radial-gradient(circle at 50% 50%, rgba(226, 179, 110, 0.34), transparent 34%),
        radial-gradient(circle at 60% 34%, rgba(36, 95, 90, 0.36), transparent 36%),
        radial-gradient(circle at 32% 72%, rgba(181, 82, 61, 0.30), transparent 34%);
    filter: blur(18px);
    opacity: 0.92;
    transform: rotate(-8deg);
    animation: psHaloDrift 9.2s ease-in-out infinite alternate;
}

.ps-hero::after {
    content: "";
    position: absolute;
    right: 2rem;
    bottom: 1.5rem;
    width: 124px;
    height: 10px;
    background: linear-gradient(90deg, #245f5a 0 28%, #b5523d 28% 48%, #c08a45 48% 72%, #182433 72% 100%);
    background-size: 220% 100%;
    box-shadow: 0 10px 26px rgba(21,25,24,0.12);
    animation: psColorDrift 4.8s ease-in-out infinite alternate;
    pointer-events: none;
    z-index: 1;
}

.ps-hero > * {
    position: relative;
    z-index: 2;
}

.ps-hero .ps-help-wrap {
    position: absolute;
    top: 1.25rem;
    right: 1.35rem;
    z-index: 20;
}

.ps-kicker {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.02em;
    font-family: "Snell Roundhand", "Apple Chancery", "Brush Script MT", "Segoe Script", cursive;
    font-size: 1.18rem;
    letter-spacing: 0.03em;
    color: #e2b36e;
    font-weight: 600;
    margin-bottom: 0.25rem;
    transform-origin: left center;
}

.ps-kicker span {
    display: inline-block;
    transform-origin: center bottom;
    animation: psGlyphDance 2.7s ease-in-out infinite;
    animation-delay: calc(var(--i) * 0.045s);
}

.ps-title {
    position: relative;
    display: inline-block;
    max-width: 840px;
    font-family: "Xingkai SC", "STXingkai", "HanziPen SC", "Kaiti SC", "KaiTi", "Songti SC", serif;
    font-size: 3.35rem;
    line-height: 1.06;
    font-weight: 900;
    margin: 0.1rem 0 0.7rem 0;
    color: #fffdf8;
    letter-spacing: 0;
    text-shadow: 0 10px 34px rgba(0, 0, 0, 0.28);
    transform-origin: left center;
}

.ps-title::after {
    content: "";
    position: absolute;
    inset: -0.05em -0.18em;
    pointer-events: none;
    background: linear-gradient(110deg, transparent 0%, rgba(255,253,248,0.0) 34%, rgba(255,253,248,0.68) 50%, rgba(255,253,248,0.0) 66%, transparent 100%);
    transform: translateX(-120%);
    mix-blend-mode: screen;
    animation: psTitleSheen 4.8s ease-in-out infinite;
}

.ps-title-cn {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.03em;
    transform-origin: center bottom;
    animation: psInkPulse 5.2s ease-in-out infinite alternate;
}

.ps-title-cn span {
    display: inline-block;
    transform-origin: center bottom;
    animation: psHanDance 2.9s cubic-bezier(0.36, 0.01, 0.22, 1) infinite;
    animation-delay: calc(var(--i) * 0.09s);
}

.ps-subtitle {
    font-family: "Kaiti SC", "STKaiti", "Xingkai SC", "HanziPen SC", "Songti SC", serif;
    color: rgba(255, 253, 248, 0.78);
    font-size: 1.08rem;
    line-height: 1.72;
    max-width: 720px;
    margin-bottom: 1rem;
    letter-spacing: 0.02em;
}

.ps-stat-strip {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.58rem;
    margin: 0;
}

.ps-stat {
    border: 1px solid rgba(255, 253, 248, 0.18);
    background: rgba(255, 253, 248, 0.10);
    border-radius: 10px;
    padding: 0.62rem 0.68rem;
    box-shadow: var(--ps-tight-shadow);
    transition: transform 180ms ease, border-color 180ms ease, background 180ms ease, box-shadow 180ms ease;
    animation: psFadeUp 0.72s cubic-bezier(0.22, 0.61, 0.36, 1) both, psStatGlow 6.8s ease-in-out infinite alternate;
}

.ps-stat:hover {
    transform: translateY(-4px);
    border-color: rgba(226, 179, 110, 0.42);
    background: rgba(255, 253, 248, 0.22);
    box-shadow: 0 18px 38px rgba(24, 36, 51, 0.16);
}

.ps-stat-head {
    display: flex;
    align-items: center;
    gap: 0.48rem;
}

.ps-stat-icon {
    width: 1.72rem;
    height: 1.72rem;
    display: inline-grid;
    place-items: center;
    border-radius: 999px;
    border: 1px solid rgba(255, 253, 248, 0.24);
    background: rgba(255, 253, 248, 0.10);
    color: #e2b36e;
    font-size: 1rem;
    line-height: 1;
}

.ps-stat:nth-child(2) {
    animation-delay: 0.08s, 0.6s;
}

.ps-stat:nth-child(3) {
    animation-delay: 0.16s, 1.2s;
}

.ps-stat:nth-child(4) {
    animation-delay: 0.24s, 1.8s;
}

.ps-stat-value {
    font-family: "Cormorant Garamond", "Georgia", "Times New Roman", serif;
    color: #fffdf8;
    font-size: 1.22rem;
    line-height: 1;
    font-weight: 900;
}

.ps-stat-label {
    font-family: "Kaiti SC", "STKaiti", "Xingkai SC", "HanziPen SC", "Songti SC", serif;
    margin-top: 0.35rem;
    color: rgba(255, 253, 248, 0.66);
    font-size: 0.76rem;
    font-weight: 700;
    letter-spacing: 0.04em;
}

.ps-stat-value-text {
    font-family: "Snell Roundhand", "Apple Chancery", "Brush Script MT", "Segoe Script", cursive;
    font-size: 1.3rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}

.ps-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    margin-top: 0.85rem;
}

.ps-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.42rem 0.68rem;
    border-radius: 999px;
    border: 1px solid rgba(36, 95, 90, 0.18);
    background: rgba(255, 253, 248, 0.82);
    color: var(--ps-ink);
    font-size: 0.80rem;
    font-weight: 700;
    transition: transform 180ms ease, border-color 180ms ease, background 180ms ease;
}

.ps-chip:hover {
    transform: translateY(-1px);
    border-color: rgba(181, 82, 61, 0.32);
    background: rgba(255, 253, 248, 0.96);
}

.ps-workbench-note {
    margin: 0.35rem 0 0.85rem 0;
    color: var(--ps-muted);
    font-size: 0.88rem;
    line-height: 1.55;
}

.ps-workbench-rule {
    height: 1px;
    margin: 0.35rem 0 0.9rem 0;
    background: linear-gradient(90deg, var(--ps-jade), rgba(21,25,24,0.10), transparent);
    background-size: 220% 100%;
    animation: psRuleSweep 4.8s ease-in-out infinite alternate;
}

.ps-section-title {
    position: relative;
    overflow: visible;
    z-index: 40;
    margin: 1.2rem 0 0.45rem 0;
    font-size: 1.08rem;
    font-weight: 900;
    color: var(--ps-ink);
    letter-spacing: 0;
}

.ps-section-title span {
    color: var(--ps-accent);
}

.ps-section-help {
    position: relative;
    display: inline-flex;
    align-items: center;
    margin-left: 0.5rem;
    vertical-align: middle;
    z-index: 60;
}

.ps-section-help-dot {
    width: 1.35rem;
    height: 1.35rem;
    display: inline-grid;
    place-items: center;
    border-radius: 999px;
    border: 1px solid rgba(36, 95, 90, 0.28);
    background: rgba(255, 253, 248, 0.76);
    color: var(--ps-jade);
    font-family: "Cormorant Garamond", "Georgia", serif;
    font-size: 0.94rem;
    font-weight: 900;
    cursor: help;
    box-shadow: 0 8px 18px rgba(31, 34, 31, 0.08);
    transition: transform 180ms ease, background 180ms ease, box-shadow 180ms ease;
}

.ps-section-help:hover .ps-section-help-dot {
    transform: translateY(-2px) rotate(4deg);
    background: rgba(236, 250, 248, 0.94);
    box-shadow: 0 12px 28px rgba(36, 95, 90, 0.14);
}

.ps-section-help-panel {
    position: absolute;
    top: 1.95rem;
    left: 0;
    width: min(28rem, calc(100vw - 3rem));
    border-radius: 16px;
    border: 1px solid rgba(36, 95, 90, 0.18);
    background:
        linear-gradient(135deg, rgba(255, 253, 248, 0.96), rgba(236, 250, 248, 0.88)),
        radial-gradient(circle at 92% 12%, rgba(192, 138, 69, 0.16), transparent 36%);
    color: var(--ps-muted);
    box-shadow: 0 24px 52px rgba(31, 34, 31, 0.16);
    padding: 0.82rem 0.92rem;
    opacity: 0;
    visibility: hidden;
    transform: translate(0, -6px) scale(0.98);
    transition: opacity 180ms ease, visibility 180ms ease, transform 180ms ease;
    backdrop-filter: blur(12px) saturate(1.12);
    -webkit-backdrop-filter: blur(12px) saturate(1.12);
    pointer-events: none;
    z-index: 999;
    font-size: 0.82rem;
    line-height: 1.62;
    font-weight: 700;
}

.ps-section-help:hover .ps-section-help-panel {
    opacity: 1;
    visibility: visible;
    transform: translate(0, 0) scale(1);
    pointer-events: auto;
}

.ps-card {
    height: 100%;
    border-radius: 10px;
    border: 1px solid rgba(21, 25, 24, 0.055);
    background: rgba(255, 253, 248, 0.90);
    box-shadow: var(--ps-tight-shadow);
    padding: 0.9rem;
}

.ps-control-spacer {
    height: 2.05rem;
}

.ps-card-highlight {
    border-color: rgba(181, 82, 61, 0.46);
    box-shadow: 0 16px 34px rgba(181, 82, 61, 0.13);
}

.ps-card-title {
    margin-top: 0.35rem;
    font-size: 1rem;
    font-weight: 800;
    color: var(--ps-ink);
    line-height: 1.45;
}

.ps-card-meta {
    font-size: 0.84rem;
    color: var(--ps-muted);
    line-height: 1.5;
}

.ps-result-image {
    position: relative;
    width: 100%;
    aspect-ratio: 1 / 1.16;
    height: auto;
    margin-bottom: 0.62rem;
    border-radius: 9px;
    overflow: hidden;
    background: linear-gradient(135deg, rgba(36,95,90,0.12), rgba(181,82,61,0.08));
    border: 1px solid rgba(21,25,24,0.08);
    box-shadow:
        0 18px 32px rgba(31, 34, 31, 0.16),
        0 9px 18px rgba(145, 100, 36, 0.11),
        0 2px 0 rgba(255, 253, 248, 0.76) inset;
    transform-origin: center bottom;
    cursor: pointer;
    transition:
        transform 520ms cubic-bezier(0.22, 0.61, 0.36, 1),
        box-shadow 520ms ease,
        filter 520ms ease;
}

.ps-result-image img {
    width: 100%;
    height: 100%;
    display: block;
    object-fit: cover;
    transition: transform 520ms cubic-bezier(0.22, 0.61, 0.36, 1), filter 520ms ease;
}

.ps-result-image::after {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    background:
        linear-gradient(180deg, rgba(24, 36, 51, 0.02), rgba(24, 36, 51, 0.58)),
        radial-gradient(circle at 18% 12%, rgba(255, 253, 248, 0.36), transparent 24%);
    opacity: 0;
    transition: opacity 360ms ease;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-card-sentinel):hover .ps-result-image {
    transform: translateY(-22px) scale(1.035) rotate(-0.35deg);
    box-shadow:
        0 34px 58px rgba(31, 34, 31, 0.24),
        0 0 0 1px rgba(255, 253, 248, 0.42) inset;
}

.ps-result-image:hover {
    transform: translateY(-26px) scale(1.052) rotate(-0.35deg);
    box-shadow:
        0 36px 62px rgba(31, 34, 31, 0.26),
        0 18px 34px rgba(180, 118, 42, 0.18),
        0 0 0 1px rgba(255, 253, 248, 0.46) inset;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-card-sentinel):hover .ps-result-image img {
    transform: scale(1.055);
    filter: saturate(1.09) contrast(1.04);
}

.ps-result-image:hover img {
    transform: scale(1.065);
    filter: saturate(1.1) contrast(1.05);
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-card-sentinel):hover .ps-result-image::after {
    opacity: 1;
}

.ps-result-image:hover::after {
    opacity: 1;
}

.ps-result-title {
    font-size: 1.02rem;
    font-weight: 900;
    line-height: 1.35;
    color: var(--ps-ink);
    min-height: 2.55em;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.ps-result-meta {
    font-size: 0.80rem;
    color: var(--ps-muted);
    line-height: 1.45;
    margin-top: 0.28rem;
    min-height: 2.8em;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.ps-result-caption {
    display: none;
}

.ps-result-cover-caption {
    position: absolute;
    left: 0.85rem;
    right: 0.85rem;
    bottom: 0.78rem;
    z-index: 2;
    color: #fffdf8;
    opacity: 0;
    transform: translateY(14px);
    transition: opacity 320ms ease, transform 320ms ease;
    text-shadow: 0 8px 22px rgba(0, 0, 0, 0.42);
}

.ps-result-cover-title {
    font-size: 1rem;
    font-weight: 900;
    line-height: 1.25;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.ps-result-cover-meta {
    margin-top: 0.3rem;
    font-size: 0.76rem;
    line-height: 1.35;
    color: rgba(255, 253, 248, 0.82);
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-card-sentinel):hover .ps-result-cover-caption {
    opacity: 1;
    transform: translateY(0);
}

.ps-result-image:hover .ps-result-cover-caption {
    opacity: 1;
    transform: translateY(0);
}

.ps-rank-mark {
    position: absolute;
    top: 0.72rem;
    left: 0.72rem;
    z-index: 3;
    width: 2.15rem;
    height: 2.15rem;
    display: inline-grid;
    place-items: center;
    border-radius: 999px;
    background:
        linear-gradient(135deg, rgba(255, 248, 230, 0.96), rgba(205, 141, 64, 0.78));
    color: #3e2a13;
    font-family: "Cormorant Garamond", "Georgia", serif;
    font-size: 0.92rem;
    font-weight: 900;
    border: 1px solid rgba(255, 253, 248, 0.58);
    box-shadow:
        0 12px 24px rgba(31, 34, 31, 0.22),
        0 0 0 1px rgba(145, 100, 36, 0.10) inset;
}

.ps-result-reason {
    position: relative;
    font-size: 0.82rem;
    color: var(--ps-muted);
    line-height: 1.45;
    margin-top: 0.58rem;
    min-height: 3.05em;
    padding-left: 0.7rem;
    border-left: 2px solid rgba(36,95,90,0.20);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.ps-result-overlay-note {
    opacity: 0;
    transform: translateY(8px);
    max-height: 0;
    overflow: hidden;
    transition: opacity 280ms ease, transform 280ms ease, max-height 280ms ease;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-card-sentinel):hover .ps-result-overlay-note {
    opacity: 1;
    transform: translateY(0);
    max-height: 5.5rem;
}

.ps-result-palette {
    margin: 0.1rem 0 0.78rem 0;
}

.ps-card-chip-space {
    height: 0;
}

.ps-result-pin {
    position: absolute;
    top: 0.68rem;
    left: 0.68rem;
    z-index: 4;
    display: inline-flex;
    align-items: center;
    padding: 0.28rem 0.55rem;
    border-radius: 999px;
    background: rgba(255, 253, 248, 0.92);
    color: #174f58;
    font-size: 0.72rem;
    font-weight: 900;
    box-shadow: 0 10px 22px rgba(31, 34, 31, 0.16);
}

.ps-card-footer-note {
    min-height: 1.55rem;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.84rem;
    color: var(--ps-muted);
}

.ps-card-footer-note a {
    color: var(--ps-jade);
    text-decoration: none;
    font-weight: 800;
}

.ps-result-source-link {
    margin: -0.18rem 0 0.52rem 0;
    min-height: 1.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.84rem;
    font-weight: 900;
}

.ps-result-source-link a {
    color: var(--ps-jade);
    text-decoration: none;
    border-bottom: 1px solid rgba(36, 95, 90, 0.28);
    transition: color 160ms ease, border-color 160ms ease;
}

.ps-result-source-link a:hover {
    color: var(--ps-accent);
    border-color: rgba(31, 111, 122, 0.58);
}

.ps-source-note {
    margin: -0.2rem 0 1rem 0;
    padding: 0.58rem 0.78rem;
    border-radius: 999px;
    border: 1px solid rgba(36, 95, 90, 0.12);
    background: rgba(255, 253, 248, 0.64);
    color: var(--ps-muted);
    font-size: 0.80rem;
    line-height: 1.45;
}

.ps-submission-intro {
    margin: 0.2rem 0 1rem 0;
    border-radius: 18px;
    border: 1px solid rgba(36, 95, 90, 0.14);
    background:
        linear-gradient(135deg, rgba(255, 253, 248, 0.82), rgba(226, 243, 239, 0.38)),
        radial-gradient(circle at 88% 22%, rgba(192, 138, 69, 0.16), transparent 32%);
    padding: 1rem 1.05rem;
    color: var(--ps-muted);
    line-height: 1.7;
    box-shadow: 0 14px 34px rgba(31, 34, 31, 0.06);
}

.ps-upload-scroll-sentinel {
    display: none;
}

div[data-testid="stElementContainer"]:has(#toggle_upload_form_btn),
div[data-testid="stButton"]:has(#toggle_upload_form_btn) {
    position: relative;
    z-index: 1;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-upload-scroll-sentinel) {
    border: 0 !important;
    outline: 0 !important;
    border-radius: 22px !important;
    background:
        linear-gradient(180deg, rgba(126, 86, 48, 0.92) 0 0.72rem, transparent 0.72rem),
        linear-gradient(0deg, rgba(126, 86, 48, 0.88) 0 0.72rem, transparent 0.72rem),
        linear-gradient(135deg, rgba(255, 253, 248, 0.88), rgba(246, 237, 218, 0.74));
    box-shadow:
        0 24px 54px rgba(31, 34, 31, 0.12),
        0 1px 0 rgba(255, 253, 248, 0.72) inset;
    padding: 1.55rem 1.05rem 1.25rem 1.05rem !important;
    animation: psScrollUnfurl 0.72s cubic-bezier(0.19, 1, 0.22, 1) both;
    transform-origin: center top;
}

.ps-upload-mini-note {
    margin: 0.34rem 0 0.85rem 0;
    color: rgba(104, 113, 111, 0.82);
    font-size: 0.82rem;
    line-height: 1.55;
}

.ps-submission-card-sentinel {
    display: none;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-submission-card-sentinel) {
    position: relative;
    overflow: visible;
    border: 0 !important;
    outline: 0 !important;
    border-radius: 22px !important;
    background:
        linear-gradient(145deg, rgba(255, 253, 248, 0.58), rgba(225, 210, 181, 0.24)),
        radial-gradient(circle at 22% 10%, rgba(255, 255, 255, 0.78), transparent 34%);
    box-shadow:
        0 22px 42px rgba(31, 34, 31, 0.10),
        0 9px 22px rgba(143, 100, 45, 0.08),
        0 1px 0 rgba(255, 253, 248, 0.74) inset;
    padding: 1.05rem !important;
    transition: transform 280ms cubic-bezier(0.22, 0.61, 0.36, 1), box-shadow 280ms ease;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-submission-card-sentinel):hover {
    transform: translateY(-7px) scale(1.012);
    box-shadow:
        0 30px 58px rgba(31, 34, 31, 0.15),
        0 14px 28px rgba(36, 95, 90, 0.10),
        0 1px 0 rgba(255, 253, 248, 0.86) inset;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-submission-card-sentinel)::before,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-submission-card-sentinel)::after {
    display: none !important;
}

.ps-submission-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    margin: 0.48rem 0 0.58rem 0;
    padding: 0.32rem 0.58rem;
    border-radius: 999px;
    background: rgba(36, 95, 90, 0.10);
    color: var(--ps-jade);
    font-size: 0.72rem;
    font-weight: 900;
}

.ps-submission-title {
    margin-top: 0.58rem;
    color: var(--ps-ink);
    font-size: 1.02rem;
    line-height: 1.35;
    font-weight: 900;
}

.ps-submission-meta {
    margin-top: 0.25rem;
    color: var(--ps-muted);
    font-size: 0.82rem;
    line-height: 1.45;
    font-weight: 700;
}

.ps-submission-note {
    margin-top: 0.52rem;
    color: rgba(104, 113, 111, 0.82);
    font-size: 0.78rem;
    line-height: 1.52;
}

.ps-shelf-rail {
    position: relative;
    height: 4.2rem;
    margin: -0.58rem 0 1.85rem 0;
    pointer-events: none;
    perspective: 900px;
}

.ps-shelf-rail::before {
    content: "";
    position: absolute;
    left: 1.2%;
    right: 1.2%;
    top: 0.45rem;
    height: 1.42rem;
    border-radius: 6px 6px 18px 18px;
    background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(241, 239, 230, 0.94) 46%, rgba(203, 199, 187, 0.92) 100%),
        linear-gradient(90deg, rgba(255,255,255,0.18), rgba(255,255,255,0.78), rgba(255,255,255,0.14));
    box-shadow:
        0 4px 0 rgba(255, 253, 248, 0.96) inset,
        0 -8px 16px rgba(31, 34, 31, 0.16) inset,
        0 14px 24px rgba(31, 34, 31, 0.22),
        0 36px 54px rgba(31, 34, 31, 0.13);
    transform: rotateX(54deg) translateY(-0.16rem);
    transform-origin: center top;
}

.ps-shelf-rail::after {
    content: "";
    position: absolute;
    left: 4%;
    right: 4%;
    top: 1.42rem;
    height: 2rem;
    border-radius: 50%;
    background:
        radial-gradient(ellipse at center, rgba(31, 34, 31, 0.34), rgba(31, 34, 31, 0.12) 46%, transparent 72%);
    filter: blur(13px);
    opacity: 0.82;
}

.ps-shelf-rail span {
    position: absolute;
    left: 2.4%;
    right: 2.4%;
    top: 1.18rem;
    height: 0.22rem;
    border-radius: 999px;
    background: linear-gradient(90deg, transparent, rgba(255, 253, 248, 0.92), transparent);
    box-shadow: 0 8px 14px rgba(255, 253, 248, 0.18);
}

.ps-palette {
    display: flex;
    overflow: hidden;
    height: 16px;
    border-radius: 999px;
    background: rgba(17, 24, 39, 0.06);
    border: 1px solid rgba(17, 24, 39, 0.06);
}

.ps-palette span {
    display: block;
    height: 100%;
    animation: psPaletteSettle 0.72s cubic-bezier(0.22, 0.61, 0.36, 1) both;
    transform-origin: left center;
}

.ps-detail-panel {
    border-radius: 10px;
    border: 1px solid var(--ps-line);
    background: rgba(255, 253, 248, 0.94);
    box-shadow: var(--ps-shadow);
    padding: 1.05rem;
    animation: psFadeUp 0.62s cubic-bezier(0.22, 0.61, 0.36, 1) both;
}

.ps-detail-shell-sentinel {
    display: none;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-detail-shell-sentinel) {
    border: 0 !important;
    outline: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-detail-shell-sentinel)::before,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-detail-shell-sentinel)::after {
    border: 0 !important;
    outline: 0 !important;
    box-shadow: none !important;
}

.ps-scroll-report {
    position: relative;
    max-width: 980px;
    margin: 1.05rem auto 0 auto;
    padding: 2.15rem 1.15rem;
    animation: psScrollUnfurl 0.9s cubic-bezier(0.19, 1, 0.22, 1) both;
    transform-origin: center top;
}

.ps-scroll-report::before,
.ps-scroll-report::after {
    content: "";
    position: absolute;
    left: 0.45rem;
    right: 0.45rem;
    height: 1.1rem;
    border-radius: 999px;
    background:
        linear-gradient(180deg, #7f5630, #3d2817),
        linear-gradient(90deg, #3d2817, #c08a45, #3d2817);
    box-shadow:
        0 10px 22px rgba(31, 34, 31, 0.22),
        0 1px 0 rgba(255, 253, 248, 0.28) inset;
    z-index: 2;
}

.ps-scroll-report::before {
    top: 0.72rem;
}

.ps-scroll-report::after {
    bottom: 0.72rem;
}

.ps-scroll-paper {
    position: relative;
    overflow: hidden;
    border-radius: 12px;
    background:
        repeating-linear-gradient(90deg, rgba(120, 86, 45, 0.035) 0 1px, transparent 1px 18px),
        linear-gradient(90deg, rgba(145, 100, 36, 0.13), transparent 8%, transparent 92%, rgba(145, 100, 36, 0.13)),
        linear-gradient(180deg, #fffaf0, #f5ead8);
    border: 1px solid rgba(145, 100, 36, 0.18);
    box-shadow:
        0 28px 58px rgba(31, 34, 31, 0.16),
        0 0 0 1px rgba(255, 253, 248, 0.62) inset;
    padding: 1rem;
}

.ps-scroll-paper img {
    width: 100%;
    max-width: 100%;
    height: auto;
    display: block;
    border-radius: 8px;
    border: 1px solid rgba(145, 100, 36, 0.12);
    background: #fff;
}

.ps-detail-divider {
    height: 1px;
    margin: 0.98rem 0;
    background: linear-gradient(90deg, rgba(36, 95, 90, 0.22), rgba(21, 25, 24, 0.07), transparent);
}

.ps-detail-file-title {
    margin-bottom: 0.9rem;
    padding: 0.78rem 0.88rem;
    border-radius: 14px;
    border: 1px solid rgba(36, 95, 90, 0.12);
    background:
        linear-gradient(135deg, rgba(255, 253, 248, 0.88), rgba(236, 250, 248, 0.46));
    box-shadow: 0 12px 26px rgba(31, 34, 31, 0.06);
}

.ps-detail-file-title strong {
    display: block;
    color: var(--ps-ink);
    font-size: 1.05rem;
    line-height: 1.35;
}

.ps-detail-file-title span {
    display: block;
    margin-top: 0.28rem;
    color: var(--ps-muted);
    font-size: 0.82rem;
    line-height: 1.45;
}

.ps-usage-card-list {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.62rem;
}

.ps-usage-card {
    min-height: 4.35rem;
    border-radius: 14px;
    border: 1px solid rgba(192, 138, 69, 0.18);
    background:
        linear-gradient(135deg, rgba(255, 253, 248, 0.92), rgba(250, 229, 191, 0.38));
    padding: 0.72rem 0.78rem;
    box-shadow:
        0 12px 24px rgba(31, 34, 31, 0.06),
        0 1px 0 rgba(255, 253, 248, 0.84) inset;
}

.ps-usage-card-key {
    color: #7d5624;
    font-size: 0.76rem;
    font-weight: 900;
    letter-spacing: 0.08em;
}

.ps-usage-card-value {
    margin-top: 0.35rem;
    color: var(--ps-ink);
    font-size: 0.86rem;
    line-height: 1.45;
    font-weight: 700;
}

.ps-search-note {
    border-radius: 12px;
    border: 1px dashed rgba(36, 95, 90, 0.16);
    background: rgba(255, 253, 248, 0.48);
    color: rgba(104, 113, 111, 0.76);
    font-size: 0.78rem;
    line-height: 1.55;
    padding: 0.68rem 0.75rem;
}

.ps-copy-hint {
    margin: 0.52rem 0 0.2rem 0;
    color: var(--ps-muted);
    font-size: 0.78rem;
    line-height: 1.45;
}

.ps-report-shell {
    max-width: 920px;
    margin: 0 auto;
}

.ps-face-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
    color: var(--ps-muted);
    font-size: 0.82rem;
    font-weight: 800;
}

.ps-view-tab {
    display: inline-flex;
    align-items: center;
    padding: 0.36rem 0.65rem;
    border-radius: 999px;
    color: var(--ps-paper);
    background: var(--ps-blueblack);
    font-size: 0.78rem;
    font-weight: 800;
}

.ps-soft-appear {
    animation: psFadeUp 0.78s cubic-bezier(0.22, 0.61, 0.36, 1) both;
}

.ps-detail-anchor {
    scroll-margin-top: 1.25rem;
}

@keyframes psFadeUp {
    from {
        opacity: 0;
        transform: translateY(16px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes psHeroReveal {
    from {
        opacity: 0;
        transform: translateY(18px) scale(0.992);
        filter: saturate(0.9);
    }
    to {
        opacity: 1;
        transform: translateY(0) scale(1);
        filter: saturate(1);
    }
}

@keyframes psColorDrift {
    from {
        background-position: 0% 50%;
    }
    to {
        background-position: 100% 50%;
    }
}

@keyframes psRuleSweep {
    from {
        background-position: 0% 50%;
        opacity: 0.72;
    }
    to {
        background-position: 100% 50%;
        opacity: 1;
    }
}

@keyframes psPaletteSettle {
    from {
        transform: scaleX(0.18);
        opacity: 0.72;
    }
    to {
        transform: scaleX(1);
        opacity: 1;
    }
}

@keyframes psBackdropBreathe {
    from {
        background-position: 0 0, 0 0, 0% 0%, 100% 0%, 0 0;
    }
    to {
        background-position: 46px 28px, -36px 30px, 10% 6%, 82% 11%, 0 0;
    }
}

@keyframes psHaloDrift {
    0% {
        opacity: 0.62;
        filter: blur(32px);
        transform: rotate(-10deg) translate3d(0, 0, 0) scale(0.92);
    }
    52% {
        opacity: 0.98;
        filter: blur(10px);
        transform: rotate(9deg) translate3d(-34px, 24px, 0) scale(1.12);
    }
    100% {
        opacity: 0.72;
        filter: blur(24px);
        transform: rotate(16deg) translate3d(-58px, -18px, 0) scale(1.06);
    }
}

@keyframes psTitleFloat {
    0%, 100% {
        transform: translateY(0);
        text-shadow: 0 10px 34px rgba(0, 0, 0, 0.28);
    }
    45% {
        transform: translateY(-7px) scale(1.012);
        text-shadow: 0 18px 48px rgba(226, 179, 110, 0.38);
    }
}

@keyframes psTitleBounce {
    0%, 100% {
        transform: translateY(0) scale(1);
        color: #fffdf8;
        text-shadow: 0 10px 34px rgba(0, 0, 0, 0.28);
    }
    24% {
        transform: translateY(-10px) scale(1.035);
        color: #fff8de;
        text-shadow: 0 18px 52px rgba(226, 179, 110, 0.42);
    }
    42% {
        transform: translateY(3px) scale(0.985);
    }
    64% {
        transform: translateY(-5px) scale(1.018);
        color: #f6e7bf;
    }
}

@keyframes psGlyphDance {
    0%, 100% {
        transform: translateY(0) scale(1) rotate(0deg);
        color: #e2b36e;
        text-shadow: 0 0 0 rgba(226, 179, 110, 0);
    }
    28% {
        transform: translateY(-7px) scale(1.18) rotate(-1deg);
        color: #ffd58f;
        text-shadow: 0 0 24px rgba(226, 179, 110, 0.42);
    }
    52% {
        transform: translateY(2px) scale(0.94) rotate(0.8deg);
    }
}

@keyframes psHanDance {
    0%, 100% {
        transform: translateY(0) scale(1) rotate(0deg);
        color: #fffdf8;
        text-shadow: 0 10px 34px rgba(0, 0, 0, 0.28);
    }
    26% {
        transform: translateY(-13px) scale(1.15) rotate(-1.5deg);
        color: #fff1bd;
        text-shadow: 0 20px 54px rgba(226, 179, 110, 0.46);
    }
    48% {
        transform: translateY(4px) scale(0.94) rotate(1deg);
        color: #f5dfaa;
    }
    70% {
        transform: translateY(-5px) scale(1.06) rotate(-0.4deg);
    }
}

@keyframes psInkPulse {
    from {
        filter: saturate(0.95);
    }
    to {
        filter: saturate(1.2) drop-shadow(0 0 16px rgba(226, 179, 110, 0.24));
    }
}

@keyframes psTitleSheen {
    0%, 42% {
        transform: translateX(-125%);
        opacity: 0;
    }
    52% {
        opacity: 1;
    }
    66%, 100% {
        transform: translateX(125%);
        opacity: 0;
    }
}

@keyframes psKickerTint {
    from {
        color: #e2b36e;
        text-shadow: 0 0 0 rgba(226, 179, 110, 0);
    }
    to {
        color: #ffd58f;
        text-shadow: 0 0 26px rgba(226, 179, 110, 0.42);
    }
}

@keyframes psKickerDance {
    0%, 100% {
        transform: translateY(0) rotate(0deg) scale(1);
        color: #e2b36e;
        text-shadow: 0 0 0 rgba(226, 179, 110, 0);
    }
    32% {
        transform: translateY(-5px) rotate(-1deg) scale(1.08);
        color: #ffd58f;
        text-shadow: 0 0 28px rgba(226, 179, 110, 0.48);
    }
    58% {
        transform: translateY(2px) rotate(0.7deg) scale(0.99);
    }
}

@keyframes psStatGlow {
    from {
        background: rgba(255, 253, 248, 0.09);
        box-shadow: 0 10px 26px rgba(31, 34, 31, 0.08);
    }
    to {
        background: rgba(255, 253, 248, 0.20);
        box-shadow: 0 16px 34px rgba(226, 179, 110, 0.18);
    }
}

@keyframes psScrollReveal {
    from {
        opacity: 0.28;
        transform: translateY(32px) scale(0.965);
        filter: blur(12px);
    }
    to {
        opacity: 1;
        transform: translateY(0) scale(1);
        filter: blur(0);
    }
}

@keyframes psCardFloatReveal {
    0% {
        opacity: 0;
        transform: translateY(46px) scale(0.94);
        filter: blur(14px) saturate(0.82);
        box-shadow: 0 4px 14px rgba(31, 34, 31, 0.04);
    }
    42% {
        opacity: 0.62;
        transform: translateY(18px) scale(0.982);
        filter: blur(5px) saturate(0.96);
    }
    100% {
        opacity: 1;
        transform: translateY(0) scale(1);
        filter: blur(0) saturate(1);
        box-shadow: 0 14px 34px rgba(31, 34, 31, 0.11);
    }
}

@keyframes psPanelBreathe {
    from {
        box-shadow: 0 10px 26px rgba(31, 34, 31, 0.08);
    }
    to {
        box-shadow: 0 15px 34px rgba(36, 95, 90, 0.12);
    }
}

@keyframes psScrollUnfurl {
    0% {
        opacity: 0;
        transform: scaleY(0.08) translateY(-12px);
        filter: blur(8px) saturate(0.85);
    }
    52% {
        opacity: 1;
        transform: scaleY(1.035) translateY(0);
        filter: blur(1px) saturate(1.04);
    }
    100% {
        opacity: 1;
        transform: scaleY(1) translateY(0);
        filter: blur(0) saturate(1);
    }
}

.ps-detail-title {
    font-size: 1.55rem;
    font-weight: 900;
    margin: 0 0 0.35rem 0;
    color: var(--ps-ink);
}

.ps-label {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    color: var(--ps-jade);
    text-transform: uppercase;
    margin-bottom: 0.35rem;
}

.ps-swatch-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 0.75rem;
}

.ps-swatch {
    border-radius: 8px;
    padding: 0.62rem;
    border: 1px solid rgba(17, 24, 39, 0.08);
    background: rgba(255, 253, 248, 0.90);
    transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
}

.ps-swatch:hover {
    transform: translateY(-2px);
    border-color: rgba(36, 95, 90, 0.24);
    box-shadow: 0 12px 26px rgba(31, 34, 31, 0.10);
}

.ps-swatch-color {
    border-radius: 6px;
    height: 68px;
    margin-bottom: 0.58rem;
    border: 1px solid rgba(17, 24, 39, 0.08);
}

.ps-swatch-name {
    font-size: 0.90rem;
    font-weight: 800;
    line-height: 1.4;
}

.ps-swatch-hex {
    margin-top: 0.2rem;
    font-size: 0.78rem;
    color: var(--ps-muted);
}

.ps-info-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.65rem;
    margin-bottom: 0.9rem;
}

.ps-info-card {
    border: 1px solid var(--ps-line);
    border-radius: 8px;
    background: rgba(255, 253, 248, 0.76);
    padding: 0.68rem 0.72rem;
}

.ps-info-label {
    color: var(--ps-muted);
    font-size: 0.72rem;
    font-weight: 800;
    margin-bottom: 0.22rem;
}

.ps-info-value {
    color: var(--ps-ink);
    font-size: 0.88rem;
    line-height: 1.45;
    font-weight: 700;
    overflow-wrap: anywhere;
}

.ps-image-frame {
    border: 1px solid var(--ps-line);
    border-radius: 10px;
    background: rgba(255, 253, 248, 0.86);
    padding: 0.55rem;
    box-shadow: var(--ps-tight-shadow);
    transition: transform 220ms ease, box-shadow 220ms ease;
}

.ps-image-frame:hover {
    transform: translateY(-2px);
    box-shadow: 0 16px 32px rgba(31, 34, 31, 0.12);
}

.ps-badge-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
}

.ps-badge {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 0.34rem 0.62rem;
    background: rgba(36, 95, 90, 0.09);
    color: var(--ps-ink);
    font-size: 0.82rem;
    font-weight: 700;
}

.ps-badge-blue {
    background: rgba(31, 111, 122, 0.12);
    color: #164f58;
}

.ps-badge-red {
    background: rgba(181, 82, 61, 0.12);
    color: #8a3d2d;
}

.ps-badge-yellow {
    background: rgba(192, 138, 69, 0.16);
    color: #7d5624;
}

.ps-badge-green {
    background: rgba(36, 95, 90, 0.12);
    color: #245f5a;
}

.ps-badge-neutral {
    background: rgba(21, 25, 24, 0.08);
    color: var(--ps-ink);
}

.ps-muted-note {
    color: var(--ps-muted);
    font-size: 0.88rem;
    line-height: 1.55;
}

.stButton > button {
    border-radius: 999px;
    font-weight: 700;
    border: 1px solid rgba(36, 95, 90, 0.24);
    background: rgba(255, 253, 248, 0.88);
    color: var(--ps-ink);
    transition: transform 160ms ease, border-color 160ms ease, color 160ms ease, box-shadow 160ms ease;
}

.stButton > button:hover {
    border-color: rgba(31, 111, 122, 0.42);
    color: var(--ps-accent);
    transform: translateY(-1px);
    box-shadow: 0 8px 18px rgba(31, 34, 31, 0.08);
}

div[role="radiogroup"] {
    gap: 0.55rem;
    width: 100%;
}

div[role="radiogroup"] label {
    flex: 1;
    min-width: 0;
    height: 3.18rem;
    justify-content: center;
    align-items: center;
    border-radius: 999px;
    border: 1px solid rgba(36, 95, 90, 0.16);
    background: rgba(255, 253, 248, 0.72);
    padding: 0.34rem 0.86rem;
    transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
}

div[role="radiogroup"] label > div {
    display: flex;
    align-items: center;
}

div[role="radiogroup"] label > div:first-child {
    flex: 0 0 auto;
    margin-right: 0.42rem;
}

div[role="radiogroup"] label > div:last-child {
    flex: 0 1 auto;
    min-width: 0;
    white-space: nowrap;
}

div[role="radiogroup"] label p {
    white-space: nowrap;
    word-break: keep-all;
    line-height: 1.1;
    margin: 0;
    font-size: 0.96rem;
}

div[role="radiogroup"] label:hover {
    transform: translateY(-1px);
    border-color: rgba(31, 111, 122, 0.32);
    background: rgba(255, 253, 248, 0.96);
}

div[role="radiogroup"] label:has(input:checked) {
    background: linear-gradient(135deg, rgba(236, 250, 248, 0.96), rgba(255, 253, 248, 0.98));
    border-color: rgba(31, 111, 122, 0.46);
    color: #174f58;
    box-shadow: 0 10px 24px rgba(31, 111, 122, 0.12);
}

div[role="radiogroup"] label:has(input:checked) [data-testid="stMarkdownContainer"] p {
    color: #174f58;
    font-weight: 900;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: rgba(21, 25, 24, 0.055);
    border-radius: 10px;
    background: rgba(255, 253, 248, 0.70);
    box-shadow: var(--ps-tight-shadow);
    transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
    animation: psPanelBreathe 7.5s ease-in-out infinite alternate;
}

div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-2px);
    border-color: rgba(36, 95, 90, 0.20);
    box-shadow: 0 16px 36px rgba(31, 34, 31, 0.12);
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-card-sentinel) {
    transform-origin: center 72%;
    will-change: transform, opacity, filter;
    position: relative;
    overflow: visible;
    border-color: transparent !important;
    border-width: 0 !important;
    border-radius: 18px !important;
    background:
        linear-gradient(135deg, rgba(255, 247, 224, 0.44), rgba(188, 126, 48, 0.13)),
        radial-gradient(circle at 18% 8%, rgba(255, 253, 248, 0.56), transparent 34%),
        rgba(255, 244, 218, 0.26) !important;
    box-shadow:
        0 26px 54px rgba(31, 34, 31, 0.10),
        0 12px 24px rgba(161, 104, 38, 0.10),
        0 1px 0 rgba(255, 253, 248, 0.72) inset !important;
    backdrop-filter: blur(10px) saturate(1.14);
    -webkit-backdrop-filter: blur(10px) saturate(1.14);
    padding: 0.9rem 0.82rem 0.72rem 0.82rem;
    animation: psCardFloatReveal 0.72s cubic-bezier(0.22, 0.61, 0.36, 1) both;
}

div[data-testid="stElementContainer"]:has(.ps-result-card-sentinel),
div[data-testid="stVerticalBlock"]:has(.ps-result-card-sentinel),
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-card-sentinel),
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-card-sentinel) > div,
div[data-testid="stElementContainer"]:has(.ps-submission-card-sentinel),
div[data-testid="stVerticalBlock"]:has(.ps-submission-card-sentinel),
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-submission-card-sentinel),
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-submission-card-sentinel) > div {
    border: 0 !important;
    outline: 0 !important;
}

div[data-testid="stElementContainer"]:has(.ps-result-card-sentinel)::before,
div[data-testid="stElementContainer"]:has(.ps-result-card-sentinel)::after,
div[data-testid="stVerticalBlock"]:has(.ps-result-card-sentinel)::before,
div[data-testid="stVerticalBlock"]:has(.ps-result-card-sentinel)::after,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-card-sentinel)::after {
    border: 0 !important;
    outline: 0 !important;
    box-shadow: none !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-card-sentinel):hover {
    transform: translateY(-12px) scale(1.028);
    border-color: transparent !important;
    border-width: 0 !important;
    box-shadow:
        0 38px 76px rgba(31, 34, 31, 0.16),
        0 20px 40px rgba(161, 104, 38, 0.16),
        0 1px 0 rgba(255, 253, 248, 0.80) inset !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-selected) {
    border-left: 5px solid #7fb8ad !important;
    box-shadow:
        -10px 0 24px rgba(127, 184, 173, 0.26),
        0 28px 58px rgba(31, 34, 31, 0.12),
        0 13px 28px rgba(161, 104, 38, 0.12),
        0 1px 0 rgba(255, 253, 248, 0.76) inset !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-selected)::before {
    content: "";
    position: absolute;
    left: -5px;
    top: 1rem;
    bottom: 1rem;
    width: 5px;
    border-radius: 999px;
    background: linear-gradient(180deg, rgba(196, 238, 230, 0.95), rgba(77, 146, 137, 0.86));
    box-shadow: 0 0 22px rgba(127, 184, 173, 0.55);
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-card-sentinel) .stButton > button,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-submission-card-sentinel) .stButton > button,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-card-sentinel) div[data-testid="stButton"] button,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-submission-card-sentinel) div[data-testid="stButton"] button {
    width: 100%;
    min-height: 2.45rem;
    padding: 0.42rem 0.88rem;
    border-radius: 999px !important;
    border: 1px solid rgba(36, 95, 90, 0.20) !important;
    background:
        linear-gradient(135deg, rgba(255, 253, 248, 0.70), rgba(236, 250, 248, 0.46)) !important;
    color: #174f58 !important;
    font-size: 0.88rem;
    font-weight: 900;
    letter-spacing: 0.02em;
    box-shadow:
        0 12px 26px rgba(31, 34, 31, 0.08),
        0 1px 0 rgba(255, 253, 248, 0.82) inset !important;
    backdrop-filter: blur(11px) saturate(1.12);
    -webkit-backdrop-filter: blur(11px) saturate(1.12);
    cursor: pointer;
    transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease, background 180ms ease;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-card-sentinel):hover .stButton > button:hover,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-submission-card-sentinel):hover .stButton > button:hover,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-card-sentinel):hover div[data-testid="stButton"] button:hover,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-submission-card-sentinel):hover div[data-testid="stButton"] button:hover {
    transform: translateY(-3px) scale(1.025);
    background:
        linear-gradient(135deg, rgba(236, 250, 248, 0.92), rgba(255, 253, 248, 0.72)) !important;
    color: #0f4d57 !important;
    border-color: rgba(31, 111, 122, 0.42) !important;
    box-shadow:
        0 18px 34px rgba(31, 111, 122, 0.14),
        0 1px 0 rgba(255, 253, 248, 0.90) inset !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-card-sentinel) .stButton > button:active,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-submission-card-sentinel) .stButton > button:active,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-card-sentinel) div[data-testid="stButton"] button:active,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-submission-card-sentinel) div[data-testid="stButton"] button:active {
    transform: translateY(1px) scale(0.985);
    box-shadow:
        0 8px 18px rgba(31, 111, 122, 0.10),
        0 2px 8px rgba(31, 34, 31, 0.08) inset !important;
}

@supports (animation-timeline: view()) {
    div[data-testid="stVerticalBlockBorderWrapper"],
    .ps-section-title,
    .ps-soft-appear,
    .ps-image-frame {
        animation-name: psScrollReveal;
        animation-duration: 1ms;
        animation-timing-function: linear;
        animation-fill-mode: both;
        animation-timeline: view();
        animation-range: entry 0% cover 28%;
    }

    div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-card-sentinel) {
        animation-name: psCardFloatReveal;
        animation-duration: 1ms;
        animation-timing-function: linear;
        animation-fill-mode: both;
        animation-timeline: view();
        animation-range: entry -8% cover 34%;
    }
}

@media (max-width: 760px) {
    .ps-title {
        font-size: 2.05rem;
    }

    .ps-hero {
        padding: 1.35rem;
    }

    .ps-stat-strip {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    div[role="radiogroup"] {
        flex-wrap: wrap;
    }

    div[role="radiogroup"] label {
        flex-basis: calc(50% - 0.55rem);
    }

    .ps-usage-card-list {
        grid-template-columns: 1fr;
    }
}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.001ms !important;
        animation-iteration-count: 1 !important;
        scroll-behavior: auto !important;
        transition-duration: 0.001ms !important;
    }
}

</style>
"""

st.markdown(APP_CSS, unsafe_allow_html=True)


def load_backend() -> PaletteSeek:
    return PaletteSeek(
        excel_path=EXCEL_PATH,
        color_cards_dir=COLOR_CARDS_DIR,
    )


@st.cache_resource
def get_backend() -> PaletteSeek:
    return load_backend()


def split_items(value: Any) -> list[str]:
    if not value:
        return []
    text = str(value).replace("，", "、").replace(",", "、")
    return [item.strip() for item in text.split("、") if item.strip()]


def palette_bar_html(hexes: list[str], ratios: list[float]) -> str:
    if not hexes:
        return '<div class="ps-palette"><span style="flex:1;background:#d4d8dd"></span></div>'

    clean_ratios = []
    for ratio in ratios[: len(hexes)]:
        try:
            clean_ratios.append(max(float(ratio), 0.0))
        except (TypeError, ValueError):
            clean_ratios.append(0.0)

    if not clean_ratios or sum(clean_ratios) <= 0:
        clean_ratios = [1.0] * len(hexes)

    parts = []
    total = sum(clean_ratios)
    for hex_color, ratio in zip(hexes, clean_ratios):
        flex = max(ratio / total, 0.04)
        parts.append(f'<span style="flex:{flex:.6f};background:{hex_color}"></span>')
    return '<div class="ps-palette">' + "".join(parts) + "</div>"


def usage_badges(usage: dict[str, str]) -> str:
    if not usage:
        return '<div class="ps-muted-note">暂无配色建议。</div>'
    cards = []
    for key, value in usage.items():
        safe_key = html.escape(str(key))
        safe_value = html.escape(str(value))
        cards.append(
            f'<div class="ps-usage-card">'
            f'<div class="ps-usage-card-key">{safe_key}</div>'
            f'<div class="ps-usage-card-value">{safe_value}</div>'
            f'</div>'
        )
    return '<div class="ps-usage-card-list">' + "".join(cards) + "</div>"


def tag_badge_class(item: str) -> str:
    text = str(item)
    if any(word in text for word in ["蓝", "青", "冷"]):
        return "ps-badge ps-badge-blue"
    if any(word in text for word in ["红", "朱", "粉", "暖"]):
        return "ps-badge ps-badge-red"
    if any(word in text for word in ["黄", "金", "橙"]):
        return "ps-badge ps-badge-yellow"
    if any(word in text for word in ["绿", "自然", "植物"]):
        return "ps-badge ps-badge-green"
    if any(word in text for word in ["灰", "黑", "白", "中性"]):
        return "ps-badge ps-badge-neutral"
    return "ps-badge"


def render_hero(ps: PaletteSeek) -> None:
    stats = ps.stats()
    with st.container():
        st.markdown(
            f"""
            <div class="ps-hero">
                <div class="ps-help-wrap">
                    <span class="ps-help-dot">?</span>
                    <div class="ps-help-panel">
                        <div class="ps-help-title">馆藏概览 / 使用提示</div>
                        <div class="ps-stat-strip">
                            <div class="ps-stat">
                                <div class="ps-stat-head">
                                    <span class="ps-stat-icon">▧</span>
                                    <div>
                                        <div class="ps-stat-value">{stats.get("total", 0)}</div>
                                        <div class="ps-stat-label">馆藏作品</div>
                                    </div>
                                </div>
                            </div>
                            <div class="ps-stat">
                                <div class="ps-stat-head">
                                    <span class="ps-stat-icon">◒</span>
                                    <div>
                                        <div class="ps-stat-value">{len(stats.get("color_families", []))}</div>
                                        <div class="ps-stat-label">主色系</div>
                                    </div>
                                </div>
                            </div>
                            <div class="ps-stat">
                                <div class="ps-stat-head">
                                    <span class="ps-stat-icon">◍</span>
                                    <div>
                                        <div class="ps-stat-value">{len(stats.get("overall_tones", []))}</div>
                                        <div class="ps-stat-label">整体色调</div>
                                    </div>
                                </div>
                            </div>
                            <div class="ps-stat">
                                <div class="ps-stat-head">
                                    <span class="ps-stat-icon">▦</span>
                                    <div>
                                        <div class="ps-stat-value ps-stat-value-text">Excel</div>
                                        <div class="ps-stat-label">本地数据源</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="ps-muted-note" style="color:rgba(255,253,248,0.68);font-size:0.76rem;margin-top:0.68rem;">
                            关键词支持 OR / NOT；颜色检索可直接选择或粘贴 HEX；空关键词会展示全部作品。
                        </div>
                    </div>
                </div>
                <div class="ps-kicker">
                    <span style="--i:0">P</span><span style="--i:1">a</span><span style="--i:2">l</span><span style="--i:3">e</span><span style="--i:4">t</span><span style="--i:5">t</span><span style="--i:6">e</span><span style="--i:7">S</span><span style="--i:8">e</span><span style="--i:9">e</span><span style="--i:10">k</span>
                    <span style="--i:11">&nbsp;/&nbsp;</span>
                    <span style="--i:12">C</span><span style="--i:13">o</span><span style="--i:14">l</span><span style="--i:15">o</span><span style="--i:16">r</span>
                    <span style="--i:17">&nbsp;</span>
                    <span style="--i:18">A</span><span style="--i:19">r</span><span style="--i:20">c</span><span style="--i:21">h</span><span style="--i:22">i</span><span style="--i:23">v</span><span style="--i:24">e</span>
                </div>
                <div class="ps-title">
                    <span class="ps-title-cn">
                        <span style="--i:0">艺</span><span style="--i:1">术</span><span style="--i:2">作</span><span style="--i:3">品</span><span style="--i:4">配</span><span style="--i:5">色</span><span style="--i:6">检</span><span style="--i:7">索</span><span style="--i:8">馆</span>
                    </span>
                </div>
                <div class="ps-subtitle">
                    从绘画、电影海报与视觉艺术作品中提取色彩线索，把关键词、取色盘和风格标签
                    转译成可浏览、可比较、可落地的灵感档案。
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def build_filter_options(ps: PaletteSeek) -> dict[str, list[str]]:
    raw = ps.list_filter_options()
    return {
        "overall_tone": ["全部"] + raw.get("overall_tone", []),
        "color_family": ["全部"] + raw.get("color_family", []),
        "culture": ["全部"] + raw.get("culture", []),
        "classification": ["全部"] + raw.get("classification", []),
    }


def render_controls(filter_options: dict[str, list[str]]) -> dict[str, str]:
    st.markdown('<div class="ps-section-title">检索工作台 <span>/ Search Desk</span></div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="ps-workbench-note">
            先选择检索方式，再用关键词、颜色或筛选条件缩小范围。页面会把结果整理成作品档案卡，便于横向比较配色气质。
        </div>
        <div class="ps-workbench-rule"></div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.1, 0.9], gap="large")
    with left:
        mode = st.radio(
            "检索模式",
            ["混合检索", "关键词检索", "颜色检索"],
            horizontal=True,
            key="mode_select",
        )
        q_col, b_col = st.columns([0.84, 0.16], gap="small")
        with q_col:
            query = st.text_input(
                "关键词",
                value=st.session_state.get("query_text", ""),
                placeholder="例如：电影海报 深蓝、冷色 科技、蓝紫 not 暖色",
                help="支持 OR / NOT 布尔语法，例如：深蓝 or 蓝紫 not 暖色",
                key="query_text",
            )
        with b_col:
            st.markdown('<div class="ps-control-spacer"></div>', unsafe_allow_html=True)
            st.button("搜索", use_container_width=True, key="search_btn")
        st.caption("支持 OR / NOT；空关键词会默认展示全部作品。")

    with right:
        hex_text = st.color_picker(
            "HEX 色值 / 取色盘",
            value=st.session_state.get("hex_text", "#1E3A8A"),
            help="颜色检索时，可粘贴 HEX 色值，以该颜色为基准匹配配色方案。",
            key="hex_text",
        )
        st.caption("点击色块取色，或粘贴 HEX 色值；颜色检索会以该颜色为基准匹配。")
        top_k = st.number_input(
            "最大结果数量",
            min_value=1,
            value=int(st.session_state.get("top_k", 30)),
            step=1,
            help="设置本次检索最多展示多少条结果；实际结果可能少于这个数量。",
            key="top_k",
        )

    f1, f2, f3, f4, f5 = st.columns([1, 1, 1, 1, 0.8], gap="small")
    with f1:
        overall_tone = st.selectbox("整体色调", filter_options["overall_tone"], key="filter_overall_tone")
    with f2:
        color_family = st.selectbox("色系", filter_options["color_family"], key="filter_color_family")
    with f3:
        culture = st.selectbox("文化", filter_options["culture"], key="filter_culture")
    with f4:
        classification = st.selectbox("分类", filter_options["classification"], key="filter_classification")
    with f5:
        st.markdown('<div class="ps-control-spacer"></div>', unsafe_allow_html=True)
        has_active_filter = any(
            value and value != "全部"
            for value in (overall_tone, color_family, culture, classification)
        )
        reset_label = "重置筛选" if has_active_filter else "无筛选"
        st.button(reset_label, use_container_width=True, on_click=reset_filters, disabled=not has_active_filter)

    active_filters = [
        value
        for value in (overall_tone, color_family, culture, classification)
        if value and value != "全部"
    ]
    filter_note = " · ".join(active_filters) if active_filters else "未启用筛选"
    st.markdown(
        f"""
        <div class="ps-chip-row">
            <span class="ps-chip">当前模式：{mode}</span>
            <span class="ps-chip">筛选：{filter_note}</span>
            <span class="ps-chip">最多展示：{top_k} 条</span>
            <span class="ps-chip">颜色提示：HEX 可直接粘贴</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return {
        "mode": mode,
        "query": query,
        "hex_text": hex_text,
        "top_k": top_k,
        "overall_tone": overall_tone,
        "color_family": color_family,
        "culture": culture,
        "classification": classification,
    }


def build_filters(values: dict[str, str]) -> dict[str, str]:
    filters: dict[str, str] = {}
    for field, value in (
        ("overall_tone", values["overall_tone"]),
        ("color_family", values["color_family"]),
        ("culture", values["culture"]),
        ("classification", values["classification"]),
    ):
        if value and value != "全部":
            filters[field] = value
    return filters


def search_artworks(ps: PaletteSeek, values: dict[str, str]) -> tuple[list[dict], str | None]:
    filters = build_filters(values)
    mode = values["mode"]
    query = values["query"].strip()
    hex_text = values["hex_text"].strip()
    top_k = int(values["top_k"])

    if mode == "关键词检索":
        if not query:
            return ps.get_all(top_k=top_k), "关键词为空，当前展示全部作品。"
        return ps.keyword_search(query=query, top_k=top_k, filters=filters), None

    if mode == "颜色检索":
        if not is_valid_hex(hex_text):
            raise ValueError("HEX 格式不正确，请输入 6 位十六进制颜色，例如 #1E3A8A。")
        return ps.color_search(hex_color=hex_text, top_k=top_k, filters=filters), None

    if not query and not hex_text:
        return ps.get_all(top_k=top_k), "混合检索的关键词和颜色都为空，当前展示全部作品。"

    if hex_text and not is_valid_hex(hex_text):
        raise ValueError("HEX 格式不正确，请输入 6 位十六进制颜色，例如 #1E3A8A。")

    return ps.hybrid_search(query=query, hex_color=hex_text, top_k=top_k, filters=filters), None


def ensure_selected_card(results: list[dict]) -> dict | None:
    if not results:
        return None

    selected_id = st.session_state.get("selected_card_id")
    if selected_id is not None:
        for item in results:
            if str(item.get("id")) == str(selected_id):
                return item

    st.session_state.selected_card_id = str(results[0].get("id"))
    return results[0]


def select_card(card_id: str) -> None:
    st.session_state.selected_card_id = str(card_id)
    st.session_state.scroll_to_detail = True


def toggle_report(card_id: str) -> None:
    st.session_state.report_card_id = str(card_id)
    st.session_state.show_report = True
    st.session_state.scroll_to_detail = True


def close_report() -> None:
    st.session_state.show_report = False


def select_submission(submission_id: str) -> None:
    st.session_state.selected_submission_id = str(submission_id)
    st.session_state.scroll_to_submission_detail = True


def toggle_submission_report(submission_id: str) -> None:
    st.session_state.submission_report_id = str(submission_id)
    st.session_state.show_submission_report = True
    st.session_state.scroll_to_submission_detail = True


def close_submission_report() -> None:
    st.session_state.show_submission_report = False


def toggle_upload_form() -> None:
    st.session_state.show_upload_form = not bool(st.session_state.get("show_upload_form"))


def activate_detail_scroll() -> None:
    if st.session_state.get("scroll_to_detail"):
        st.session_state.scroll_trigger_nonce = int(st.session_state.get("scroll_trigger_nonce", 0)) + 1
        scroll_to_detail()
        st.session_state.scroll_to_detail = False


def activate_submission_detail_scroll() -> None:
    if st.session_state.get("scroll_to_submission_detail"):
        st.session_state.submission_scroll_nonce = int(st.session_state.get("submission_scroll_nonce", 0)) + 1
        scroll_to_anchor("ps-submission-detail-anchor", "submission_scroll_nonce")
        st.session_state.scroll_to_submission_detail = False


def reset_filters() -> None:
    st.session_state.selected_card_id = None
    st.session_state.query_text = ""
    st.session_state.hex_text = "#1E3A8A"
    st.session_state.top_k = 30
    st.session_state.mode_select = "混合检索"
    st.session_state.filter_overall_tone = "全部"
    st.session_state.filter_color_family = "全部"
    st.session_state.filter_culture = "全部"
    st.session_state.filter_classification = "全部"
    st.session_state.show_report = False
    st.session_state.report_card_id = None


def get_report_path(card_id: str) -> Path:
    return REPORTS_DIR / f"{card_id}_palette_report.png"


def get_submission_report_path(submission_id: str) -> Path:
    safe_id = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in str(submission_id))
    return SUBMISSION_REPORTS_DIR / f"{safe_id}_palette_report.png"


def ensure_report_image(card: dict) -> Path | None:
    report_path = get_report_path(str(card.get("id", "")))
    if report_path.exists():
        return report_path

    try:
        from paletteseek_backend import render_palette_report_from_artwork
    except Exception:
        return None

    try:
        return render_palette_report_from_artwork(
            excel_path=EXCEL_PATH,
            artwork_id=card.get("id"),
            output_path=report_path,
        )
    except Exception:
        return None


def ensure_submission_report_image(card: dict) -> Path | None:
    report_path = get_submission_report_path(str(card.get("submission_id") or card.get("id") or ""))
    if report_path.exists():
        return report_path

    try:
        from paletteseek_backend import render_palette_report
    except Exception:
        return None

    try:
        return render_palette_report(card, report_path)
    except Exception:
        return None


def image_to_data_uri(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    try:
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"
    except Exception:
        return None


def parse_json_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    text = str(value or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


def normalize_uploaded_image(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA"):
        background = Image.new("RGB", image.size, "#FFFFFF")
        alpha = image.getchannel("A") if image.mode == "RGBA" else image.getchannel("A")
        background.paste(image.convert("RGBA"), mask=alpha)
        return background
    return image.convert("RGB")


def extract_palette_from_image(image: Image.Image, max_colors: int = 9) -> tuple[list[str], list[float]]:
    work = normalize_uploaded_image(image)
    resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
    work.thumbnail((420, 420), resampling)

    quantize_enum = getattr(Image, "Quantize", None)
    quantize_method = getattr(quantize_enum, "MEDIANCUT", 0) if quantize_enum else 0
    quantized = work.quantize(colors=max_colors, method=quantize_method)
    colors = quantized.getcolors(work.size[0] * work.size[1]) or []
    colors.sort(reverse=True, key=lambda item: item[0])

    palette = quantized.getpalette() or []
    total = sum(count for count, _ in colors) or 1
    hexes: list[str] = []
    ratios: list[float] = []
    for count, palette_index in colors[:max_colors]:
        base = int(palette_index) * 3
        if base + 2 >= len(palette):
            continue
        hex_value = rgb_to_hex(palette[base], palette[base + 1], palette[base + 2])
        if hex_value in hexes:
            continue
        hexes.append(hex_value)
        ratios.append(round(count / total, 6))

    ratio_total = sum(ratios)
    if ratio_total > 0:
        ratios = [round(ratio / ratio_total, 6) for ratio in ratios]
    return hexes, ratios


def infer_overall_tone(hexes: list[str], ratios: list[float]) -> str:
    if not hexes:
        return "未标注色调"

    import colorsys

    weights = ratios if len(ratios) == len(hexes) and sum(ratios) > 0 else [1 / len(hexes)] * len(hexes)
    total = sum(weights) or 1
    brightness = 0.0
    saturation = 0.0
    for hex_value, weight in zip(hexes, weights):
        clean = hex_value.lstrip("#")
        try:
            r, g, b = int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16)
        except Exception:
            continue
        _, sat, val = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        brightness += val * weight
        saturation += sat * weight
    brightness /= total
    saturation /= total

    if brightness < 0.34:
        return "深色调"
    if brightness > 0.74:
        return "浅色调"
    if saturation < 0.24:
        return "低饱和色调"
    return "中明度色调"


def dominant_family_from_palette(hexes: list[str], ratios: list[float]) -> str:
    if not hexes:
        return "未标注色系"
    weights = ratios if len(ratios) == len(hexes) and sum(ratios) > 0 else [1 / len(hexes)] * len(hexes)
    family_weights: dict[str, float] = {}
    family_order: list[str] = []
    for hex_value, weight in zip(hexes, weights):
        family = classify_hex_family(hex_value)
        if family not in family_weights:
            family_weights[family] = 0.0
            family_order.append(family)
        family_weights[family] += float(weight)
    return max(family_order, key=lambda item: family_weights[item]) if family_order else "未标注色系"


def submission_image_path(raw_path: Any) -> Path | None:
    text = str(raw_path or "").strip()
    if not text:
        return None
    path = Path(text)
    if not path.is_absolute():
        path = BACKEND_PACKAGE_DIR / path
    return path


def load_submissions() -> list[dict]:
    if not SUBMISSIONS_FILE.exists():
        return []
    try:
        import pandas as pd

        df = pd.read_excel(SUBMISSIONS_FILE, dtype=str).fillna("")
    except Exception:
        return []

    records: list[dict] = []
    for _, row in df.iterrows():
        rec = {str(key): str(value) for key, value in row.to_dict().items()}
        rec["palette_hexes"] = [str(item) for item in parse_json_list(rec.get("palette_hexes"))]
        rec["palette_ratios"] = [
            float(item) for item in parse_json_list(rec.get("palette_ratios")) if str(item).strip()
        ]
        rec["id"] = rec.get("submission_id", "")
        rec["source_type"] = "user_submission"
        local_image_path = submission_image_path(rec.get("image_path"))
        rec["local_image_path"] = str(local_image_path or "")
        rec["image_url"] = str(local_image_path or "")
        rec["color_tags"] = rec.get("color_family", "")
        rec["emotion_tags"] = rec.get("tags", "")
        rec["style_tags"] = rec.get("classification", "")
        rec["use_tags"] = rec.get("usage_note", "")
        rec["color_names"] = [f"Color {idx:02d}" for idx, _ in enumerate(rec["palette_hexes"], start=1)]
        rec["usage_suggestion"] = generate_usage_suggestion(rec)
        records.append(rec)
    records.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return records


def save_submission(uploaded_file: Any, fields: dict[str, str]) -> tuple[bool, str]:
    title = fields.get("title", "").strip()
    if not uploaded_file:
        return False, "请先上传一张 JPG 或 PNG 图片。"
    if not title:
        return False, "请至少填写作品标题，方便在开放区中识别。"

    raw_bytes = uploaded_file.getvalue()
    try:
        image = Image.open(BytesIO(raw_bytes))
        image.verify()
        image = Image.open(BytesIO(raw_bytes))
    except Exception:
        return False, "图片无法读取，请更换 JPG 或 PNG 文件。"

    hexes, ratios = extract_palette_from_image(image)
    if not hexes:
        return False, "暂时无法从这张图片中提取有效调色盘。"

    SUBMISSIONS_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(uploaded_file.name or "").suffix.lower()
    if suffix not in (".jpg", ".jpeg", ".png", ".webp"):
        suffix = ".png"
    digest = hashlib.sha1(raw_bytes).hexdigest()[:10]
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    submission_id = f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{digest}"
    image_filename = f"{submission_id}{suffix}"
    image_path = SUBMISSIONS_IMAGES_DIR / image_filename
    image_path.write_bytes(raw_bytes)

    record = {
        "submission_id": submission_id,
        "id": submission_id,
        "title": title,
        "artist": fields.get("artist", "").strip() or "用户未填写",
        "year": fields.get("year", "").strip() or "未知年份",
        "culture": fields.get("culture", "").strip() or "用户上传",
        "classification": fields.get("classification", "").strip() or "视觉作品",
        "medium": fields.get("medium", "").strip() or "用户上传图片",
        "source_url": fields.get("source_url", "").strip(),
        "tags": fields.get("tags", "").strip(),
        "usage_note": fields.get("usage_note", "").strip(),
        "image_path": str(Path("submissions_images") / image_filename),
        "palette_hexes": json.dumps(hexes, ensure_ascii=False),
        "palette_ratios": json.dumps(ratios, ensure_ascii=False),
        "overall_tone": infer_overall_tone(hexes, ratios),
        "color_family": dominant_family_from_palette(hexes, ratios),
        "created_at": created_at,
        "source_type": "user_submission",
    }

    try:
        import pandas as pd

        existing = pd.read_excel(SUBMISSIONS_FILE, dtype=str).fillna("") if SUBMISSIONS_FILE.exists() else pd.DataFrame()
        updated = pd.concat([existing, pd.DataFrame([record])], ignore_index=True)
        updated.to_excel(SUBMISSIONS_FILE, index=False)
    except Exception as exc:
        if image_path.exists():
            image_path.unlink()
        return False, f"保存失败：{exc}"

    return True, "作品已保存到开放区，不会进入正式馆藏检索结果。"


def build_submission_filter_options(submissions: list[dict]) -> dict[str, list[str]]:
    options: dict[str, list[str]] = {}
    for field in ("overall_tone", "color_family", "culture", "classification"):
        values = sorted({str(item.get(field, "")).strip() for item in submissions if str(item.get(field, "")).strip()})
        options[field] = ["全部"] + values
    return options


def render_submission_controls(submissions: list[dict]) -> dict[str, Any]:
    filter_options = build_submission_filter_options(submissions)
    st.markdown('<div class="ps-label">检索台</div>', unsafe_allow_html=True)
    mode = st.radio(
        "检索模式",
        ["混合检索", "关键词检索", "颜色检索"],
        horizontal=True,
        key="submission_mode_select",
    )
    q_col, c_col = st.columns([0.62, 0.38], gap="small")
    with q_col:
        query = st.text_input(
            "关键词",
            value=st.session_state.get("submission_query_text", ""),
            placeholder="例如：海报 蓝色 梦幻 not 暖色",
            key="submission_query_text",
        )
    with c_col:
        hex_text = st.color_picker(
            "颜色",
            value=st.session_state.get("submission_hex_text", "#1E3A8A"),
            key="submission_hex_text",
        )

    f1, f2, f3, f4, f5 = st.columns([1, 1, 1, 1, 0.8], gap="small")
    with f1:
        overall_tone = st.selectbox("整体色调", filter_options["overall_tone"], key="submission_filter_overall_tone")
    with f2:
        color_family = st.selectbox("色系", filter_options["color_family"], key="submission_filter_color_family")
    with f3:
        culture = st.selectbox("文化", filter_options["culture"], key="submission_filter_culture")
    with f4:
        classification = st.selectbox("分类", filter_options["classification"], key="submission_filter_classification")
    with f5:
        top_k = st.number_input(
            "最大结果数量",
            min_value=1,
            value=int(st.session_state.get("submission_top_k", 30)),
            step=1,
            key="submission_top_k",
        )

    return {
        "mode": mode,
        "query": query,
        "hex_text": hex_text,
        "top_k": int(top_k),
        "overall_tone": overall_tone,
        "color_family": color_family,
        "culture": culture,
        "classification": classification,
    }


def submission_search_text(item: dict) -> str:
    fields = [
        "title", "artist", "year", "culture", "classification", "medium",
        "overall_tone", "color_family", "tags", "usage_note", "source_url",
    ]
    return " ".join(str(item.get(field, "")) for field in fields).lower()


def keyword_score_for_submission(query: str, item: dict) -> float:
    text = submission_search_text(item)
    raw = query.strip().lower()
    if not raw:
        return 1.0

    not_terms: list[str] = []
    if " not " in f" {raw} ":
        chunks = raw.split(" not ")
        raw = chunks[0].strip()
        not_terms = [term.strip() for chunk in chunks[1:] for term in chunk.replace("，", " ").split() if term.strip()]
    if any(term in text for term in not_terms):
        return 0.0

    or_terms = [term.strip() for term in raw.replace(" or ", " OR ").split(" OR ") if term.strip()]
    if len(or_terms) > 1:
        return 1.0 if any(term in text for term in or_terms) else 0.0

    terms = [term.strip() for term in raw.replace("，", " ").split() if term.strip()]
    if not terms:
        return 1.0
    matched = sum(1 for term in terms if term in text)
    return matched / len(terms)


def filter_submission_records(submissions: list[dict], values: dict[str, Any]) -> list[dict]:
    filtered = submissions
    for field in ("overall_tone", "color_family", "culture", "classification"):
        value = str(values.get(field, "")).strip()
        if value and value != "全部":
            filtered = [item for item in filtered if value in str(item.get(field, ""))]
    return filtered


def search_submissions(submissions: list[dict], values: dict[str, Any]) -> tuple[list[dict], str | None]:
    candidates = filter_submission_records(submissions, values)
    mode = str(values.get("mode", "混合检索"))
    query = str(values.get("query", "")).strip()
    hex_text = str(values.get("hex_text", "")).strip()
    top_k = int(values.get("top_k", 9))
    scored: list[dict] = []

    if mode in ("颜色检索", "混合检索") and hex_text and not is_valid_hex(hex_text):
        raise ValueError("颜色检索的 HEX 格式不正确。")

    for item in candidates:
        text_score = keyword_score_for_submission(query, item) if mode in ("关键词检索", "混合检索") else 1.0
        color_score = (
            palette_color_similarity(hex_text, item.get("palette_hexes", []), item.get("palette_ratios", []))
            if mode in ("颜色检索", "混合检索") and hex_text
            else 1.0
        )

        if mode == "关键词检索":
            score = text_score
        elif mode == "颜色检索":
            score = color_score
        else:
            score = 0.52 * text_score + 0.48 * color_score if query else color_score

        if score <= 0:
            continue
        scored.append({
            **item,
            "_score": round(float(score), 6),
            "_reason": "来自开放区；仅在开放区数据内检索，不进入正式馆藏。",
        })

    scored.sort(key=lambda item: (float(item.get("_score", 0)), str(item.get("created_at", ""))), reverse=True)
    results = scored[:top_k]
    for idx, item in enumerate(results, start=1):
        item["_rank"] = idx
    note = "关键词为空，当前展示开放区作品。" if mode == "关键词检索" and not query else None
    return results, note


def resolve_ring_image_src(card: dict) -> str:
    image_url = str(card.get("image_url", "")).strip()
    if not image_url:
        return ""
    if image_url.startswith(("http://", "https://", "data:")):
        return image_url
    try:
        image_path = Path(image_url)
        if image_path.exists():
            return image_to_data_uri(image_path) or ""
    except Exception:
        pass
    return ""


def render_palette_copy_tools(hexes: list[str]) -> None:
    clean_hexes = [str(item).strip() for item in hexes if str(item).strip()]
    if not clean_hexes:
        return

    payload = json.dumps(clean_hexes, ensure_ascii=False)
    components.html(
        f"""
        <div class="ps-copy-widget">
          <button type="button" class="ps-copy-all" data-palette='{payload}'>复制全套色值</button>
          <div class="ps-copy-list">
            {''.join(f'<button type="button" class="ps-copy-one" data-hex="{hex_color}">{hex_color}</button>' for hex_color in clean_hexes[:8])}
          </div>
          <div class="ps-copy-status" aria-live="polite">点击色号即可复制 HEX。</div>
        </div>
        <style>
          body {{
            margin: 0;
            background: transparent;
            font-family: "Kaiti SC", "STKaiti", "Songti SC", serif;
          }}
          .ps-copy-widget {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 8px;
            color: #68716f;
            font-size: 12px;
          }}
          .ps-copy-all,
          .ps-copy-one {{
            border: 1px solid rgba(36, 95, 90, 0.20);
            border-radius: 999px;
            background: rgba(255, 253, 248, 0.92);
            color: #151918;
            padding: 7px 11px;
            cursor: pointer;
            font-weight: 700;
            transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
          }}
          .ps-copy-all {{
            background: #182433;
            color: #fffdf8;
            border-color: #182433;
          }}
          .ps-copy-all:hover,
          .ps-copy-one:hover {{
            transform: translateY(-1px);
            border-color: rgba(31, 111, 122, 0.42);
            background: rgba(255, 253, 248, 1);
          }}
          .ps-copy-all:hover {{
            background: #1f6f7a;
            color: #fffdf8;
          }}
          .ps-copy-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
          }}
          .ps-copy-status {{
            flex-basis: 100%;
            color: #68716f;
            line-height: 1.4;
          }}
        </style>
        <script>
          const status = document.querySelector(".ps-copy-status");
          async function copyText(text) {{
            try {{
              await navigator.clipboard.writeText(text);
              status.textContent = "已复制：" + text;
            }} catch (err) {{
              status.textContent = "复制失败，请手动选择色值。";
            }}
          }}
          document.querySelector(".ps-copy-all").addEventListener("click", (event) => {{
            const values = JSON.parse(event.currentTarget.dataset.palette || "[]");
            copyText(values.join(" "));
          }});
          document.querySelectorAll(".ps-copy-one").forEach((button) => {{
            button.addEventListener("click", () => copyText(button.dataset.hex || ""));
          }});
        </script>
        """,
        height=106,
    )


def scroll_to_anchor(anchor_id: str, nonce_key: str = "scroll_trigger_nonce") -> None:
    nonce = int(st.session_state.get(nonce_key, 0))
    safe_anchor_id = json.dumps(anchor_id)
    safe_nonce_key = json.dumps(nonce_key)
    components.html(
        f"""
        <script>
          (function () {{
            const triggerNonce = {nonce};
            const delays = [80, 220, 420, 760];
            const anchorId = {safe_anchor_id};
            const nonceKey = {safe_nonce_key};
            const offsetGap = 18;

            function jumpToAnchor() {{
              try {{
                const doc = window.parent && window.parent.document ? window.parent.document : null;
                if (!doc) {{
                  return false;
                }}
                const anchor = doc.getElementById(anchorId);
                if (!anchor) {{
                  return false;
                }}
                const scrollTarget =
                  doc.scrollingElement ||
                  doc.documentElement ||
                  doc.body ||
                  null;
                const rect = anchor.getBoundingClientRect();
                const currentTop = scrollTarget && typeof scrollTarget.scrollTop === "number"
                  ? scrollTarget.scrollTop
                  : (window.parent.pageYOffset || 0);
                const targetTop = Math.max(0, rect.top + currentTop - offsetGap);
                if (scrollTarget && typeof scrollTarget.scrollTo === "function") {{
                  scrollTarget.scrollTo({{ top: targetTop, behavior: "smooth" }});
                }}
                if (typeof window.parent.scrollTo === "function") {{
                  window.parent.scrollTo({{ top: targetTop, behavior: "smooth" }});
                }}
                anchor.scrollIntoView({{ behavior: "smooth", block: "start", inline: "nearest" }});
                return true;
              }} catch (err) {{
                return false;
              }}
            }}

            delays.forEach((delay) => {{
              window.setTimeout(() => {{
                try {{
                  window.parent.__psScrollNonceMap = window.parent.__psScrollNonceMap || {{}};
                  if (window.parent.__psScrollNonceMap[nonceKey] === triggerNonce) {{
                    return;
                  }}
                  window.parent.__psScrollNonceMap[nonceKey] = triggerNonce;
                  if (!jumpToAnchor()) {{
                    const doc = window.parent && window.parent.document ? window.parent.document : null;
                    const anchor = doc ? doc.getElementById(anchorId) : null;
                    if (anchor && typeof anchor.scrollIntoView === "function") {{
                      anchor.scrollIntoView({{ behavior: "smooth", block: "start", inline: "nearest" }});
                    }}
                  }}
                }} catch (err) {{
                  // ignore
                }}
              }}, delay);
            }});
          }})();
        </script>
        """,
        height=1,
    )


def scroll_to_detail() -> None:
    scroll_to_anchor("ps-detail-anchor", "scroll_trigger_nonce")


def render_result_card(card: dict, selected: bool = False) -> None:
    palette_html = palette_bar_html(card.get("palette_hexes", []), card.get("palette_ratios", []))
    rank = card.get("_rank", "")
    image_src = resolve_ring_image_src(card)
    card_id = str(card.get("id", ""))
    source_url = str(card.get("source_url", "") or "").strip()
    safe_source_url = html.escape(source_url, quote=True)

    with st.container(border=True):
        st.markdown('<span class="ps-result-card-sentinel"></span>', unsafe_allow_html=True)
        if selected:
            st.markdown('<span class="ps-result-selected"></span>', unsafe_allow_html=True)
            st.markdown('<span class="ps-result-pin">正在查看</span>', unsafe_allow_html=True)

        if image_src:
            st.markdown(
                f"""
                <div class="ps-result-image" title="点击查看作品详情">
                    <img src="{image_src}" alt="{html.escape(str(card.get("title", "未命名作品")), quote=True)}" />
                    <span class="ps-rank-mark">{rank}</span>
                    <div class="ps-result-cover-caption">
                        <div class="ps-result-cover-title">{card.get("title", "未命名作品")}</div>
                        <div class="ps-result-cover-meta">
                            {card.get("artist", "未知作者")} · {card.get("year", "未知年份")}
                            <br />
                            {card.get("overall_tone", "未标注色调")} · {card.get("color_family", "未标注色系")}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="ps-result-image" title="点击查看作品详情" style="display:grid;place-items:center;color:var(--ps-muted);font-weight:700;"><span class="ps-rank-mark">{rank}</span>暂无原作图</div>',
                unsafe_allow_html=True,
            )
        st.button(
            "卡片详情",
            key=f"image_detail_{card_id}",
            on_click=select_card,
            args=(card_id,),
        )
        if source_url:
            st.markdown(
                f'<div class="ps-result-source-link"><a href="{safe_source_url}" target="_blank" rel="noreferrer">来源链接</a></div>',
                unsafe_allow_html=True,
            )
        st.markdown(f'<div class="ps-result-palette">{palette_html}</div>', unsafe_allow_html=True)


def render_results(results: list[dict]) -> None:
    st.markdown(f'<div class="ps-section-title">检索结果 <span>/ {len(results)} items</span></div>', unsafe_allow_html=True)
    if not results:
        st.info("没有找到匹配结果。可以尝试扩大关键词范围、调高最大结果数量或更换颜色。")
        return
    st.markdown(
        """
        <div class="ps-source-note">
            素材来源以 Wikimedia Commons 与本地整理数据为主；部分作品的官方来源信息可能未完整提供，可在卡片底部查看来源链接。
        </div>
        """,
        unsafe_allow_html=True,
    )

    count = len(results)
    if count >= 25:
        column_count = 5
    elif count >= 13:
        column_count = 4
    elif count >= 7:
        column_count = 3
    else:
        column_count = 2

    selected_id = str(st.session_state.get("selected_card_id") or "")
    for row_start in range(0, len(results), column_count):
        row_cards = results[row_start : row_start + column_count]
        row_columns = st.columns(column_count, gap="large")
        for idx, card in enumerate(row_cards):
            with row_columns[idx]:
                render_result_card(
                    card,
                    selected=str(card.get("id")) == selected_id,
                )
        st.markdown('<div class="ps-shelf-rail"><span></span></div>', unsafe_allow_html=True)


def render_submission_card(item: dict, selected: bool = False) -> None:
    image_path = submission_image_path(item.get("image_path"))
    image_src = image_to_data_uri(image_path) or ""
    palette_html = palette_bar_html(item.get("palette_hexes", []), item.get("palette_ratios", []))
    title = html.escape(str(item.get("title", "未命名上传作品")))
    artist = html.escape(str(item.get("artist", "用户未填写")))
    year = html.escape(str(item.get("year", "未知年份")))
    classification = html.escape(str(item.get("classification", "视觉作品")))
    tone = html.escape(str(item.get("overall_tone", "未标注色调")))
    family = html.escape(str(item.get("color_family", "未标注色系")))
    tags = html.escape(str(item.get("tags", "")))
    usage_note = html.escape(str(item.get("usage_note", "")))
    created_at = html.escape(str(item.get("created_at", "")))
    source_url = str(item.get("source_url", "") or "").strip()
    submission_id = str(item.get("submission_id") or item.get("id") or "")

    with st.container(border=True):
        st.markdown('<span class="ps-submission-card-sentinel"></span>', unsafe_allow_html=True)
        if selected:
            st.markdown('<span class="ps-result-pin">正在查看</span>', unsafe_allow_html=True)
        if image_src:
            st.markdown(
                f"""
                <div class="ps-result-image">
                    <img src="{image_src}" alt="{title}" />
                    <span class="ps-submission-badge" style="position:absolute;left:0.72rem;top:0.72rem;z-index:4;margin:0;">用户上传</span>
                    <div class="ps-result-cover-caption">
                        <div class="ps-result-cover-title">{title}</div>
                        <div class="ps-result-cover-meta">{artist} · {year}<br />{tone} · {family}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="ps-result-image" style="display:grid;place-items:center;color:var(--ps-muted);font-weight:800;">上传图片未找到</div>',
                unsafe_allow_html=True,
            )
        st.button(
            "卡片详情",
            key=f"submission_detail_{submission_id}",
            on_click=select_submission,
            args=(submission_id,),
        )
        st.markdown(f'<div class="ps-result-palette">{palette_html}</div>', unsafe_allow_html=True)
        st.markdown('<div class="ps-submission-badge">未经馆藏核验</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ps-submission-title">{title}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="ps-submission-meta">{artist} · {year} · {classification}<br />{tone} · {family}</div>',
            unsafe_allow_html=True,
        )
        if tags or usage_note:
            note_parts = [part for part in (tags, usage_note) if part]
            st.markdown(f'<div class="ps-submission-note">{" · ".join(note_parts)}</div>', unsafe_allow_html=True)
        if source_url:
            safe_source_url = html.escape(source_url, quote=True)
            st.markdown(
                f'<div class="ps-result-source-link"><a href="{safe_source_url}" target="_blank" rel="noreferrer">来源链接</a></div>',
                unsafe_allow_html=True,
            )
        if created_at:
            st.caption(f"提交时间：{created_at}")


def render_submission_wall(submissions: list[dict]) -> None:
    if not submissions:
        st.info("还没有用户上传作品。上传第一张作品后，它会出现在这里，并与正式馆藏分开展示。")
        return

    st.markdown(
        """
        <div class="ps-source-note">
            用户上传作品不会进入正式馆藏检索结果；作品信息由上传者填写，尚未经过馆藏核验。
        </div>
        """,
        unsafe_allow_html=True,
    )
    column_count = 3 if len(submissions) >= 3 else max(len(submissions), 1)
    selected_id = str(st.session_state.get("selected_submission_id") or "")
    for row_start in range(0, len(submissions), column_count):
        row_items = submissions[row_start : row_start + column_count]
        cols = st.columns(column_count, gap="large")
        for idx, item in enumerate(row_items):
            with cols[idx]:
                render_submission_card(
                    item,
                    selected=str(item.get("submission_id") or item.get("id")) == selected_id,
                )
        st.markdown('<div class="ps-shelf-rail"><span></span></div>', unsafe_allow_html=True)


def ensure_selected_submission(results: list[dict]) -> dict | None:
    if not results:
        return None
    selected_id = st.session_state.get("selected_submission_id")
    if selected_id is not None:
        for item in results:
            if str(item.get("submission_id") or item.get("id")) == str(selected_id):
                return item
    st.session_state.selected_submission_id = str(results[0].get("submission_id") or results[0].get("id"))
    return results[0]


def render_submission_detail_panel(card: dict | None) -> None:
    st.markdown('<div id="ps-submission-detail-anchor" class="ps-detail-anchor"></div>', unsafe_allow_html=True)
    st.markdown('<div class="ps-section-title">上传档案 <span>/ Upload File</span></div>', unsafe_allow_html=True)
    if not card:
        st.info("请选择一张用户上传作品查看详情。")
        return

    card_id = str(card.get("submission_id") or card.get("id"))
    show_report_face = bool(
        st.session_state.get("show_submission_report")
        and str(st.session_state.get("submission_report_id")) == card_id
    )

    with st.container(border=True):
        st.markdown('<span class="ps-detail-shell-sentinel"></span>', unsafe_allow_html=True)
        head_left, head_right = st.columns([0.82, 0.18], gap="large")
        with head_left:
            st.markdown(
                f"""
                <div class="ps-detail-title">{html.escape(str(card.get("title", "未命名上传作品")))}</div>
                <div class="ps-muted-note">
                    <span class="ps-view-tab">{"分析报告" if show_report_face else "作品详情"}</span>
                    &nbsp; {html.escape(str(card.get("artist", "用户未填写")))} · {html.escape(str(card.get("year", "未知年份")))}
                    · 用户上传 · 未经馆藏核验
                </div>
                """,
                unsafe_allow_html=True,
            )
        with head_right:
            st.markdown('<div class="ps-control-spacer"></div>', unsafe_allow_html=True)
            if show_report_face:
                st.button("返回详情", use_container_width=True, key=f"submission_back_{card_id}", on_click=close_submission_report)
            else:
                st.button(
                    "查看分析报告",
                    use_container_width=True,
                    key=f"submission_report_{card_id}",
                    on_click=toggle_submission_report,
                    args=(card_id,),
                )

        if show_report_face:
            report_image = ensure_submission_report_image(card)
            if report_image is None:
                st.warning("分析报告暂时无法生成。请检查上传图片是否仍存在。")
            else:
                st.markdown(
                    f"""
                    <div class="ps-soft-appear">
                        <div class="ps-face-chip" style="margin: 0.8rem 0 0.9rem 0;">
                            <span>报告模式</span>
                            <span>·</span>
                            <span>仅基于用户上传图片和自动调色盘生成</span>
                        </div>
                        <div class="ps-report-shell">
                            <div class="ps-scroll-report">
                                <div class="ps-scroll-paper">
                                    <img src="{image_to_data_uri(report_image) or ''}" alt="分析报告" />
                                </div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            return

        st.markdown('<div class="ps-soft-appear">', unsafe_allow_html=True)
        left, right = st.columns([1.05, 1.15], gap="large")

        with left:
            st.markdown('<div class="ps-label">原图</div>', unsafe_allow_html=True)
            image_path = submission_image_path(card.get("image_path"))
            if image_path and image_path.exists():
                st.markdown('<div class="ps-image-frame">', unsafe_allow_html=True)
                st.image(str(image_path), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.caption("上传图片未找到。")

        with right:
            st.markdown(
                f"""
                <div class="ps-detail-file-title">
                    <strong>{html.escape(str(card.get("title", "未命名上传作品")))}</strong>
                    <span>{html.escape(str(card.get("artist", "用户未填写")))} · {html.escape(str(card.get("year", "未知年份")))} · 用户上传</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown('<div class="ps-label">基础信息</div>', unsafe_allow_html=True)
            info_cols = st.columns(2)
            info_map = [
                ("媒介", card.get("medium", "")),
                ("整体色调", card.get("overall_tone", "")),
                ("主色系", card.get("color_family", "")),
                ("分类", card.get("classification", "")),
            ]
            for idx, (label, value) in enumerate(info_map):
                with info_cols[idx % 2]:
                    st.markdown(f"**{label}**")
                    st.caption(str(value or "暂无"))

            source_url = str(card.get("source_url", "") or "").strip()
            if source_url:
                st.markdown(
                    f'<div class="ps-card-footer-note" style="justify-content:flex-start;"><a href="{html.escape(source_url, quote=True)}" target="_blank" rel="noreferrer">查看来源</a></div>',
                    unsafe_allow_html=True,
                )

            st.markdown('<div class="ps-detail-divider"></div>', unsafe_allow_html=True)
            st.markdown('<div class="ps-label" style="margin-top:0.9rem;">调色盘</div>', unsafe_allow_html=True)
            st.markdown(palette_bar_html(card.get("palette_hexes", []), card.get("palette_ratios", [])), unsafe_allow_html=True)
            swatch_cols = st.columns(min(max(len(card.get("palette_hexes", [])), 1), 5))
            palette_hexes = card.get("palette_hexes", [])
            palette_ratios = card.get("palette_ratios", [])
            for idx, hex_color in enumerate(palette_hexes[:5]):
                with swatch_cols[idx % len(swatch_cols)]:
                    ratio = palette_ratios[idx] if idx < len(palette_ratios) else 0
                    st.markdown(
                        f"""
                        <div class="ps-swatch">
                            <div class="ps-swatch-color" style="background:{hex_color};"></div>
                            <div class="ps-swatch-name">Color {idx + 1:02d}</div>
                            <div class="ps-swatch-hex">{hex_color}</div>
                            <div class="ps-swatch-hex">占比 {ratio:.2%}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            render_palette_copy_tools(palette_hexes)

            st.markdown('<div class="ps-detail-divider"></div>', unsafe_allow_html=True)
            st.markdown('<div class="ps-label" style="margin-top:0.9rem;">配色用途建议</div>', unsafe_allow_html=True)
            st.markdown(usage_badges(card.get("usage_suggestion", {})), unsafe_allow_html=True)

            st.markdown('<div class="ps-detail-divider"></div>', unsafe_allow_html=True)
            st.markdown('<div class="ps-label" style="margin-top:0.9rem;">标签</div>', unsafe_allow_html=True)
            tag_items = split_items(card.get("tags", "")) + split_items(card.get("usage_note", ""))
            if tag_items:
                st.markdown(
                    '<div class="ps-badge-list">'
                    + "".join(f'<span class="{tag_badge_class(item)}">{html.escape(item)}</span>' for item in tag_items[:16])
                    + "</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.caption("暂无标签。")

            st.markdown('<div class="ps-detail-divider"></div>', unsafe_allow_html=True)
            st.markdown('<div class="ps-label" style="margin-top:0.9rem;">检索信息</div>', unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="ps-search-note">
                    数据源：开放区 · 不进入正式馆藏
                    <br />
                    排名：#{card.get("_rank", "")} · 得分：{card.get("_score", 0.0):.3f}
                    <br />
                    提交时间：{html.escape(str(card.get("created_at", "暂无")))}
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)


def render_submission_section() -> None:
    st.markdown("---")
    st.markdown(
        """
        <div class="ps-section-title">
            用户上传 <span>/ Community Uploads</span>
            <span class="ps-section-help">
                <span class="ps-section-help-dot">?</span>
                <span class="ps-section-help-panel">
                    这里是开放上传区：用户可以上传自己的图片并填写基础信息，系统会自动提取调色盘。
                    上传内容只展示在本区域，不进入正式馆藏检索结果，也不会影响原有数据质量。
                </span>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.button(
        "上传作品" if not st.session_state.get("show_upload_form") else "收起上传表单",
        use_container_width=True,
        key="toggle_upload_form_btn",
        on_click=toggle_upload_form,
    )

    notice = st.session_state.pop("submission_notice", None)
    if notice:
        level, message = notice
        if level == "success":
            st.success(message)
        else:
            st.error(message)

    if st.session_state.get("show_upload_form"):
        with st.container(border=True):
            st.markdown('<span class="ps-upload-scroll-sentinel"></span>', unsafe_allow_html=True)
            st.markdown('<div class="ps-label">上传作品</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="ps-upload-mini-note">填写基础信息后，系统会自动提取调色盘，并把作品保存到开放区。</div>',
                unsafe_allow_html=True,
            )
            with st.form("community_submission_form", clear_on_submit=True):
                uploaded = st.file_uploader(
                    "作品图片",
                    type=["jpg", "jpeg", "png", "webp"],
                    help="上传后系统会自动提取主色调色盘。",
                )
                title = st.text_input("作品标题 *", placeholder="例如：雨夜的蓝色海报")
                artist = st.text_input("作者 / 上传者", placeholder="例如：匿名用户、作者姓名或未知")
                year = st.text_input("年份", placeholder="例如：2026、未知年份")
                c1, c2 = st.columns(2)
                with c1:
                    culture = st.text_input("文化 / 地区", placeholder="例如：中国、欧洲、用户上传")
                    classification = st.text_input("分类", placeholder="例如：绘画、电影海报、摄影")
                with c2:
                    medium = st.text_input("媒介", placeholder="例如：数字图像、油画、海报")
                    source_url = st.text_input("来源链接", placeholder="可选，用于追溯图片来源")
                tags = st.text_input("标签", placeholder="例如：冷色、梦幻、展览视觉")
                usage_note = st.text_area("用途说明", placeholder="例如：适合品牌视觉、海报设计或 UI 配色参考", height=82)
                submitted = st.form_submit_button("提交到开放区", use_container_width=True)

            if submitted:
                ok, message = save_submission(
                    uploaded,
                    {
                        "title": title,
                        "artist": artist,
                        "year": year,
                        "culture": culture,
                        "classification": classification,
                        "medium": medium,
                        "source_url": source_url,
                        "tags": tags,
                        "usage_note": usage_note,
                    },
                )
                st.session_state.submission_notice = ("success" if ok else "error", message)
                if ok:
                    st.session_state.show_upload_form = False
                st.rerun()

    submissions = load_submissions()
    st.markdown(
        f'<div class="ps-label" style="margin-top:1rem;">开放区作品 · {len(submissions)} 件</div>',
        unsafe_allow_html=True,
    )
    if submissions:
        try:
            submission_values = render_submission_controls(submissions)
            submission_results, submission_note = search_submissions(submissions, submission_values)
            if submission_note:
                st.info(submission_note)
        except ValueError as exc:
            st.error(str(exc))
            submission_results = submissions[:30]
        except Exception as exc:
            st.error(f"检索失败：{exc}")
            submission_results = []
    else:
        submission_results = []

    selected_submission = None
    if submission_results:
        selected_options = {
            f'{item.get("title", "未命名上传作品")} · {item.get("artist", "用户未填写")} · {item.get("year", "未知年份")}': idx
            for idx, item in enumerate(submission_results)
        }
        labels = list(selected_options.keys())
        current_selected = str(st.session_state.get("selected_submission_id") or "")
        default_index = 0
        for label, idx in selected_options.items():
            item = submission_results[idx]
            if str(item.get("submission_id") or item.get("id")) == current_selected:
                default_index = idx
                break
        selected_label = st.selectbox("选择开放区作品", labels, index=default_index, key="selected_upload_label")
        selected_submission = submission_results[selected_options[selected_label]]
        st.session_state.selected_submission_id = str(
            selected_submission.get("submission_id") or selected_submission.get("id")
        )
    else:
        st.info("还没有可展示的开放区作品。上传第一张作品后，它会出现在这里，并与正式馆藏分开展示。")

    render_submission_detail_panel(selected_submission)


def render_detail_panel(card: dict | None) -> None:
    st.markdown('<div id="ps-detail-anchor" class="ps-detail-anchor"></div>', unsafe_allow_html=True)
    st.markdown('<div class="ps-section-title">作品档案 <span>/ Artwork File</span></div>', unsafe_allow_html=True)
    if not card:
        st.info("请选择一张卡片查看详情。")
        return

    show_report_face = bool(
        st.session_state.get("show_report")
        and str(st.session_state.get("report_card_id")) == str(card.get("id"))
    )

    with st.container(border=True):
        st.markdown('<span class="ps-detail-shell-sentinel"></span>', unsafe_allow_html=True)
        head_left, head_right = st.columns([0.82, 0.18], gap="large")
        with head_left:
            if show_report_face:
                st.markdown(
                    f"""
                    <div class="ps-detail-title">{card.get("title", "未命名作品")}</div>
                    <div class="ps-muted-note">
                        <span class="ps-view-tab">分析报告</span>
                        &nbsp; {card.get("artist", "未知作者")} · {card.get("year", "未知年份")}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div class="ps-detail-title">{card.get("title", "未命名作品")}</div>
                    <div class="ps-muted-note">
                        <span class="ps-view-tab">作品详情</span>
                        &nbsp; {card.get("artist", "未知作者")} · {card.get("year", "未知年份")} ·
                        {card.get("culture", "未知文化")} · {card.get("classification", "未知分类")}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        with head_right:
            if show_report_face:
                st.markdown('<div class="ps-control-spacer"></div>', unsafe_allow_html=True)
                st.button(
                    "返回详情",
                    use_container_width=True,
                    key=f"back_{card.get('id')}",
                    on_click=close_report,
                )
            else:
                st.markdown('<div class="ps-control-spacer"></div>', unsafe_allow_html=True)
                st.button(
                    "查看分析报告",
                    use_container_width=True,
                    key=f"report_{card.get('id')}",
                    on_click=toggle_report,
                    args=(card.get("id"),),
                )

        if show_report_face:
            report_image = ensure_report_image(card)
            if report_image is None:
                st.warning("分析报告暂时无法生成。请重启 Streamlit 后再试，或检查数据文件与本地色卡目录。")
            else:
                st.markdown(
                    f"""
                    <div class="ps-soft-appear">
                        <div class="ps-face-chip" style="margin: 0.8rem 0 0.9rem 0;">
                            <span>报告模式</span>
                            <span>·</span>
                            <span>{card.get("source_url", "") and "基于该作品调色盘生成" or "按作品数据生成"}</span>
                        </div>
                        <div class="ps-report-shell">
                            <div class="ps-scroll-report">
                                <div class="ps-scroll-paper">
                                    <img
                                        src="{image_to_data_uri(report_image) or ''}"
                                        alt="分析报告"
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            return

        st.markdown('<div class="ps-soft-appear">', unsafe_allow_html=True)
        left, right = st.columns([1.05, 1.15], gap="large")

        with left:
            st.markdown(f'<div class="ps-label">原作图</div>', unsafe_allow_html=True)
            image_url = card.get("image_url", "")
            if image_url:
                try:
                    st.markdown('<div class="ps-image-frame">', unsafe_allow_html=True)
                    st.image(image_url, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                except Exception:
                    st.warning("原作图片暂时无法加载。")
            else:
                st.caption("暂无原作图。")

            palette_img = None
            try:
                backend = get_backend()
                palette_img = backend.get_palette_image_path(card.get("id"))
            except Exception:
                palette_img = None

            st.markdown('<div class="ps-label" style="margin-top:0.95rem;">色卡图</div>', unsafe_allow_html=True)
            if palette_img:
                st.markdown('<div class="ps-image-frame">', unsafe_allow_html=True)
                st.image(str(palette_img), use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.caption("本地色卡图片未找到。")

        with right:
            st.markdown(
                f"""
                <div class="ps-detail-file-title">
                    <strong>{card.get("title", "未命名作品")}</strong>
                    <span>{card.get("artist", "未知作者")} · {card.get("year", "未知年份")} · {card.get("culture", "未知文化")}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown('<div class="ps-label">基础信息</div>', unsafe_allow_html=True)
            info_cols = st.columns(2)
            info_map = [
                ("媒介", card.get("medium", "")),
                ("整体色调", card.get("overall_tone", "")),
                ("主色系", card.get("color_family", "")),
                ("分类", card.get("classification", "")),
            ]
            for idx, (label, value) in enumerate(info_map):
                with info_cols[idx % 2]:
                    st.markdown(f"**{label}**")
                    st.caption(str(value or "暂无"))
            source_url = card.get("source_url", "")
            if source_url:
                st.markdown(f'<div class="ps-card-footer-note" style="justify-content:flex-start;"><a href="{source_url}" target="_blank" rel="noreferrer">查看馆藏来源</a></div>', unsafe_allow_html=True)

            st.markdown('<div class="ps-detail-divider"></div>', unsafe_allow_html=True)
            st.markdown('<div class="ps-label" style="margin-top:0.9rem;">调色盘</div>', unsafe_allow_html=True)
            st.markdown(
                palette_bar_html(card.get("palette_hexes", []), card.get("palette_ratios", [])),
                unsafe_allow_html=True,
            )
            st.markdown('<div class="ps-copy-hint">点击下方色号可复制单个 HEX，也可以一键复制整套色值。</div>', unsafe_allow_html=True)

            swatch_cols = st.columns(min(max(len(card.get("palette_hexes", [])), 1), 5))
            palette_hexes = card.get("palette_hexes", [])
            palette_ratios = card.get("palette_ratios", [])
            color_names = card.get("color_names", [])
            for idx, hex_color in enumerate(palette_hexes[:5]):
                with swatch_cols[idx % len(swatch_cols)]:
                    ratio = palette_ratios[idx] if idx < len(palette_ratios) else 0
                    color_name = color_names[idx] if idx < len(color_names) else "主色"
                    st.markdown(
                        f"""
                        <div class="ps-swatch">
                            <div class="ps-swatch-color" style="background:{hex_color};"></div>
                            <div class="ps-swatch-name">{color_name}</div>
                            <div class="ps-swatch-hex">{hex_color}</div>
                            <div class="ps-swatch-hex">占比 {ratio:.2%}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            render_palette_copy_tools(palette_hexes)

            st.markdown('<div class="ps-detail-divider"></div>', unsafe_allow_html=True)
            st.markdown('<div class="ps-label" style="margin-top:0.9rem;">配色用途建议</div>', unsafe_allow_html=True)
            st.markdown(usage_badges(card.get("usage_suggestion", {})), unsafe_allow_html=True)

            st.markdown('<div class="ps-detail-divider"></div>', unsafe_allow_html=True)
            st.markdown('<div class="ps-label" style="margin-top:0.9rem;">标签</div>', unsafe_allow_html=True)
            tag_items = []
            for field in ["color_tags", "emotion_tags", "style_tags", "use_tags"]:
                for item in split_items(card.get(field, "")):
                    tag_items.append(item)
            if tag_items:
                st.markdown(
                    '<div class="ps-badge-list">'
                    + "".join(
                        f'<span class="{tag_badge_class(item)}">{item}</span>'
                        for item in tag_items[:16]
                    )
                    + "</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.caption("暂无标签。")

            st.markdown('<div class="ps-detail-divider"></div>', unsafe_allow_html=True)
            st.markdown('<div class="ps-label" style="margin-top:0.9rem;">检索信息</div>', unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="ps-search-note">
                    排名：#{card.get("_rank", "")} · 得分：{card.get("_score", 0.0):.3f}
                    <br />
                    推荐理由：{card.get("_reason", "") or "暂无"}
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown('</div>', unsafe_allow_html=True)


def main() -> None:
    st.session_state.setdefault("selected_card_id", None)
    st.session_state.setdefault("scroll_to_detail", False)
    st.session_state.setdefault("show_report", False)
    st.session_state.setdefault("report_card_id", None)
    st.session_state.setdefault("scroll_trigger_nonce", 0)
    st.session_state.setdefault("query_text", "")
    st.session_state.setdefault("hex_text", "#1E3A8A")
    st.session_state.setdefault("top_k", 30)
    st.session_state.setdefault("mode_select", "混合检索")
    st.session_state.setdefault("filter_overall_tone", "全部")
    st.session_state.setdefault("filter_color_family", "全部")
    st.session_state.setdefault("filter_culture", "全部")
    st.session_state.setdefault("filter_classification", "全部")
    st.session_state.setdefault("selected_submission_id", None)
    st.session_state.setdefault("scroll_to_submission_detail", False)
    st.session_state.setdefault("submission_scroll_nonce", 0)
    st.session_state.setdefault("show_submission_report", False)
    st.session_state.setdefault("submission_report_id", None)
    st.session_state.setdefault("submission_query_text", "")
    st.session_state.setdefault("submission_hex_text", "#1E3A8A")
    st.session_state.setdefault("submission_top_k", 30)
    st.session_state.setdefault("submission_mode_select", "混合检索")
    st.session_state.setdefault("submission_filter_overall_tone", "全部")
    st.session_state.setdefault("submission_filter_color_family", "全部")
    st.session_state.setdefault("submission_filter_culture", "全部")
    st.session_state.setdefault("submission_filter_classification", "全部")

    if BACKEND_IMPORT_ERROR is not None:
        st.error(
            "后端包暂时无法导入，请先安装依赖后再运行前端。"
            f" 详细错误：{BACKEND_IMPORT_ERROR}"
        )
        st.code("pip install -r 前端/requirements.txt", language="bash")
        st.stop()

    ps = get_backend()
    render_hero(ps)

    if not EXCEL_PATH.exists():
        st.error(f"找不到数据文件：{EXCEL_PATH}")
        st.stop()

    filter_options = build_filter_options(ps)
    values = render_controls(filter_options)

    try:
        results, note = search_artworks(ps, values)
    except ValueError as exc:
        st.error(str(exc))
        results = ps.get_all(top_k=int(values["top_k"]))
        note = "已回退为默认浏览模式。"
    except Exception as exc:
        st.error(f"检索失败：{exc}")
        results = []
        note = None

    if note:
        st.info(note)

    render_results(results)

    selected_card = ensure_selected_card(results)

    st.markdown("---")
    render_detail_panel(selected_card)
    render_submission_section()
    activate_detail_scroll()
    activate_submission_detail_scroll()


if __name__ == "__main__":
    main()



st.markdown("---")
st.caption("PaletteSeek © 2026")
