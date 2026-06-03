from __future__ import annotations

import base64
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
    --ps-bg: #f5efe4;
    --ps-panel: rgba(255, 255, 255, 0.72);
    --ps-panel-strong: rgba(255, 255, 255, 0.92);
    --ps-border: rgba(68, 84, 92, 0.16);
    --ps-text: #172126;
    --ps-muted: #62707a;
    --ps-accent: #245f63;
    --ps-accent-2: #c98f43;
    --ps-shadow: 0 18px 60px rgba(58, 74, 82, 0.12);
}

html, body, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at top left, rgba(36, 95, 99, 0.10), transparent 35%),
        radial-gradient(circle at top right, rgba(201, 143, 67, 0.12), transparent 30%),
        linear-gradient(180deg, #faf6ef 0%, #f5efe4 42%, #efe8dc 100%);
    color: var(--ps-text);
}

#MainMenu, footer, header { visibility: hidden; }

.block-container {
    padding-top: 1.1rem;
    padding-bottom: 2rem;
}

.ps-hero {
    border: 1px solid var(--ps-border);
    background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(255,255,255,0.68));
    box-shadow: var(--ps-shadow);
    border-radius: 28px;
    padding: 1.6rem 1.7rem;
    margin-bottom: 1rem;
}

.ps-kicker {
    display: inline-block;
    font-size: 0.78rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--ps-accent);
    font-weight: 700;
    margin-bottom: 0.4rem;
}

.ps-title {
    font-size: 2.25rem;
    line-height: 1.08;
    font-weight: 800;
    margin: 0.15rem 0 0.55rem 0;
    color: var(--ps-text);
}

.ps-subtitle {
    color: var(--ps-muted);
    font-size: 1.0rem;
    line-height: 1.6;
    max-width: 60rem;
    margin-bottom: 0.8rem;
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
    padding: 0.48rem 0.75rem;
    border-radius: 999px;
    border: 1px solid rgba(36, 95, 99, 0.14);
    background: rgba(255, 255, 255, 0.72);
    color: var(--ps-text);
    font-size: 0.84rem;
    font-weight: 600;
}

.ps-section-title {
    margin: 1.1rem 0 0.35rem 0;
    font-size: 1.08rem;
    font-weight: 800;
    color: var(--ps-text);
}

.ps-card {
    height: 100%;
    border-radius: 20px;
    border: 1px solid rgba(36, 95, 99, 0.14);
    background: rgba(255, 255, 255, 0.82);
    box-shadow: 0 10px 28px rgba(58, 74, 82, 0.08);
    padding: 0.95rem 0.95rem 0.85rem 0.95rem;
}

.ps-control-spacer {
    height: 2.05rem;
}

.ps-card-highlight {
    border-color: rgba(36, 95, 99, 0.42);
    box-shadow: 0 16px 34px rgba(36, 95, 99, 0.16);
}

.ps-card-title {
    margin-top: 0.35rem;
    font-size: 1rem;
    font-weight: 800;
    color: var(--ps-text);
    line-height: 1.45;
}

.ps-card-meta {
    font-size: 0.84rem;
    color: var(--ps-muted);
    line-height: 1.5;
}

.ps-result-image {
    width: 100%;
    height: 180px;
    margin-bottom: 0.7rem;
    border-radius: 18px;
    overflow: hidden;
    background: linear-gradient(135deg, rgba(36,95,99,0.12), rgba(201,143,67,0.10));
}

.ps-result-image img {
    width: 100%;
    height: 100%;
    display: block;
    object-fit: cover;
}

