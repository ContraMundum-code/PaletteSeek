"""
test_backend.py
---------------
PaletteSeek 后端功能验证脚本。

运行方式：
    cd paletteseek_backend
    python test_backend.py

验证内容：
    1. 颜色工具函数
    2. 数据加载
    3. 关键词检索
    4. 颜色检索
    5. 混合检索
    6. 配色用途建议生成
    7. 筛选器功能
    8. 错误处理
"""

import sys
import os
from pathlib import Path

# 确保从当前目录导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── 项目方案里给的 10 个测试查询 ──────────────────────────────────────
TEST_QUERIES = [
    ("Q1",  "深蓝色 科技感 数据大屏",  "#1E3A8A"),
    ("Q2",  "温柔 低饱和 女性主题 PPT", "#E8D5CC"),
    ("Q3",  "复古海报配色",             "#8B4513"),
    ("Q4",  "环保主题 数据可视化",      "#2D6A4F"),
    ("Q5",  "高级感 黑金配色",          "#1A1A1A"),
    ("Q6",  "清新春天感",               "#A8D8A8"),
    ("Q7",  "神秘 夜晚 冷色调",         "#0D1B2A"),
    ("Q8",  "热烈 节日 红色系",         "#CC2936"),
    ("Q9",  "儿童主题 明亮配色",        "#FFD700"),
    ("Q10", "学术汇报 稳重配色",        "#4A6FA5"),
]

PASS = "✅"
FAIL = "❌"


def section(title: str) -> None:
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


