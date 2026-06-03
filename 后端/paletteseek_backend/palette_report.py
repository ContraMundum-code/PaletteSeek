"""
palette_report.py
-----------------
生成 PaletteSeek 的综合色彩可视化报告图。

既可以单独命令行运行，也可以在后端 / 前端搜索结果里直接调用。

示例：
    python palette_report.py --excel 数据.xlsx --artwork-id 869 --output report_869.png
"""

from __future__ import annotations

import argparse
import io
import os
import ssl
import tempfile
import urllib.request
from pathlib import Path

_CACHE_ROOT = Path(tempfile.gettempdir()) / "paletteseek-cache"
_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_CACHE_ROOT / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(_CACHE_ROOT))

import matplotlib

matplotlib.use("Agg")

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib import patches
from PIL import Image

try:
    from .color_utils import delta_e, hex_to_rgb, rgb_to_hex, rgb_to_hsv, rgb_to_lab
    from .data_loader import ArtworkDataset
except ImportError:
    from color_utils import delta_e, hex_to_rgb, rgb_to_hex, rgb_to_hsv, rgb_to_lab
    from data_loader import ArtworkDataset


USER_AGENT = "PaletteSeek-Palette-Report/1.0"


def configure_matplotlib_fonts() -> None:
    """尽量使用本机可用的中文字体，避免中文标题乱码。"""
    plt.rcParams["font.sans-serif"] = [
        "PingFang SC",
        "Hiragino Sans GB",
        "Microsoft YaHei",
        "SimHei",
        "Arial Unicode MS",
        "Noto Sans CJK SC",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False


def build_ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def fetch_image_from_url(url: str) -> Image.Image:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20, context=build_ssl_context()) as resp:
        return Image.open(io.BytesIO(resp.read())).convert("RGB")


def load_original_image(record: dict) -> Image.Image:
    image_url = str(record.get("image_url", "")).strip()
    if image_url:
        try:
            return fetch_image_from_url(image_url)
        except Exception:
            pass

    palette_path = str(record.get("palette_image_path", "")).strip()
    if palette_path and Path(palette_path).exists():
        return Image.open(palette_path).convert("RGB")

    palette_image_filename = str(record.get("palette_image_filename", "")).strip()
    palette_cards_dir = record.get("_palette_cards_dir")
    if palette_image_filename and palette_cards_dir:
        fallback_path = Path(palette_cards_dir) / palette_image_filename
        if fallback_path.exists():
            return Image.open(fallback_path).convert("RGB")

    raise ValueError("既无法读取原图，也无法回退到本地色卡图")


def ensure_palette_data(record: dict) -> tuple[list[str], list[float], list[str]]:
    hexes = list(record.get("palette_hexes", []) or [])
    ratios = list(record.get("palette_ratios", []) or [])

    if not hexes:
        for idx in range(1, 10):
            hx = str(record.get(f"color_{idx}_hex", "")).strip()
            if hx:
                hexes.append(hx)
                raw_ratio = str(record.get(f"color_{idx}_ratio", "")).strip().rstrip("%")
                try:
                    val = float(raw_ratio)
                    ratios.append(val / 100.0 if val > 1 else val)
                except ValueError:
                    ratios.append(0.0)

    raw_names = record.get("color_names")
    if isinstance(raw_names, list):
        names = raw_names
    else:
        text = str(record.get("color_chinese_names", "") or record.get("color_tags_cn", ""))
        names = [x.strip() for x in text.replace("，", "、").split("、") if x.strip()]

    if not hexes:
        raise ValueError("记录中没有可用的主色数据")

    if not ratios or len(ratios) != len(hexes):
        ratios = [1.0 / len(hexes)] * len(hexes)

    total = sum(ratios) or 1.0
    ratios = [r / total for r in ratios]
    names = names[: len(hexes)]
    if len(names) < len(hexes):
        names += [""] * (len(hexes) - len(names))

    return hexes, ratios, names


