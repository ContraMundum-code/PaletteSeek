# 🎨 PaletteSeek

> **Color isn't a value. It's a story, a proportion, a feeling, and a source.**
>
> A prototype color retrieval system for visual culture — turning vague aesthetic intent into searchable, comparable, and actionable color archives.

[**🚀 Live Demo**](https://paletteseek.streamlit.app/)

---

## The Problem

When a designer searches for "a deep blue that's professional but not depressing," stock-photo sites give context without precision. Color pickers give precision without meaning. **PaletteSeek connects the two.**

Instead of asking "what color is this?", it lets you ask **"what palette fits this feeling?"**

---

## ✨ Key Features

| Feature | What it does |
|---|---|
| 🗣️ **Intent-based Retrieval** | Search with natural language — e.g., "deep blue, professional, not too warm for a thesis defense." Maps fuzzy aesthetic goals to structured artwork metadata. |
| 🎯 **Color Science Matching** | Uses **CIELab** color space and **Delta-E** distance to find visually (not just digitally) similar palettes, weighted by each color's proportion in the artwork. |
| 📋 **Complete Color Profile** | Every result is a full archive: dominant colors, hue family, cultural tags, and ready-to-use design-role suggestions (background, heading, body, accent). |
| 🛡️ **Curated vs. Open** | A core verified collection plus an independent user-upload track. The system grows without sacrificing the trustworthiness of the curated corpus. |
| 📊 **From Search to Design** | Instantly copy a full HEX set or view a visual color-network report — closing the gap between aesthetic discovery and practical production. |

---

## How it works

Users start with **text, color, or mood**, apply **multi-dimensional filters** (tone, hue family, culture, category), and receive ranked results from a hybrid scoring engine that fuses **keyword relevance + tag overlap + CIELab color distance**.

Every work in the result set expands into a full **palette profile** with proportion bars, color-network graphs, and contextual metadata so the designer understands *why* the palette works, not just *what* the colors are.

---

## Why it matters for IR

PaletteSeek explores a classic information-retrieval challenge in a new domain:

> **How do you index and retrieve subjective, aesthetic content?**

- **Semantic gap reduction**: We built structured metadata (mood, style, scene, medium) that bridges human language and visual features.
- **Multi-modal hybrid scoring**: Three independent signals (text relevance, color distance, tag overlap) are fused into a unified ranking.
- **Information quality boundary**: Two-track storage (curated vs. user-uploaded) ensures that an open system can grow without contamination.
- **Color science over RGB hackery**: CIELab-based matching overcomes the perceptual non-uniformity of simple RGB distance.

We documented candidate next steps — including natural-language semantic profiles, vector-based indexing, and design-tool export — in [`prospects.md`](prospects.md).

---

## Quick Start

```bash
git clone https://github.com/ContraMundum-code/PaletteSeek.git
cd PaletteSeek

python3 -m venv .venv
source .venv/bin/activate
pip install -r 前端/requirements.txt

streamlit run 前端/app.py
```

The app will be available at `http://localhost:8501`.

---

## Dataset & Credits

Artwork images and metadata are sourced from **Wikimedia Commons** and curated by the project team. Original source links are preserved where available.

PaletteSeek is a course project developed for the *Information Storage and Retrieval* course at **Peking University**, Department of Information Management.

---

*PaletteSeek © 2026 — Peking University, Information Management*
