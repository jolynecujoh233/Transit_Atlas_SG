# Transit Atlas · 新加坡公共交通供需缺口情景分析 Agent

> **National University of Singapore (NUS) · AR5958A Artificial Intelligence for Urban Planning**  
> **Final Group Project · Group 2**  
> 组员 (Team Members)：Han Yingjie, Mao Mei, Wang Muqing, Xie Ziqian, Yue Jingqiu, Zhou Qianya  

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Bilingual](https://img.shields.io/badge/Language-EN%20%7C%20%E4%B8%AD%E6%96%87-purple.svg)](#bilingual-support)

---

## 🌟 项目简介 (Project Overview)

**公共交通服务调查应优先从哪些居住区开始？**

公共巴士占新加坡公共交通日均出行量的 **50.9%**，但“家门口有车站”并不等同于“享有良好出行可达性”。传统 GIS 分析往往依赖固定脚本和预设权重，无法灵活应对规划师动态演化的政策关切与弱势群体需求；而纯大语言模型（LLM）又缺乏严谨的空间计算能力与数据真实性保障。

**Transit Atlas** 构建了一个面向城市规划师的 **7 步人机协同（Human-in-the-Loop）研究工作台**：
1. **全岛 400 米网格评价**：在新加坡 1,597 个常住人口居住网格上，构建 9 项需求 vs 11 项供给指标体系。
2. **等权 GIS 基线**：筛选出 **148 个候选优先核查网格**（约 65 万居民）。
3. **关键规划洞察**：全岛仅 20 个网格存在 400 米物理站点覆盖不足，但多达 91 个网格存在超市可达短板、81~82 个网格存在 30/60 分钟 CHAS 基层诊所可达短板——**交通公平的核心瓶颈在于“目的地连通能力”，而非盲目加密物理站点**。
4. **AI 研究 Agent 协同**：大语言模型负责理解规划师的自然语言提问并提出文献支撑的指标权重建议；规划师全流程审核数据口径与指标权重；本地 GIS 引擎执行确定性空间重算。
5. **就医情景增量验证**：将老年人口与 30 分钟诊所可达性权重从 1 调整至 2，精准识别出 **158 个候选网格**（146 保留，12 新增，2 退出），新增区域高度集中在老年人比例高但基层就诊可达薄弱的典型组屋区。

---

## 🧭 快速链接 (Quick Links)

- 🌐 **在线项目主页 (Project Portal)**: 直接访问本仓库的 GitHub Pages 主页，查阅项目概况、双语切换、极简/深色主题。
- 🕹️ **在线交互演示 (Interactive Demo)**: 部署于 `demo-site/` 目录，前端高仿真还原工作台对话交互（支持体验「老年人就医情景」与「周末下午公交边界识别」）。
- 📊 **汇报演讲幻灯片 (Presentation Slides)**: 查阅 `assets/presentation.pdf`（21 页答辩演示文稿与录屏说明）。
- 📄 **最终研究报告 (Final Research Report)**: 查阅 `assets/final_report.pdf` / `assets/report_draft.pdf`。

---

## 🔄 7 步人机协同循环 (7-Step Workflow)

```
[01 规划师提问] ──> [02 Agent检索文献与指标库提案] ──> [03 规划师审核数据与口径]
                                                                  │
[06 规划师审改权重] <── [05 Agent生成建议权重与论证] <── [04 本地GIS数据清洗入格]
         │
         └──> [07 本地GIS重算情景评分与148基线空间对比] ──> [交互地图/CSV成果导出]
```

> **核心设计哲学**：  
> *“AI 支持研究适配，规划师把关最终裁量，GIS 执行严谨计算。”*  
> *计算可复现性（Computational Consistency）≠ 现实世界的真实准确性（Real-world Accuracy）。*

---

## 💻 本地部署指南 (Local Deployment Guide)

本地工作台内置完整 Python GIS 引擎，可直接连接您本机的 OpenAI Codex 账号，支持**任意自由提问**与**完全私密的数据计算**。

### 1. 系统要求 (Requirements)
- **操作系统**：Windows 10/11，macOS 12+，或 Linux (Ubuntu 22.04+)
- **Python 环境**：**Python 3.12**（强烈建议 3.12 版本以保证 GIS 科学计算轮子兼容性）
- **Git**：用于克隆代码仓库
- **OpenAI Codex CLI**（可选，用于开启本地 Agent 智能对话）：
  ```bash
  npm install -g @openai/codex
  codex login
  ```

### 2. 克隆仓库与启动 (Clone & Launch)

```bash
# 克隆仓库
git clone https://github.com/jolynecujoh233/Transit_Atlas_SG.git
cd Transit_Atlas_SG
```

#### Windows 用户（推荐一键启动）：
直接双击运行根目录下的 **`Start-Workbench.cmd`**。  
脚本会自动完成：
- 检查 Python 3.12 环境
- 自动创建并激活 `.venv` 虚拟环境
- 自动解压并就绪 GIS 空间数据库（包含 Master Plan 2019 大数据集）
- 自动安装 `requirements.txt` 中所需依赖（geopandas, fastapi, uvicorn 等）
- 自动拉起后端并在浏览器中打开 `http://127.0.0.1:8764/`

#### macOS / Linux 用户：
```bash
# 运行启动引导脚本
python3.12 start.py

# 首次运行可添加 --check 参数仅自检依赖与 Codex 登录状态
python3.12 start.py --check
```

---

## 📂 仓库目录结构 (Repository Structure)

```text
transit-atlas/
├── index.html                 # 项目公开主页 (Project Portal Landing Page)
├── homepage.css               # 主页样式表 (支持 Auto / 极简 Light / 深色 Dark 主题)
├── homepage.js                # 主页交互逻辑 (主题切换、中英文 i18n、报告/幻灯片 Tab、代码复制)
├── demo-site/                 # 静态高仿真在线体验版 (适合 GitHub Pages 部署)
│   ├── index.html             # 体验版单页入口 (包含研究对话、地图对比与使用指南)
│   ├── demo.js                # 交互对话与情景重算模拟逻辑
│   ├── i18n.js                # 双语翻译字典
│   └── style.css              # 地图工作台经典深色科技 UI
├── workbench/                 # 本地完整版工作台后端与静态服务
│   ├── server.py              # 本地服务引擎 (支持 API、静态路由与 Codex 串接)
│   ├── app.js                 # 工作台前端核心逻辑 (支持任意自由对话与交互重算)
│   ├── research_agent.py      # 研究 Agent 提示词工程与 Codex 驱动模块
│   └── i18n.js                # 本地工作台双语支持
├── analysis/                  # 确定性 GIS 空间计算脚本
│   ├── baseline_gis.py        # 1,597 网格等权基线计算逻辑
│   └── scenario_eval.py       # 情景权重调整与网格进退对比算法
├── data/                      # 空间数据库 (已严格压缩优化以适应 GitHub 100MB 限制)
│   ├── demand/                # 需求侧指标图层 (人口、老年人、低收入、学龄、TOD 等)
│   ├── supply/                # 供给侧指标图层 (公交班次、站点覆盖、超市场所、CHAS诊所等)
│   └── manifest.json          # 数据源元数据清单与字段字典
├── assets/                    # 多媒体与最终交付文档
│   ├── presentation.pdf       # 21 页汇报演讲文稿与演示幻灯片
│   ├── report_draft.pdf       # 最终学术报告初稿
│   ├── baseline_148.png       # 148 基线网格分布图
│   └── changes_map.png        # 就医情景空间进退变化图
├── start.py                   # 本地 Python 环境一键引导脚本 (含自动解压与依赖构建)
├── Start-Workbench.cmd        # Windows 一键启动脚本
├── requirements.txt           # Python 依赖清单
└── README.md                  # 项目说明文档
```

---

## 🌐 双语支持与主题说明 (Bilingual & Themes)

- **中英双语 (EN | 中文)**：
  - 项目主页、在线 Demo、本地工作台均已原生内置双语切换器。
  - 点击右上角 `[EN | 中文]` 按钮即可即时切换，偏好自动持久化于浏览器的 `localStorage` 中。
- **自适应与自调主题 (Auto | Light | Dark)**：
  - **🌓 Auto (自动)**：跟随操作系统系统的浅色/深色外观设置无缝切换。
  - **☀️ 极简 (Editorial Academic Light)**：专为学术阅读与报告翻阅优化的清新明亮风格。
  - **🌙 深色 (Cyber Cartographic Dark)**：延续专业 GIS 制图与夜间工作台的高对比度深色风格。

---

## 📊 数据来源与声明 (Data Sources & Citation)

本项目所采用的所有空间与交通数据均来自新加坡官方公开数据门户：
- **Land Transport Authority (LTA) DataMall**：公交站点位置、公交线路运行班次与 GTFS 数据
- **Department of Statistics Singapore (SingStat)**：亚分区人口普查统计、年龄结构与收入特征
- **Singapore Land Authority (SLA) OneMap API**：路网拓扑、公共服务设施点位与等时圈计算
- **Urban Redevelopment Authority (URA)**：Master Plan 2019 土地利用规划图层

---

## 👥 课题组成员 (Group 2 Contributors)

- **Han Yingjie**
- **Mao Mei**
- **Wang Muqing**
- **Xie Ziqian**
- **Yue Jingqiu**
- **Zhou Qianya**

*National University of Singapore (NUS) · Department of Architecture / Urban Planning*  
*Course: AR5958A Artificial Intelligence for Urban Planning (2026)*