def build_network_graph(ax, hexes: list[str], ratios: list[float]) -> None:
    n = len(hexes)
    G = nx.Graph()
    labels = {}
    for idx, (hx, ratio) in enumerate(zip(hexes, ratios), start=1):
        node = f"{idx:02d}"
        G.add_node(node, color=hx, ratio=ratio)
        labels[node] = node

    nodes = list(G.nodes())
    for i in range(n):
        for j in range(i + 1, n):
            sim = max(0.0, 1.0 - delta_e(hexes[i], hexes[j]) / 100.0)
            G.add_edge(nodes[i], nodes[j], weight=sim)

    pos = nx.circular_layout(G, scale=1.0)
    edge_widths = [0.5 + 3.2 * G[u][v]["weight"] for u, v in G.edges()]
    edge_alphas = [0.18 + 0.45 * G[u][v]["weight"] for u, v in G.edges()]
    node_sizes = [950 + 5200 * ratio for ratio in ratios]

    for (u, v), width, alpha in zip(G.edges(), edge_widths, edge_alphas):
        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=[(u, v)],
            width=width,
            alpha=alpha,
            edge_color="#9AA0A6",
            ax=ax,
        )

    nx.draw_networkx_nodes(
        G,
        pos,
        node_color=hexes,
        node_size=node_sizes,
        edgecolors="white",
        linewidths=2.0,
        ax=ax,
    )
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=10, font_weight="bold", ax=ax)

    ax.set_title("色彩网络图", fontsize=22, fontweight="bold", pad=14)
    ax.set_axis_off()


def build_bar_chart(ax, hexes: list[str], ratios: list[float]) -> None:
    labels = [f"{idx:02d}" for idx in range(1, len(hexes) + 1)]
    percents = [r * 100 for r in ratios]
    y_pos = list(range(len(hexes)))
    ax.barh(y_pos, percents, color=hexes, edgecolor="none", height=0.72)
    ax.set_yticks(y_pos, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, max(percents) * 1.15)
    ax.set_title("色彩占比（柱状图）", fontsize=18, fontweight="bold", pad=10)
    ax.grid(axis="x", linestyle="--", alpha=0.18)
    for y, value in zip(y_pos, percents):
        ax.text(value + 0.5, y, f"{value:.1f}%", va="center", fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)


def build_pie_chart(ax, hexes: list[str], ratios: list[float]) -> None:
    labels = [f"{idx:02d}" for idx in range(1, len(hexes) + 1)]
    ax.pie(
        ratios,
        labels=labels,
        colors=hexes,
        startangle=90,
        counterclock=False,
        autopct=lambda p: f"{p:.1f}%",
        textprops={"fontsize": 10},
        wedgeprops={"linewidth": 0.8, "edgecolor": "white"},
    )
    ax.set_title("色彩占比（饼图）", fontsize=18, fontweight="bold", pad=10)


def build_swatch_panel(ax, hexes: list[str], ratios: list[float], names: list[str]) -> None:
    ax.set_title("色卡详细信息", fontsize=18, fontweight="bold", pad=10)
    ax.set_xlim(0, 3)
    ax.set_ylim(0, 3)
    ax.axis("off")

    for idx, (hx, ratio, name) in enumerate(zip(hexes, ratios, names)):
        row = 2 - idx // 3
        col = idx % 3
        x0 = col + 0.08
        y0 = row + 0.42

        rect = patches.Rectangle((x0, y0), 0.62, 0.42, facecolor=hx, edgecolor="#DDDDDD", linewidth=0.8)
        ax.add_patch(rect)

        r, g, b = hex_to_rgb(hx)
        h, s, v = rgb_to_hsv(r, g, b)
        ax.text(x0, y0 + 0.34, f"{idx+1:02d}", fontsize=10, fontweight="bold")
        ax.text(x0, y0 - 0.03, name or "未命名", fontsize=8)
        ax.text(x0, y0 - 0.12, f"RGB ({r}, {g}, {b})", fontsize=7)
        ax.text(x0, y0 - 0.21, f"HSV ({h:.0f}, {s*100:.0f}, {v*100:.0f})", fontsize=7)
        ax.text(x0, y0 - 0.30, f"HEX {hx}", fontsize=7)
        ax.text(x0, y0 - 0.39, f"占比 {ratio*100:.1f}%", fontsize=7)


