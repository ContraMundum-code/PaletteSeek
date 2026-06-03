# PaletteSeek 后端说明

## 文件结构

```
paletteseek_backend/
├── palette_seek.py       # 前端统一入口（只需导入这一个）
├── search_engine.py      # 检索核心：关键词 / 颜色 / 混合
├── color_utils.py        # 颜色工具：HEX↔RGB↔Lab、Delta-E
├── data_loader.py        # 数据加载：读 Excel、派生字段
├── result_formatter.py   # 结果格式化：卡片、配色建议
├── test_backend.py       # 功能验证脚本
└── requirements.txt
```

数据文件可以放在以下任一位置：

```
后端/
├── 数据.xlsx               ← 推荐，放在 paletteseek_backend 同级
├── color_cards/            ← 色卡图片目录（解压后）
└── paletteseek_backend/    ← 代码目录

或：

后端/
└── paletteseek_backend/
    ├── 数据.xlsx
    └── ...
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 验证功能

```bash
cd paletteseek_backend
python test_backend.py
```

## 前端使用方式（Streamlit）

```python
import streamlit as st
from paletteseek_backend import PaletteSeek

# ① 初始化（只跑一次，用 cache_resource 缓存）
@st.cache_resource
def load_backend():
    return PaletteSeek(
        excel_path="数据.xlsx",
        color_cards_dir="color_cards",   # 可选，本地色卡目录
    )

ps = load_backend()

# ② 关键词检索
results = ps.keyword_search("深蓝 PPT 稳重", top_k=10)

# ③ 颜色检索（输入 HEX）
results = ps.color_search("#1E3A8A", top_k=10)

# ④ 混合检索（推荐）
results = ps.hybrid_search(
    query="科技感 数据大屏",
    hex_color="#1E3A8A",
    top_k=10,
)

# ⑤ 首页展示全部作品
all_cards = ps.get_all(top_k=20)

# ⑥ 按 ID 获取单件
card = ps.get_by_id(869)

# ⑦ 筛选下拉菜单选项
opts = ps.list_filter_options()
# {"overall_tone": [...], "color_family": [...], "culture": [...], ...}
```

## 每条结果的字段说明

```python
{
    # 基本信息
    "id", "title", "artist", "year",
    "culture", "classification", "medium",

    # 图片
    "image_url",                  # 可直接展示的原作图片 URL
    "palette_image_filename",     # 色卡图片文件名（如 869_palette.png）

    # 调色盘
    "palette_hexes",   # list[str]，最多 9 个主色 HEX
    "palette_ratios",  # list[float]，对应占比（0~1）
    "color_names",     # list[str]，中文颜色名

    # 色彩属性
    "overall_tone",    # 整体色调，如 "深色调"、"浅色调"
    "color_family",    # 主色系，如 "蓝色系"、"橙色系"

    # 标签
    "color_tags", "emotion_tags", "style_tags", "use_tags",

    # 来源
    "source_url",

    # 检索附加字段
    "_score",         # 综合得分 (0~1)
    "_rank",          # 排名（从 1 开始）
    "_reason",        # 自动生成的推荐理由
    "_color_score",   # 颜色分量（混合检索时有值）
    "_text_score",    # 文本分量
    "_tag_score",     # 标签分量

    # 配色用途建议
    "usage_suggestion": {
        "背景色": "#HEX",
        "标题色": "#HEX",
        "正文色": "#HEX",
        "强调色": "#HEX",
        "辅助色": "#HEX",
    }
}
```

## 色卡图片使用（前端）

色卡图片的本机绝对路径已从 `palette_image_path` 字段去掉，
前端只得到纯文件名（`palette_image_filename`，如 `869_palette.png`）。

**本地 Streamlit 运行时：**

```python
import streamlit as st
from pathlib import Path

card = results[0]
palette_img = Path("color_cards") / card["palette_image_filename"]
if palette_img.exists():
    st.image(str(palette_img))
```

**或使用 get_palette_image_path 方法：**

```python
ps = PaletteSeek("数据.xlsx", color_cards_dir="color_cards")
path = ps.get_palette_image_path(card["id"])
if path:
    st.image(str(path))
```

## 检索得分说明

| 检索模式 | 得分公式 |
|---|---|
| keyword_search | 0.6 × TF-IDF相关度 + 0.4 × 标签匹配度 |
| color_search   | Delta-E感知距离转换的调色盘相似度（0~1） |
| hybrid_search  | **0.4 × 颜色相似度 + 0.3 × 标签匹配度 + 0.3 × 文本相关度** |

颜色相似度使用 **CIELab Delta-E**（感知均匀颜色空间），比 RGB 欧氏距离更接近人眼对颜色差异的感受。

## 筛选器

```python
# 只检索蓝色系、深色调的作品
results = ps.keyword_search(
    "科技感",
    filters={
        "color_family": "蓝色系",
        "overall_tone": "深色调",
    }
)
```

支持的筛选字段：`color_family`、`overall_tone`、`culture`、`classification`（包含匹配，不区分大小写）。
