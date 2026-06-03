from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from typing import Any

import streamlit.components.v1 as components
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "后端"
BACKEND_PACKAGE_DIR = BACKEND_DIR / "paletteseek_backend"
EXCEL_PATH = BACKEND_PACKAGE_DIR / "数据.xlsx"
COLOR_CARDS_DIR = BACKEND_PACKAGE_DIR / "color_cards"
REPORTS_DIR = BACKEND_PACKAGE_DIR / "reports"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

BACKEND_IMPORT_ERROR: Exception | None = None
try:  # noqa: E402
    from paletteseek_backend import PaletteSeek
    from paletteseek_backend.color_utils import is_valid_hex
except Exception as exc:  # pragma: no cover - runtime guard for missing deps
    PaletteSeek = Any  # type: ignore[assignment]

    def is_valid_hex(_: str) -> bool:
        return False

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
    overflow: hidden;
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

.ps-help-dot {
    position: absolute;
    top: 1.25rem;
    right: 1.35rem;
    z-index: 2;
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

.ps-help-dot:hover {
    transform: translateY(-2px) rotate(4deg);
    background: rgba(255, 253, 248, 0.20);
    box-shadow: 0 12px 28px rgba(226, 179, 110, 0.18);
}

.ps-hero::before {
    content: "";
    position: absolute;
    inset: -34% -12% auto auto;
    width: 58%;
    height: 160%;
    pointer-events: none;
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
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.75rem;
    margin: 0.85rem 0 1.15rem 0;
}

.ps-stat {
    border: 1px solid rgba(255, 253, 248, 0.18);
    background: rgba(255, 253, 248, 0.10);
    border-radius: 10px;
    padding: 0.78rem 0.85rem;
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
    gap: 0.58rem;
}

.ps-stat-icon {
    width: 2.05rem;
    height: 2.05rem;
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
    font-size: 1.48rem;
    line-height: 1;
    font-weight: 900;
}

.ps-stat-label {
    font-family: "Kaiti SC", "STKaiti", "Xingkai SC", "HanziPen SC", "Songti SC", serif;
    margin-top: 0.35rem;
    color: rgba(255, 253, 248, 0.66);
    font-size: 0.86rem;
    font-weight: 700;
    letter-spacing: 0.04em;
}

.ps-stat-value-text {
    font-family: "Snell Roundhand", "Apple Chancery", "Brush Script MT", "Segoe Script", cursive;
    font-size: 1.58rem;
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
    margin: 1.2rem 0 0.45rem 0;
    font-size: 1.08rem;
    font-weight: 900;
    color: var(--ps-ink);
    letter-spacing: 0;
}

.ps-section-title span {
    color: var(--ps-accent);
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
    width: 100%;
    aspect-ratio: 4 / 3;
    height: auto;
    margin-bottom: 0.72rem;
    border-radius: 8px;
    overflow: hidden;
    background: linear-gradient(135deg, rgba(36,95,90,0.12), rgba(181,82,61,0.08));
    border: 1px solid rgba(21,25,24,0.10);
}

.ps-result-image img {
    width: 100%;
    height: 100%;
    display: block;
    object-fit: cover;
    transition: transform 520ms cubic-bezier(0.22, 0.61, 0.36, 1), filter 520ms ease;
}

.ps-result-image:hover img {
    transform: scale(1.045);
    filter: saturate(1.06) contrast(1.03);
}

.ps-result-title {
    font-size: 1.02rem;
    font-weight: 900;
    line-height: 1.35;
    color: var(--ps-ink);
    min-height: 2.7em;
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
    display: flex;
    justify-content: space-between;
    gap: 0.5rem;
    align-items: center;
    margin-bottom: 0.55rem;
    color: var(--ps-muted);
    font-size: 0.76rem;
    font-weight: 700;
}

.ps-rank-mark {
    width: 1.9rem;
    height: 1.9rem;
    display: inline-grid;
    place-items: center;
    border-radius: 999px;
    background: rgba(21, 25, 24, 0.18);
    color: rgba(255, 253, 248, 0.96);
    font-size: 0.72rem;
    font-weight: 900;
}

.ps-score-mark {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    color: var(--ps-muted);
}

.ps-score-stars {
    color: var(--ps-accent);
    letter-spacing: 0.02em;
    font-size: 0.78rem;
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

.ps-result-palette {
    margin: 0.1rem 0 0.78rem 0;
}

.ps-card-chip-space {
    height: 1.35rem;
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

.ps-detail-divider {
    height: 1px;
    margin: 0.98rem 0;
    background: linear-gradient(90deg, rgba(36, 95, 90, 0.22), rgba(21, 25, 24, 0.07), transparent);
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
    animation: psCardFloatReveal 0.72s cubic-bezier(0.22, 0.61, 0.36, 1) both;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-result-card-sentinel):hover {
    transform: translateY(-7px) scale(1.012);
    box-shadow: 0 24px 52px rgba(31, 34, 31, 0.16);
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
    chips = []
    for key, value in usage.items():
        chips.append(f'<span class="ps-badge">{key} · {value}</span>')
    return '<div class="ps-badge-list">' + "".join(chips) + "</div>"


def score_stars(score: float, min_score: float, max_score: float) -> str:
    if max_score <= min_score:
        filled = 5 if score > 0 else 0
    else:
        normalized = (float(score or 0.0) - min_score) / (max_score - min_score)
        filled = max(1, min(5, round(normalized * 4) + 1))
    return "★" * filled + "☆" * (5 - filled)


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
                <span class="ps-help-dot" title="检索规则：关键词支持 OR / NOT；颜色检索可直接选择或粘贴 HEX；空关键词会展示全部作品。">?</span>
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
            value=int(st.session_state.get("top_k", 12)),
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


def activate_detail_scroll() -> None:
    if st.session_state.get("scroll_to_detail"):
        st.session_state.scroll_trigger_nonce = int(st.session_state.get("scroll_trigger_nonce", 0)) + 1
        scroll_to_detail()
        st.session_state.scroll_to_detail = False


def reset_filters() -> None:
    st.session_state.selected_card_id = None
    st.session_state.query_text = ""
    st.session_state.hex_text = "#1E3A8A"
    st.session_state.top_k = 12
    st.session_state.mode_select = "混合检索"
    st.session_state.filter_overall_tone = "全部"
    st.session_state.filter_color_family = "全部"
    st.session_state.filter_culture = "全部"
    st.session_state.filter_classification = "全部"
    st.session_state.show_report = False
    st.session_state.report_card_id = None


def get_report_path(card_id: str) -> Path:
    return REPORTS_DIR / f"{card_id}_palette_report.png"


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


def image_to_data_uri(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    try:
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"
    except Exception:
        return None


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


def scroll_to_detail() -> None:
    nonce = int(st.session_state.get("scroll_trigger_nonce", 0))
    components.html(
        f"""
        <script>
          (function () {{
            const triggerNonce = {nonce};
            const delays = [80, 220, 420, 760];
            const anchorId = "ps-detail-anchor";
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
                  if (window.parent.__psScrollNonce === triggerNonce) {{
                    return;
                  }}
                  window.parent.__psScrollNonce = triggerNonce;
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


def render_result_card(card: dict, selected: bool = False, min_score: float = 0.0, max_score: float = 1.0) -> None:
    palette_html = palette_bar_html(card.get("palette_hexes", []), card.get("palette_ratios", []))
    rank = card.get("_rank", "")
    score = card.get("_score", 0.0)
    stars = score_stars(float(score or 0.0), min_score=min_score, max_score=max_score)
    reason = card.get("_reason", "")
    image_src = resolve_ring_image_src(card)

    with st.container(border=True):
        st.markdown('<span class="ps-result-card-sentinel"></span>', unsafe_allow_html=True)
        if selected:
            st.markdown('<span class="ps-chip">正在查看</span>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="ps-card-chip-space"></div>', unsafe_allow_html=True)

        if image_src:
            st.markdown(
                f'<div class="ps-result-image"><img src="{image_src}" alt="{card.get("title", "未命名作品")}" /></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="ps-result-image" style="display:grid;place-items:center;color:var(--ps-muted);font-weight:700;">暂无原作图</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            f"""
            <div class="ps-result-caption">
                <span class="ps-rank-mark">{rank}</span>
                <span class="ps-score-mark" title="星级按本次结果的相对得分计算"><span class="ps-score-stars">{stars}</span><span>{score:.3f}</span></span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(f'<div class="ps-result-palette">{palette_html}</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="ps-result-title">{card.get("title", "未命名作品")}</div>
            <div class="ps-result-meta">
                {card.get("artist", "未知作者")} · {card.get("year", "未知年份")}
                <br />
                {card.get("overall_tone", "未标注色调")} · {card.get("color_family", "未标注色系")}
            </div>
            <div class="ps-result-reason">
                {reason or "暂无推荐理由。"}
            </div>
            """,
            unsafe_allow_html=True,
        )
        left, right = st.columns(2)
        with left:
            st.button(
                "查看详情",
                key=f"detail_{card.get('id')}",
                use_container_width=True,
                on_click=select_card,
                args=(card.get("id"),),
            )
        with right:
            source_url = card.get("source_url", "")
            if source_url:
                st.markdown(
                    f'<div class="ps-card-footer-note"><a href="{source_url}" target="_blank" rel="noreferrer">来源链接</a></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown('<div class="ps-card-footer-note">暂无来源链接</div>', unsafe_allow_html=True)


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

    scores = [float(card.get("_score") or 0.0) for card in results]
    min_score = min(scores) if scores else 0.0
    max_score = max(scores) if scores else 1.0

    count = len(results)
    if count >= 25:
        columns = st.columns(5, gap="large")
    elif count >= 13:
        columns = st.columns(4, gap="large")
    elif count >= 7:
        columns = st.columns(3, gap="large")
    else:
        columns = st.columns(2, gap="large")

    selected_id = str(st.session_state.get("selected_card_id") or "")
    for idx, card in enumerate(results):
        with columns[idx % len(columns)]:
            render_result_card(
                card,
                selected=str(card.get("id")) == selected_id,
                min_score=min_score,
                max_score=max_score,
            )


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
                        <div class="ps-detail-panel">
                            <img
                                src="{image_to_data_uri(report_image) or ''}"
                                alt="分析报告"
                                style="width: 100%; max-width: 100%; height: auto; display: block; border-radius: 8px; border: 1px solid rgba(17,24,39,0.08); background: #fff;"
                            />
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
            st.markdown('<div class="ps-label" style="margin-top:0.9rem;">配色用途建议</div>', unsafe_allow_html=True)
            st.markdown(usage_badges(card.get("usage_suggestion", {})), unsafe_allow_html=True)

            st.markdown('<div class="ps-detail-divider"></div>', unsafe_allow_html=True)
            st.markdown('<div class="ps-label" style="margin-top:0.9rem;">检索信息</div>', unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="ps-muted-note">
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
    st.session_state.setdefault("top_k", 12)
    st.session_state.setdefault("mode_select", "混合检索")
    st.session_state.setdefault("filter_overall_tone", "全部")
    st.session_state.setdefault("filter_color_family", "全部")
    st.session_state.setdefault("filter_culture", "全部")
    st.session_state.setdefault("filter_classification", "全部")

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
    activate_detail_scroll()


if __name__ == "__main__":
    main()