.ps-result-title {
    font-size: 1rem;
    font-weight: 800;
    line-height: 1.35;
    color: var(--ps-text);
    min-height: 2.7em;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.ps-result-meta {
    font-size: 0.84rem;
    color: var(--ps-muted);
    line-height: 1.45;
    margin-top: 0.28rem;
    min-height: 4.1em;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.ps-result-reason {
    font-size: 0.84rem;
    color: var(--ps-muted);
    line-height: 1.45;
    margin-top: 0.3rem;
    min-height: 2.75em;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.ps-result-palette {
    margin: 0.1rem 0 0.65rem 0;
}

.ps-card-chip-space {
    height: 1.6rem;
}

.ps-card-footer-note {
    min-height: 1.55rem;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.84rem;
    color: var(--ps-muted);
}

.ps-palette {
    display: flex;
    overflow: hidden;
    height: 14px;
    border-radius: 999px;
    background: rgba(17, 24, 39, 0.06);
    border: 1px solid rgba(17, 24, 39, 0.06);
}

.ps-palette span {
    display: block;
    height: 100%;
}

.ps-detail-panel {
    border-radius: 24px;
    border: 1px solid var(--ps-border);
    background: var(--ps-panel-strong);
    box-shadow: var(--ps-shadow);
    padding: 1.1rem 1.1rem 0.95rem 1.1rem;
}

.ps-report-shell {
    max-width: 860px;
    margin: 0 auto;
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

.ps-detail-title {
    font-size: 1.45rem;
    font-weight: 900;
    margin: 0 0 0.35rem 0;
}

.ps-label {
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: var(--ps-accent);
    text-transform: uppercase;
    margin-bottom: 0.35rem;
}

.ps-swatch-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 0.75rem;
}

.ps-swatch {
    border-radius: 16px;
    padding: 0.7rem;
    border: 1px solid rgba(17, 24, 39, 0.08);
    background: rgba(255, 255, 255, 0.86);
}

.ps-swatch-color {
    border-radius: 12px;
    height: 72px;
    margin-bottom: 0.65rem;
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

.ps-badge-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
}

.ps-badge {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 0.36rem 0.65rem;
    background: rgba(36, 95, 99, 0.08);
    color: var(--ps-text);
    font-size: 0.82rem;
    font-weight: 600;
}

.ps-muted-note {
    color: var(--ps-muted);
    font-size: 0.88rem;
    line-height: 1.55;
}

.stButton > button {
    border-radius: 999px;
    font-weight: 700;
    border: 1px solid rgba(36, 95, 99, 0.22);
}

.stButton > button:hover {
    border-color: rgba(36, 95, 99, 0.38);
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


def render_hero(ps: PaletteSeek) -> None:
    stats = ps.stats()
    with st.container():
        st.markdown(
            """
            <div class="ps-hero">
                <div class="ps-kicker">PaletteSeek / 艺术作品配色检索</div>
                <div class="ps-title">把艺术作品的色彩，检索成可直接使用的灵感卡片</div>
                <div class="ps-subtitle">
                    通过关键词、颜色和混合检索，快速找到适合汇报、海报、视觉设计和主题配色的作品。
                    结果会展示原作信息、调色盘、标签、推荐理由和配色用途建议。
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("作品总数", stats.get("total", 0))
    c2.metric("色系选项", len(stats.get("color_families", [])))
    c3.metric("整体色调", len(stats.get("overall_tones", [])))
    c4.metric("数据源", "Excel")


def build_filter_options(ps: PaletteSeek) -> dict[str, list[str]]:
    raw = ps.list_filter_options()
    return {
        "overall_tone": ["全部"] + raw.get("overall_tone", []),
        "color_family": ["全部"] + raw.get("color_family", []),
        "culture": ["全部"] + raw.get("culture", []),
        "classification": ["全部"] + raw.get("classification", []),
    }


def render_controls(filter_options: dict[str, list[str]]) -> dict[str, str]:
    st.markdown('<div class="ps-section-title">检索与筛选</div>', unsafe_allow_html=True)

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
                value=st.session_state.get("query_text", "科技感 数据大屏"),
                placeholder="例如：深蓝 PPT 稳重",
                help="支持 OR / NOT 布尔语法，例如：深蓝 or 蓝紫 not 暖色",
                key="query_text",
            )
        with b_col:
            st.markdown('<div class="ps-control-spacer"></div>', unsafe_allow_html=True)
            st.button("搜索", use_container_width=True, key="search_btn")
        st.caption("关键词检索、混合检索都支持布尔语法；空关键词会默认展示全部作品。")

    with right:
        hex_text = st.color_picker(
            "HEX 色值 / 取色盘",
            value=st.session_state.get("hex_text", "#1E3A8A"),
            key="hex_text",
        )
        st.caption("点击色块可弹出取色盘；颜色检索会优先读取这里的值。")
        top_k = st.number_input(
            "结果数量",
            min_value=1,
            value=int(st.session_state.get("top_k", 12)),
            step=1,
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
        st.button("清空筛选", use_container_width=True, on_click=reset_filters)

    st.markdown(
        """
        <div class="ps-chip-row">
            <span class="ps-chip">关键词检索：支持 OR / NOT</span>
            <span class="ps-chip">颜色检索：Delta-E 感知匹配</span>
            <span class="ps-chip">混合检索：颜色 + 标签 + 文本</span>
            <span class="ps-chip">筛选字段：色调 / 色系 / 文化 / 分类</span>
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
    st.session_state.query_text = "科技感 数据大屏"
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


def render_result_card(card: dict, selected: bool = False) -> None:
    palette_html = palette_bar_html(card.get("palette_hexes", []), card.get("palette_ratios", []))
    rank = card.get("_rank", "")
    score = card.get("_score", 0.0)
    reason = card.get("_reason", "")
    image_src = resolve_ring_image_src(card)

    with st.container(border=True):
        if selected:
            st.markdown('<span class="ps-chip">当前选中</span>', unsafe_allow_html=True)
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

        st.markdown(f'<div class="ps-result-palette">{palette_html}</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="ps-result-title">{card.get("title", "未命名作品")}</div>
            <div class="ps-result-meta">
                {card.get("artist", "未知作者")} · {card.get("year", "未知年份")} · 排名 #{rank} · 得分 {score:.3f}
            </div>
            <div class="ps-result-meta">
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
    st.markdown('<div class="ps-section-title">检索结果</div>', unsafe_allow_html=True)
    if not results:
        st.info("没有找到匹配结果。可以尝试扩大关键词范围、调高结果数量或更换颜色。")
        return

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
            render_result_card(card, selected=str(card.get("id")) == selected_id)


def render_detail_panel(card: dict | None) -> None:
    st.markdown('<div id="ps-detail-anchor" class="ps-detail-anchor"></div>', unsafe_allow_html=True)
    st.markdown('<div class="ps-section-title">作品详情</div>', unsafe_allow_html=True)
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
                        分析报告面 · {card.get("artist", "未知作者")} · {card.get("year", "未知年份")}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div class="ps-detail-title">{card.get("title", "未命名作品")}</div>
                    <div class="ps-muted-note">
                        {card.get("artist", "未知作者")} · {card.get("year", "未知年份")} ·
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
                            style="width: 100%; max-width: 100%; height: auto; display: block; border-radius: 20px; border: 1px solid rgba(17,24,39,0.08); background: #fff;"
                        />
                    </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if report_image is None:
                st.warning("暂时无法生成分析报告，请检查后端依赖或数据文件。")
            return

        st.markdown('<div class="ps-soft-appear">', unsafe_allow_html=True)
        left, right = st.columns([1.05, 1.15], gap="large")

        with left:
            st.markdown(f'<div class="ps-label">原作图</div>', unsafe_allow_html=True)
            image_url = card.get("image_url", "")
            if image_url:
                try:
                    st.image(image_url, use_container_width=True)
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
                st.image(str(palette_img), use_container_width=True)
            else:
                st.caption("本地色卡图片未找到。")

        with right:
            st.markdown('<div class="ps-label">基础信息</div>', unsafe_allow_html=True)
            info_cols = st.columns(2)
            info_map = [
                ("媒介", card.get("medium", "")),
                ("整体色调", card.get("overall_tone", "")),
                ("主色系", card.get("color_family", "")),
                ("来源", card.get("source_url", "")),
            ]
            for i, (label, value) in enumerate(info_map):
                with info_cols[i % 2]:
                    if label == "来源" and value:
                        st.markdown(f"**{label}**  \n[{value}]({value})")
                    else:
                        st.markdown(f"**{label}**  \n{value or '暂无'}")

            st.markdown('<div class="ps-label" style="margin-top:0.9rem;">调色盘</div>', unsafe_allow_html=True)
            st.markdown(
                palette_bar_html(card.get("palette_hexes", []), card.get("palette_ratios", [])),
                unsafe_allow_html=True,
            )

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

            st.markdown('<div class="ps-label" style="margin-top:0.9rem;">标签</div>', unsafe_allow_html=True)
            tag_items = []
            for field in ["color_tags", "emotion_tags", "style_tags", "use_tags"]:
                for item in split_items(card.get(field, "")):
                    tag_items.append(item)
            if tag_items:
                st.markdown(
                    '<div class="ps-badge-list">' + "".join(f'<span class="ps-badge">{item}</span>' for item in tag_items[:16]) + "</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.caption("暂无标签。")

            st.markdown('<div class="ps-label" style="margin-top:0.9rem;">配色用途建议</div>', unsafe_allow_html=True)
            st.markdown(usage_badges(card.get("usage_suggestion", {})), unsafe_allow_html=True)

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
    st.session_state.setdefault("query_text", "科技感 数据大屏")
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