def check(label: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    print(f"  {status}  {label}", end="")
    if detail:
        print(f"  →  {detail}", end="")
    print()
    if not condition:
        sys.exit(1)


# ──────────────────────────────────────────────────────────────────────
# 1. 颜色工具
# ──────────────────────────────────────────────────────────────────────

section("1. 颜色工具（color_utils）")

from color_utils import (
    hex_to_rgb, rgb_to_hex, rgb_to_lab, delta_e,
    palette_color_similarity, is_valid_hex,
)

rgb = hex_to_rgb("#FF0000")
check("hex_to_rgb #FF0000", rgb == (255, 0, 0), str(rgb))

hex_out = rgb_to_hex(255, 0, 0)
check("rgb_to_hex 255,0,0", hex_out == "#FF0000", hex_out)

# 同一颜色 Delta-E 应为 0
de = delta_e("#1E3A8A", "#1E3A8A")
check("Delta-E 同色=0", abs(de) < 0.001, f"{de:.4f}")

# 黑白之间应有大 Delta-E
de_bw = delta_e("#000000", "#FFFFFF")
check("Delta-E 黑白>50", de_bw > 50, f"{de_bw:.2f}")

# 有效 HEX 验证
check("is_valid_hex #1E3A8A", is_valid_hex("#1E3A8A"))
check("is_valid_hex ZZZZZZ 无效", not is_valid_hex("ZZZZZZ"))

# 调色盘相似度
sim = palette_color_similarity(
    "#1E3A8A",
    ["#1F3B8B", "#FFFFFF", "#000000"],
    [50.0, 30.0, 20.0],
)
check("palette_color_similarity 近似蓝色应>0.5", sim > 0.5, f"{sim:.4f}")


# ──────────────────────────────────────────────────────────────────────
# 2. 数据加载
# ──────────────────────────────────────────────────────────────────────

section("2. 数据加载（data_loader）")

base_dir = Path(os.path.dirname(os.path.abspath(__file__)))
excel_candidates = [
    base_dir / "数据.xlsx",
    base_dir.parent / "数据.xlsx",
    base_dir.parent / "paletteseek_materials" / "数据.xlsx",
]
EXCEL_PATH = None
for candidate in excel_candidates:
    if candidate.exists():
        EXCEL_PATH = str(candidate)
        break

if EXCEL_PATH is None:
    print(f"  ⚠️  找不到 数据.xlsx，请把文件放在与 backend 同级目录后重新运行")
    print(f"  ⚠️  跳过数据加载及后续检索测试")
    print("\n所有颜色工具测试通过。数据文件缺失，检索测试跳过。")
    sys.exit(0)

from data_loader import ArtworkDataset

ds = ArtworkDataset(EXCEL_PATH)
records = ds.records

check("加载记录数 = 100", len(records) == 100, f"实际：{len(records)}")

rec0 = records[0]
check("第一条有 id 字段", bool(rec0.get("id")), str(rec0.get("id")))
check("第一条有 palette_hexes", len(rec0.get("palette_hexes", [])) > 0,
      str(rec0.get("palette_hexes")))
check("第一条有 searchable_text", len(rec0.get("searchable_text", "")) > 10)
check("palette_ratios 归一化后之和 ≈ 1",
      abs(sum(rec0.get("palette_ratios", [])) - 1.0) < 0.01,
      str(rec0.get("palette_ratios")))

# get_by_id
found = ds.get_by_id(869)
check("get_by_id(869) 找到", found is not None)
if found:
    check("get_by_id 返回正确 id", str(found.get("id")) == "869", str(found.get("id")))


# ──────────────────────────────────────────────────────────────────────
# 3. 关键词检索
# ──────────────────────────────────────────────────────────────────────

section("3. 关键词检索（keyword_search）")

from search_engine import SearchEngine

engine = SearchEngine(ds)

kw_results = engine.keyword_search("蓝色 PPT", top_k=5)
check("keyword_search 返回 ≤5 条", len(kw_results) <= 5, f"实际：{len(kw_results)}")
check("结果含 _score 字段", "_score" in kw_results[0])
check("结果含 _rank 字段", "_rank" in kw_results[0])
check("第一名 _rank=1", kw_results[0]["_rank"] == 1)
check("得分降序", kw_results[0]["_score"] >= kw_results[-1]["_score"])

# 空查询
empty_results = engine.keyword_search("", top_k=5)
check("空查询返回结果（不崩溃）", isinstance(empty_results, list))


# ──────────────────────────────────────────────────────────────────────
# 4. 颜色检索
# ──────────────────────────────────────────────────────────────────────

section("4. 颜色检索（color_search）")

color_results = engine.color_search("#1E3A8A", top_k=5)
check("color_search 返回 ≤5 条", len(color_results) <= 5)
check("结果含 _score 字段", "_score" in color_results[0])
check("第一名得分 > 0", color_results[0]["_score"] > 0)

# 非法 HEX 应抛 ValueError
try:
    engine.color_search("ZZZZZZ")
    check("非法 HEX 抛 ValueError", False, "未抛出异常！")
except ValueError as e:
    check("非法 HEX 抛 ValueError", True, str(e))


# ──────────────────────────────────────────────────────────────────────
# 5. 混合检索
# ──────────────────────────────────────────────────────────────────────

section("5. 混合检索（hybrid_search）")

hybrid_results = engine.hybrid_search(query="深蓝 科技感", hex_color="#1E3A8A", top_k=5)
check("hybrid_search 返回 ≤5 条", len(hybrid_results) <= 5)
check("结果含 _color_score", "_color_score" in hybrid_results[0])
check("结果含 _text_score",  "_text_score"  in hybrid_results[0])
check("结果含 _tag_score",   "_tag_score"   in hybrid_results[0])
check("得分降序", hybrid_results[0]["_score"] >= hybrid_results[-1]["_score"])

# 只有颜色，无文本
only_color = engine.hybrid_search(hex_color="#FF0000", top_k=3)
check("仅颜色混合检索不崩溃", len(only_color) == 3)

# 只有文本，无颜色
only_text = engine.hybrid_search(query="暖色调", top_k=3)
check("仅文本混合检索不崩溃", len(only_text) == 3)

# 两者都空 → ValueError
try:
    engine.hybrid_search()
    check("两者都空抛 ValueError", False, "未抛出异常！")
except ValueError as e:
    check("两者都空抛 ValueError", True, str(e))


# ──────────────────────────────────────────────────────────────────────
# 6. 配色用途建议
# ──────────────────────────────────────────────────────────────────────

section("6. 配色用途建议（result_formatter）")

from result_formatter import format_card, generate_usage_suggestion, format_results_for_display

card = format_card({**records[0], "_score": 0.9, "_rank": 1, "_reason": "测试"})
check("format_card 含 title",            bool(card.get("title")))
check("format_card 含 palette_hexes",    bool(card.get("palette_hexes")))
check("format_card 含 usage_suggestion", bool(card.get("usage_suggestion")))

sug = card["usage_suggestion"]
check("用途建议含 背景色", "背景色" in sug, str(sug))
check("用途建议含 强调色", "强调色" in sug, str(sug))
check("所有色值合法 HEX",
      all(is_valid_hex(v) for v in sug.values()),
      str(sug))

batch = format_results_for_display(hybrid_results)
check("batch format 长度正确", len(batch) == len(hybrid_results))


# ──────────────────────────────────────────────────────────────────────
# 7. 筛选器 & 统计
# ──────────────────────────────────────────────────────────────────────

section("7. 筛选器 & 统计")

opts = engine.list_filter_options()
check("overall_tone 选项非空", len(opts.get("overall_tone", [])) > 0,
      str(opts.get("overall_tone")))
check("color_family 选项非空", len(opts.get("color_family", [])) > 0,
      str(opts.get("color_family")))

from palette_seek import PaletteSeek
ps = PaletteSeek(EXCEL_PATH)
stats = ps.stats()
check("stats total=100", stats["total"] == 100, str(stats["total"]))

filtered = engine.keyword_search("蓝色", filters={"color_family": "蓝色系"}, top_k=10)
check("筛选 蓝色系 结果非空", len(filtered) > 0, f"找到 {len(filtered)} 条")


# ──────────────────────────────────────────────────────────────────────
# 8. 完整流程测试（项目方案里的 10 个测试查询）
# ──────────────────────────────────────────────────────────────────────

section("8. 完整流程（项目方案 10 个测试查询）")

print(f"\n  {'编号':4}  {'查询词':20}  {'颜色':8}  Top1标题")
print(f"  {'-'*4}  {'-'*20}  {'-'*8}  {'-'*30}")

for qid, query, hex_c in TEST_QUERIES:
    results = ps.hybrid_search(query=query, hex_color=hex_c, top_k=1)
    if results:
        title = results[0].get("title", "")[:28]
        score = results[0].get("_score", 0)
        print(f"  {qid:4}  {query[:20]:20}  {hex_c:8}  {title}  ({score:.3f})")
    else:
        print(f"  {qid:4}  {query[:20]:20}  {hex_c:8}  （无结果）")

check("10 个测试查询均有结果",
      all(bool(ps.hybrid_search(query=q, hex_color=h, top_k=1)) for _, q, h in TEST_QUERIES))


# ──────────────────────────────────────────────────────────────────────
print(f"\n{'='*55}")
print("  🎉  所有测试通过！后端功能验证完成。")
print(f"{'='*55}\n")