def build_table(ax, hexes: list[str], ratios: list[float], names: list[str]) -> None:
    ax.axis("off")
    ax.set_title("色彩聚类结果", fontsize=22, fontweight="bold", pad=12)

    columns = ["序号", "颜色", "RGB", "HSV", "Lab", "HEX", "占比(%)"]
    rows = []
    for idx, (hx, ratio, name) in enumerate(zip(hexes, ratios, names), start=1):
        r, g, b = hex_to_rgb(hx)
        h, s, v = rgb_to_hsv(r, g, b)
        l_val, a_val, b_val = rgb_to_lab(r, g, b)
        rows.append(
            [
                str(idx),
                name or "",
                f"({r}, {g}, {b})",
                f"({h:.0f}, {s*100:.0f}, {v*100:.0f})",
                f"({l_val:.0f}, {a_val:.0f}, {b_val:.0f})",
                hx,
                f"{ratio*100:.1f}",
            ]
        )

    table = ax.table(cellText=rows, colLabels=columns, loc="center", cellLoc="center", colLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.8)

    for j in range(len(columns)):
        header = table[(0, j)]
        header.set_facecolor("#F2F2F2")
        header.set_text_props(weight="bold")

    for i, hx in enumerate(hexes, start=1):
        swatch_cell = table[(i, 1)]
        swatch_cell.set_facecolor(hx)
        swatch_cell.get_text().set_text("")
        swatch_cell.set_edgecolor("#FFFFFF")


def render_palette_report(record: dict, output_path: str | Path, max_colors: int = 9) -> Path:
    configure_matplotlib_fonts()

    image = load_original_image(record)
    hexes, ratios, names = ensure_palette_data(record)

    hexes = hexes[:max_colors]
    ratios = ratios[:max_colors]
    names = names[:max_colors]
    total = sum(ratios) or 1.0
    ratios = [r / total for r in ratios]

    fig = plt.figure(figsize=(16, 20), dpi=170, facecolor="white")
    gs = gridspec.GridSpec(
        3,
        3,
        figure=fig,
        height_ratios=[1.02, 0.92, 1.10],
        width_ratios=[1.25, 1.0, 0.92],
        hspace=0.30,
        wspace=0.20,
    )

    title = str(record.get("title", ""))
    artist = str(record.get("artist", ""))
    year = str(record.get("year", ""))
    subtitle = " | ".join(x for x in [artist, year] if x)
    fig.suptitle(title if title else "PaletteSeek 色彩分析报告", fontsize=26, fontweight="bold", y=0.985)
    if subtitle:
        fig.text(0.5, 0.962, subtitle, ha="center", va="top", fontsize=13, color="#666666")

    ax_img = fig.add_subplot(gs[0, 0])
    ax_img.imshow(image)
    ax_img.set_title("原图", fontsize=22, fontweight="bold", pad=14)
    ax_img.axis("off")

    ax_net = fig.add_subplot(gs[0, 1:])
    build_network_graph(ax_net, hexes, ratios)

    ax_bar = fig.add_subplot(gs[1, 0])
    build_bar_chart(ax_bar, hexes, ratios)

    ax_pie = fig.add_subplot(gs[1, 1])
    build_pie_chart(ax_pie, hexes, ratios)

    ax_swatches = fig.add_subplot(gs[1, 2])
    build_swatch_panel(ax_swatches, hexes, ratios, names)

    ax_table = fig.add_subplot(gs[2, :])
    build_table(ax_table, hexes, ratios, names)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path


def render_palette_report_from_artwork(
    excel_path: str | Path,
    artwork_id: int | str,
    output_path: str | Path,
    sheet_name: str | None = None,
) -> Path:
    if sheet_name:
        dataset = ArtworkDataset(excel_path, sheet_name=sheet_name)
    else:
        dataset = ArtworkDataset(excel_path)
    record = dataset.get_by_id(artwork_id)
    if record is None:
        raise ValueError(f"找不到作品 ID: {artwork_id}")
    record["_palette_cards_dir"] = Path(excel_path).parent / "color_cards"
    return render_palette_report(record, output_path)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a PaletteSeek palette report image")
    parser.add_argument("--excel", default="数据.xlsx", help="数据工作簿路径")
    parser.add_argument("--sheet", default=None, help="工作表名称；默认使用后端数据加载器的主表")
    parser.add_argument("--artwork-id", required=True, help="作品 ID")
    parser.add_argument("--output", required=True, help="输出图片路径，如 reports/869_report.png")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    out = render_palette_report_from_artwork(
        excel_path=args.excel,
        artwork_id=args.artwork_id,
        output_path=args.output,
        sheet_name=args.sheet,
    )
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
