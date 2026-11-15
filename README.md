# Transit Atlas: An AI Research Agent for Planners to Explore Bus Transit Gaps
### 新加坡公共交通供需缺口情景分析 Agent

> **National University of Singapore (NUS) · AR5958A Artificial Intelligence for Urban Planning**  
> **Final Project Deliverable · Group 2 (2026)**  
> **Team Members (Alphabetical Order)**: Han Yingjie, Mao Mei, Wang Muqing, Xie Ziqian, Yue Jingqiu, Zhou Qianya  

[![Live Portal](https://img.shields.io/badge/Live%20Portal-GitHub%20Pages-success?style=for-the-badge&logo=github)](https://jolynecujoh233.github.io/Transit_Atlas_SG/)
[![Interactive Demo](https://img.shields.io/badge/Interactive%20Demo-Online-purple?style=for-the-badge)](https://jolynecujoh233.github.io/Transit_Atlas_SG/demo-site/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

---

## 🧭 Quick Links & Deliverables / 快速链接与成果入口

- 🌐 **Project Portal (Live Website) / 在线项目主页**:  
  👉 **[https://jolynecujoh233.github.io/Transit_Atlas_SG/](https://jolynecujoh233.github.io/Transit_Atlas_SG/)**  
  *Explore the comprehensive project landing page, switch between Light and Dark themes, toggle English/Chinese, inspect baseline spatial maps, and review embedded deliverables.*  
  *（访问项目完整总主页，支持浅色/深色主题切换、中英双语切换、查看 148 基线空间地图与全量交付物展示。）*

- 🕹️ **Interactive Workbench Demo / 在线交互演示工作台**:  
  👉 **[https://jolynecujoh233.github.io/Transit_Atlas_SG/demo-site/](https://jolynecujoh233.github.io/Transit_Atlas_SG/demo-site/)**  
  *Experience the high-fidelity research dialogue simulator. Test the "Healthcare Access for Seniors (148 → 158 cells)" scenario and the "Weekend Afternoon Bus Service" honest data-gap review.*  
  *（体验高仿真研究对话工作台。支持模拟测试「老年人就医情景（148 → 158 格）」与「周末下午公交服务（规划边界与数据缺失核验）」两个典型案例。）*

- 📊 **Presentation Slides (PDF) / 汇报演讲幻灯片**:    
  *The full 21-slide deck covering urban mobility challenges, the 400 m GIS baseline, the 7-step Human-in-the-Loop agent architecture, scenario results, and critical limitations.*  
  *（完整 21 页答辩幻灯片，涵盖交通出行痛点、400 米网格基线、7 步人机协同架构、情景对比结果与反思局限。）*

- 📄 **Final Research Report / 最终学术研究报告**:  
  👉 **[`assets/report_draft.pdf`](assets/report_draft.pdf)** *(Draft available; final revised version will be embedded upon final review / 初稿已就绪，定稿核校完成后无缝替换)*  
  *Full academic report: "Singapore Public Transport Supply–Demand Gap Scenario Analysis: 400 m Grid Baseline & Research Agent".*  
  *（完整学术论文：《新加坡公共交通供需缺口情景分析：400 米网格基线与研究 Agent》。）*



---

## 🌟 Project Overview / 项目简介

**Where should public transport service audits begin?**  
**公共交通服务调查应优先从哪些居住区开始？**

Public buses account for **50.9%** of Singapore's daily transit journeys, yet physical proximity to a bus stop does not equate to equitable access. Traditional GIS analyses rely on fixed scripts and predetermined weights that struggle to respond to evolving policy questions or vulnerable community needs. Conversely, pure large language models (LLMs) lack rigorous spatial calculation engines and data provenance.  
公共巴士占新加坡公共交通日均出行量的 **50.9%**，但“家门口有车站”并不等同于“享有良好出行可达性”。传统 GIS 分析往往依赖固定脚本和预设权重，无法灵活应对规划师动态演化的政策关切与弱势群体需求；而纯大语言模型（LLM）又缺乏严谨的空间计算能力与数据真实性保障。

**Transit Atlas** bridges spatial transport analytics and LLM research agents through a **7-Step Human-in-the-Loop Workflow**:  
**Transit Atlas** 构建了一个面向城市规划师的 **7 步人机协同（Human-in-the-Loop）研究工作台**：

1. **Island-wide 400 m Grid Evaluation / 全岛 400 米网格评价**:  
   Evaluates 1,597 residential 400-metre cells across Singapore using 9 Demand indicators vs 11 Supply deficit metrics.  
   在新加坡 1,597 个估计有常住人口的 400 米居住网格上，构建 9 项需求指标 vs 11 项供给薄弱指标体系。

2. **Equal-Weighted GIS Baseline / 等权 GIS 基线筛选**:  
   Identified **148 candidate priority audit cells** (~650,000 residents) by crossing Demand Level ≥ 3 with Supply Deficit Level ≥ 3.  
   通过将需求等级 ≥ 3 与供给缺口等级 ≥ 3 交叉，筛选出 **148 个候选优先核查网格**（覆盖约 65 万居民）。

3. **Critical Planning Insight / 核心规划洞察**:  
   Only 20 cells exhibited bus-stop 400 m coverage deficits, whereas **91 cells suffered 30-min supermarket access deficits** and **81–82 cells had CHAS clinic access deficits**. Enhancing transit equity requires prioritizing destination connectivity over simply adding physical stops.  
   全岛仅 20 个网格存在 400 米物理站点覆盖不足，但多达 **91 个网格存在 30 分钟超市可达短板**、**81~82 个网格存在 CHAS 基层诊所可达短板**——交通公平的核心瓶颈在于“目的地连通能力”，而非盲目加密物理站点。

4. **AI Research Agent Collaboration / AI 研究 Agent 协同机制**:  
   The LLM interprets natural language policy questions and proposes evidence-backed indicator weights; planners review data sources and formulas; the local GIS executes deterministic computations.  
   大语言模型负责理解规划师的自然语言提问并提出文献支撑的指标权重建议；规划师把关数据口径与指标权重；本地 GIS 引擎执行确定性空间重算。

5. **Healthcare Scenario Verification / 就医情景增量验证**:  
   Increasing the weights for older residents and 30-min CHAS clinic access from 1 to 2 flagged **158 candidate cells** (146 retained, 12 added, 2 exited), pinpointing mature public housing estates with high elderly populations and clinic access gaps.  
   将老年人口与 30 分钟诊所可达性权重从 1 调整至 2，精准识别出 **158 个候选网格**（146 保留，12 新增，2 退出），新增区域高度集中在老年人比例高但基层就诊可达薄弱的典型成熟组屋区。

---

## 🔄 7-Step Human-in-the-Loop Architecture / 7 步人机协同循环

```
[01 Planner Asks]  ──> [02 Agent Literature & Indicators Proposal] ──> [03 Planner Audits Data]
                                                                                │
[06 Planner Adjusts Weights] <── [05 Agent Recommends Weights]     <── [04 Local GIS Ingestion]
         │
         └──> [07 Local GIS Recalculates & Compares 148 Baseline]   ──> [Map / CSV Exports]
```

- **Step 01 · Ask Question / 提出问题**: Planner enters a policy concern or target demographic into the chat. (规划师在对话框输入关心的交通公平问题或特定群体出行。)
- **Step 02 · Agent Proposes / Agent 提案**: Agent searches literature and catalog, proposing indicators and data requirements. (模型检索文献与指标目录，提出研究思路、所需数据与计算口径。)
- **Step 03 · Planner Audits / 规划师审数**: Planner checks data sources and limitations; halts if key data is missing. (核验数据来源与局限，确认计算方法。缺失核心数据时主动中止。)
- **Step 04 · Python Ingestion / 本地 GIS 处理**: Fetches open data, validates geometries, and normalizes into 400 m grids. (清洗公开数据，标准化至全岛 1,597 个 400 米网格。)
- **Step 05 · Propose Weights / Agent 建议权重**: Agent suggests evidence-based indicator weights with explicit citations. (依据研究重点与实证文献，提供有依据的指标权重建议。)
- **Step 06 · Planner Adjusts / 规划师调权**: Planner confirms or modifies weight values before authorizing computation. (审核或修改权重数值，最终确认启动本地情景评分。)
- **Step 07 · Recalculate & Map / 重算与空间对比**: Local GIS re-scores grids, comparing added, retained, and exited areas against the 148 baseline. (本地程序重算网格分级，输出 148 基线对比地图与逐格 CSV 表格。)

> **Core Philosophy / 核心设计哲学**:  
> *“AI supports research adaptation — planners retain decision control — GIS executes deterministic calculations.”*  
> *“AI 支持研究适配，规划师把关最终裁量，GIS 执行严谨计算。”*  
> *Computational consistency ≠ Real-world accuracy. (计算可复现性 ≠ 现实世界的真实准确性。)*

---

## 💻 Local Deployment Guide / 本地部署完整版工作台

The local workbench features a complete Python GIS engine and can connect directly to your personal OpenAI Codex account for private, unlimited queries.  
本地工作台内置完整 Python GIS 引擎，可直接连接您本机的 OpenAI Codex 账号，支持任意自由提问与完全私密的数据计算。

### 1. System Requirements / 系统要求
- **Operating System / 操作系统**: Windows 10/11, macOS 12+, or Linux (Ubuntu 22.04+)
- **Python Environment / Python 环境**: **Python 3.12** *(Recommended for GIS C-extension wheels / 强烈建议 3.12 版本以保证科学计算包兼容)*
- **Git**: For cloning the repository / 用于克隆代码仓库
- **OpenAI Codex CLI (Optional / 可选，用于驱动自由对话 Agent)**:
  ```bash
  npm install -g @openai/codex
  codex login
  ```

### 2. Clone & Launch / 克隆与一键启动

```bash
# Clone repository / 克隆仓库
git clone https://github.com/jolynecujoh233/Transit_Atlas_SG.git
cd Transit_Atlas_SG
```

#### Windows Users (One-Click Launch / 推荐一键启动):
Double-click **`Start-Workbench.cmd`** in the root directory.  
双击根目录下的 **`Start-Workbench.cmd`** 脚本。该脚本会自动完成：
- Auto-detects Python 3.12 / 自动检查 Python 3.12 环境
- Creates and activates the `.venv` virtual environment / 自动创建并激活虚拟环境
- Automatically decompresses GIS datasets (including the 166 MB URA Master Plan layer) / 自动解压大型空间图层
- Installs all dependencies from `requirements.txt` / 自动安装科学计算与 GIS 依赖
- Launches the local server and opens **`http://127.0.0.1:8764/`** in your browser / 自动拉起后端并开启工作台

#### macOS / Linux Users / 苹果与 Linux 用户:
```bash
# Run bootstrap launcher / 运行启动引导脚本
python3.12 start.py

# Optional: verify dependencies and Codex login status only / 仅自检环境
python3.12 start.py --check
```

---

## 📂 Repository Structure / 仓库目录结构

```text
Transit_Atlas_SG/
├── index.html                 # Project portal landing page (项目总主页，支持自选浅色/深色主题与中英文)
├── homepage.css               # Portal stylesheet with adaptive Light & Dark themes (主页样式表)
├── homepage.js                # Portal interactive logic (i18n, themes, tabs, copy snippet) (主页交互逻辑)
├── demo-site/                 # High-fidelity static demo site (适合 GitHub Pages 部署的高仿真体验版)
│   ├── index.html             # Demo single-page app with interactive research dialogue (演示页入口)
│   ├── demo.js                # Simulated Agent dialogue, thinking animation, & scenario scoring (交互逻辑)
│   ├── i18n.js                # Bilingual dictionary for demo and user guide (演示版双语字典)
│   └── style.css              # Cyber Cartographic dark workbench UI (地图工作台样式)
├── workbench/                 # Full local Python backend and GIS workbench (本地完整版工作台)
│   ├── server.py              # Local server engine & Codex subprocess integration (后端服务引擎)
│   ├── app.js                 # Workbench frontend application logic (前端核心应用逻辑)
│   ├── research_agent.py      # LLM prompt engineering & agent coordinator (研究 Agent 驱动模块)
│   └── i18n.js                # Workbench bilingual translations (工作台双语支持)
├── analysis/                  # Deterministic GIS analysis scripts (确定性 GIS 空间计算脚本)
│   ├── baseline_gis.py        # 1,597-grid equal-weighted baseline computation (基线计算算法)
│   └── scenario_eval.py       # Scenario weight recalculation & cell audit comparison (情景比对算法)
├── data/                      # Spatial datasets (Compressed <50MB for clean GitHub hosting) (空间数据库)
│   ├── demand/                # Demand layers (population, elderly, low-income, school-age, etc.)
│   ├── supply/                # Supply layers (bus stops, routes, supermarket, CHAS clinics, etc.)
│   └── manifest.json          # Catalog manifest & field data dictionary (数据源字典与元数据)
├── assets/                    # Media & Final Deliverable Documents (多媒体与交付文档)
│   ├── presentation.pdf       # 21-slide presentation deck (21 页汇报演讲文稿与演示幻灯片)
│   ├── report_draft.pdf       # Academic research report draft (最终研究报告初稿)
│   ├── baseline_148.png       # 148 Baseline Candidate Areas Map (148 基线网格分布图)
│   └── changes_map.png        # Healthcare Scenario Map Changes (就医情景增减对比图)
├── start.py                   # Python environment bootstrap script (含自动解压与依赖管理)
├── Start-Workbench.cmd        # Windows one-click start batch file (Windows 一键启动批处理)
├── Push-To-GitHub.cmd         # Helper script for GitHub synchronisation (GitHub 一键推送辅助脚本)
├── requirements.txt           # Python package requirements (Python 依赖清单)
└── README.md                  # Project documentation (项目说明文档)
```

---

## 🌐 Bilingual Support & Adaptive Themes / 双语支持与主题说明

- **Bilingual Interface / 中英双语原生支持**:  
  Both the Project Portal, Interactive Demo, and Local Workbench support one-click switching between `[EN]` and `[中文]`. Preferences are persisted in `localStorage`.  
  项目主页、在线 Demo 及本地工作台均已原生内置双语切换器，点击右上角 `[EN | 中文]` 即可即时切换，偏好自动保存。
- **Adaptive Visual Themes / 自适应与自调主题**:  
  - **🌓 Auto (Automatic / 自动)**: Automatically synchronizes with your operating system preference. (跟随操作系统浅色/深色设置自动切换。)  
  - **☀️ Light (Editorial Academic / 浅色极简)**: Optimized for scholarly reading, documentation, and reports. (专为学术阅读与报告翻阅优化的清新明亮风格。)  
  - **🌙 Dark (Cyber Cartographic / 深色科技)**: High-contrast cartographic interface matching the GIS workbench. (延续专业 GIS 制图与夜间工作台的高对比度深色风格。)

---

## 📊 Data Sources & Citations / 数据源与致谢

All spatial datasets are obtained from official Singapore Government open data portals:  
本项目所采用的所有空间与交通数据均来自新加坡官方公开数据门户：
- **Land Transport Authority (LTA) DataMall**: Bus stops, passenger volumes, bus routes, and GTFS schedules. (公交站点、客流、班次与 GTFS 班表数据)
- **Department of Statistics Singapore (SingStat)**: Census 2020 subzone demographics, age brackets, and household income. (人口普查统计、年龄结构与收入特征)
- **Singapore Land Authority (SLA) OneMap API**: Pedestrian road network topology, facility geocoding, and isochrones. (路网拓扑、设施点位与等时圈)
- **Urban Redevelopment Authority (URA)**: Master Plan 2019 Land Use zoning polygons. (Master Plan 2019 土地利用规划图层)

---

## 👥 Contributors / 课题组成员

**Group 2 · National University of Singapore (NUS)**  
*Department of Architecture / Urban Planning · AR5958A Artificial Intelligence for Urban Planning (2026)*  

- **Han Yingjie**
- **Mao Mei**
- **Wang Muqing**
- **Xie Ziqian**
- **Yue Jingqiu**
- **Zhou Qianya**
