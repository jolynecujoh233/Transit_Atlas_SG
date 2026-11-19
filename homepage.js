/**
 * Transit Atlas - Project Portal Interactive Logic
 * Handles: Auto/Light/Dark Themes, Bilingual i18n, Tabs, Copy-to-clipboard
 */

(function () {
  // --- Translations Dictionary ---
  const I18N = {
    en: {
      "nav_overview": "Overview",
      "nav_framework": "Framework",
      "nav_demo": "Interactive Demo",
      "nav_report": "Report & Slides",
      "nav_deploy": "Deploy Locally",
      "hero_tag": "NUS AR5958A · AI for Urban Planning · Final Deliverable",
      "hero_title": "Transit Atlas",
      "hero_subtitle": "An AI Research Agent for Planners to Explore Bus Transit Gaps",
      "hero_sub": "Bridging spatial transport analytics and LLM research agents on a 400 m grid across Singapore — empowering planners to query equity scenarios, audit data provenance, and recalculate candidate gap areas.",
      "btn_demo": "Launch Interactive Demo ↗",
      "btn_report": "View Report & Slides ↓",
      "btn_deploy": "Local Deployment ↓",
      "stat_grids": "Study Grids",
      "stat_grids_desc": "400 m × 400 m populated cells",
      "stat_indicators": "Indicators",
      "stat_indicators_desc": "9 Demand vs 11 Supply metrics",
      "stat_baseline": "Baseline Candidates",
      "stat_baseline_desc": "9.27% of Singapore study grids",
      "stat_scenario": "Healthcare Shift",
      "stat_scenario_desc": "+12 added in older clinic deficits",

      "section_context_kicker": "Context & Motivation",
      "section_context_title": "Why Bus Transit & Where Are the Gaps?",
      "section_context_desc": "Buses account for 50.9% of Singapore's daily transit boardings, yet physical station proximity does not guarantee equitable accessibility.",
      "context_col1_title": "The GIS Baseline Framework",
      "context_col1_p1": "We established an equal-weight baseline across 1,597 residential 400 m grids. By crossing Demand Level ≥ 3 with Supply Deficit Level ≥ 3, we identified 148 candidate priority areas (approx. 650,000 residents).",
      "context_col1_li1": "Jurong West: 27 candidate cells",
      "context_col1_li2": "Yishun: 18 candidate cells",
      "context_col1_li3": "Woodlands & Pasir Ris: 14 candidate cells each",
      "context_col2_title": "Critical Planning Insight",
      "context_col2_p1": "When examining individual deficit indicators, destination access barriers were flagged far more frequently than poor bus stop coverage:",
      "context_col2_li1": "91 cells flagged for 30-min supermarket access deficits",
      "context_col2_li2": "81–82 cells flagged for 30 & 60-min CHAS clinic access deficits",
      "context_col2_li3": "Only 20 cells flagged for bus-stop 400 m coverage deficits",
      "context_col2_note": "Conclusion: Enhancing transit equity requires looking beyond infrastructure presence toward destination connectivity.",

      "section_agent_kicker": "System Architecture",
      "section_agent_title": "Human-in-the-Loop 7-Step Workflow",
      "section_agent_desc": "A static GIS script cannot adapt to diverse and evolving urban planning queries. Transit Atlas couples LLM reasoning with deterministic spatial computing.",
      "step_01_title": "01 · Ask Question",
      "step_01_desc": "Planner inputs a policy question, target demographic, or time window.",
      "step_02_title": "02 · Agent Proposes",
      "step_02_desc": "Agent reviews literature and catalog, proposing indicators and data pipelines.",
      "step_03_title": "03 · Planner Audits",
      "step_03_desc": "Planner checks data provenance, formulas, and halts if key data are missing.",
      "step_04_title": "04 · Python Ingestion",
      "step_04_desc": "Acquires data, validates geometries, and normalizes into 400 m study cells.",
      "step_05_title": "05 · Propose Weights",
      "step_05_desc": "Agent suggests evidence-backed indicator weights with explicit justifications.",
      "step_06_title": "06 · Planner Adjusts",
      "step_06_desc": "Planner modifies or confirms weights before approving full execution.",
      "step_07_title": "07 · Recalculate & Map",
      "step_07_desc": "Local GIS re-scores grids, comparing retained, added and exited cells.",
      "philosophy_quote": "“AI supports research adaptation — planners retain decision control — GIS executes deterministic calculations.”",
      "philosophy_tag": "Computational consistency ≠ Real-world accuracy",

      "section_demo_kicker": "Interactive Workbench",
      "section_demo_title": "Experience the Transit Atlas Demo",
      "section_demo_desc": "Explore our interactive web interface below or open it in fullscreen. Supports exploring two research scenarios: 'Elderly Healthcare Access' and 'Weekend Bus Capacity Matching'.",
      "btn_fullscreen": "Open Fullscreen Demo ↗",

      "section_report_kicker": "Deliverables & Evaluation",
      "section_report_title": "Final Research Report & Presentation",
      "section_report_desc": "Review our complete academic report, slide deck, and methodological documentation.",
      "tab_report": "📄 Final Research Report",
      "tab_slides": "📊 Presentation Slides (Live Viewer)",
      "report_status": "✅ Final Deliverable Completed",
      "report_title": "Singapore Public Transport Supply–Demand Gap Scenario Analysis",
      "report_sub": "Final Research Report · 400 m Grid Baseline & Research Agent · November 2026",
      "report_summary": "Abstract: Where should public transport service audits begin? This study evaluates potential transit demand and service weaknesses across 1,597 residential 400-metre grid cells in Singapore. The equal-weighted baseline identifies 148 candidate cells (9.27% of study area). Adjusting older population and 30-minute clinic access weights expands this to 158 cells (+12 added, -2 removed). An AI research agent enables planners to translate natural language questions into auditable indicator proposals.",
      "report_notice": "The final revised report is embedded below for online reading and download.",
      "btn_download_draft": "Download Report Draft (PDF) ↓",
      "btn_download_final_report": "Download Full Report (1.3 MB) ↓",
      "btn_open_report_tab": "Open in New Tab ↗",
      "btn_view_slides_preview": "Preview Presentation Slides ↗",
      "slides_badge_preview_only": "Live Preview",

      "section_deploy_kicker": "Open Source & Reproduction",
      "section_deploy_title": "Deploy Transit Atlas Locally",
      "section_deploy_desc": "Full reproducibility. Run the complete GIS pipeline and connect your personal OpenAI Codex account for private, unlimited queries.",
      "deploy_step1": "1. Clone the repository",
      "deploy_step2": "2. Double-click to launch (auto-configures Python 3.12 venv & dependencies)",
      "deploy_step3": "3. Open local workbench in browser (listening at http://127.0.0.1:8764/)",
      "btn_copy": "Copy",
      "theme_auto": "🌓 Auto",
      "theme_light": "☀️ Light",
      "theme_dark": "🌙 Dark",
      "btn_copied": "Copied!",

      "map_caption_baseline": "Spatial distribution of 148 equal-weighted baseline candidate audit grids across Singapore",
      "map_caption_changes": "Healthcare scenario recalculation (Green: 146 retained; Magenta: 12 added; Slate: 2 exited)",
      "slides_filename_desc": "(21 presentation slides · Research background, methodology, and demo screen walkthroughs)",
      "btn_download_full_slides": "Download Presentation (6.6 MB) ↓",
      "deploy_card1_title": "Zero Dependency Hassle",
      "deploy_card1_desc": "start.py auto-checks Python 3.12, creates an isolated .venv, decompresses GIS layers, and installs all dependencies.",
      "deploy_card2_title": "Codex Agent Connection",
      "deploy_card2_desc": "Reuses your personal 'codex login' session from the terminal for private, interactive research dialogue without API fees.",
      "deploy_card3_title": "Complete Data Sovereignty",
      "deploy_card3_desc": "All spatial data, indicator weight revisions, and CSV exports execute deterministically on your local machine.",
      "footer_desc": "Singapore Public Transport Supply-Demand Gap Scenario Analysis Agent. Bridging 400 m grid spatial analytics with LLM research reasoning.",
      "footer_quick_nav": "Quick Navigation",
      "footer_link_overview": "Overview & Baseline",
      "footer_link_framework": "7-Step Architecture",
      "footer_link_demo": "Interactive Demo",
      "footer_link_report": "Report & Slides",
      "footer_link_deploy": "Local Deployment",
      "footer_sources_title": "Data Sources & Acknowledgements",
      "footer_course": "AR5958A · Artificial Intelligence for Urban Planning · 2026",
      "footer_team": "Group 2 (Alphabetical Order): Han Yingjie, Mao Mei, Wang Muqing, Xie Ziqian, Yue Jingqiu, Zhou Qianya",
      "footer_institution": "Department of Architecture / Urban Planning, National University of Singapore"
    },
    zh: {
      "theme_auto": "🌓 自动",
      "theme_light": "☀️ 浅色",
      "theme_dark": "🌙 深色",
      "nav_overview": "项目概览",
      "nav_framework": "协同机制",
      "nav_demo": "交互演示",
      "nav_report": "报告与成果",
      "nav_deploy": "本地部署",
      "hero_tag": "NUS AR5958A · 城市规划人工智能 · 期末成果展示",
      "hero_title": "Transit Atlas",
      "hero_subtitle": "新加坡公共交通供需缺口情景分析 Agent",
      "hero_sub": "在新加坡 400 米网格上，将空间交通分析与 LLM 研究智能体无缝链接——赋能规划师提出交通公平问题、审核数据来源并精准重算候选缺口区域。",
      "btn_demo": "在线体验 Demo ↗",
      "btn_report": "阅读报告与幻灯片 ↓",
      "btn_deploy": "本地部署指南 ↓",
      "stat_grids": "研究网格",
      "stat_grids_desc": "1,597 个 400 米常住人口网格",
      "stat_indicators": "指标体系",
      "stat_indicators_desc": "9 项需求 vs 11 项供给指标",
      "stat_baseline": "基线候选缺口",
      "stat_baseline_desc": "占新加坡全岛研究网格的 9.27%",
      "stat_scenario": "就医情景增量",
      "stat_scenario_desc": "148 → 158 格，新增 12 个就诊薄弱区",

      "section_context_kicker": "研究背景与痛点",
      "section_context_title": "为什么聚焦巴士？候选缺口落在哪里？",
      "section_context_desc": "公共巴士占新加坡公共交通日均出行量的 50.9%，但“家门口有车站”并不等同于“享有良好出行可达性”。",
      "context_col1_title": "GIS 等权基线框架",
      "context_col1_p1": "我们在 1,597 个 400 米居住网格上建立基线。通过将需求等级 ≥ 3 与供给缺口等级 ≥ 3 交叉，筛选出 148 个优先核查候选网格（覆盖约 65 万居民）。",
      "context_col1_li1": "裕廊西（Jurong West）：27 个候选网格",
      "context_col1_li2": "义顺（Yishun）：18 个候选网格",
      "context_col1_li3": "兀兰（Woodlands）与巴西立（Pasir Ris）：各 14 个网格",
      "context_col2_title": "核心规划洞察",
      "context_col2_p1": "在排查单项薄弱指标时，关键生活目的地可达性短板的出现频率显著高于物理车站覆盖：",
      "context_col2_li1": "91 个网格存在 30 分钟超市可达性薄弱",
      "context_col2_li2": "81–82 个网格存在 30 及 60 分钟 CHAS 基层诊所可达性薄弱",
      "context_col2_li3": "仅 20 个网格存在 400 米物理车站覆盖率不足",
      "context_col2_note": "规划结论：交通公平性的关键在于“目的地连通能力”，而非盲目增设物理站点。",

      "section_agent_kicker": "系统协同架构",
      "section_agent_title": "7 步人机协同循环（Human-in-the-Loop）",
      "section_agent_desc": "固定的 GIS 脚本无法穷尽规划师多元的动态提问。Transit Atlas 实现了大语言模型推理与本地确定性空间运算的紧密结合。",
      "step_01_title": "01 · 提出问题",
      "step_01_desc": "规划师在对话框输入关心的交通公平问题或特定群体出行。",
      "step_02_title": "02 · Agent 提案",
      "step_02_desc": "模型检索文献与指标目录，提出研究思路、所需数据与计算口径。",
      "step_03_title": "03 · 规划师审数",
      "step_03_desc": "核验数据来源与局限，确认计算方法。缺失核心数据时主动中止。",
      "step_04_title": "04 · 本地 GIS 处理",
      "step_04_desc": "抓取并清洗公开数据，标准化至全岛 1,597 个 400 米网格。",
      "step_05_title": "05 · Agent 建议权重",
      "step_05_desc": "依据研究重点与实证文献，提供有依据的指标权重建议。",
      "step_06_title": "06 · 规划师调权",
      "step_06_desc": "审核或修改权重数值，最终确认启动本地情景评分。",
      "step_07_title": "07 · 重算与空间对比",
      "step_07_desc": "本地程序重算网格分级，输出 148 基线对比地图与逐格 CSV 表格。",
      "philosophy_quote": "“AI 支持研究适配，规划师把关最终裁量，GIS 执行严谨计算。”",
      "philosophy_tag": "计算可复现性 ≠ 现实世界的真实准确性",

      "section_demo_kicker": "在线交互演示",
      "section_demo_title": "体验 Transit Atlas 交互工作台",
      "section_demo_desc": "在下方直接体验高仿真研究对话，或点击右上角全屏运行。支持体验「老年人就医情景」与「周末下午公交运力匹配」两个研究情景。",
      "btn_fullscreen": "全屏体验 Demo ↗",

      "section_report_kicker": "最终交付成果",
      "section_report_title": "研究报告与汇报演讲成果",
      "section_report_desc": "在线翻阅我们的完整学术报告与答辩演讲幻灯片。",
      "tab_report": "📄 最终研究报告 (Final Report)",
      "tab_slides": "📊 汇报演讲幻灯片 (Presentation Slides)",
      "report_status": "✅ 最终交付成果已定稿",
      "report_title": "《新加坡公共交通供需缺口情景分析》最终研究报告",
      "report_sub": "400 米网格基线与研究 Agent · 2026 年 11 月",
      "report_summary": "摘要：公共交通服务调查应优先从哪些居住区开始？本研究在新加坡 1,597 个估计有常住人口的 400 米网格中，分别评估居民的潜在公共交通需求与当地服务的相对薄弱程度。等权基线筛出 148 个候选网格。将老年人口与 30 分钟诊所可达性权重从 1 调至 2，得到 158 个就医情景候选网格（146 保留，12 新增，2 退出）。项目还实现了一个研究 Agent：模型把自然语言转化为可审核指标提案，规划师确认数据与权重，本地 GIS 负责运算。",
      "report_notice": "最终定稿报告已嵌入下方供在线翻阅与下载。",
      "btn_download_draft": "下载当前报告初稿 (PDF) ↓",
      "btn_download_final_report": "下载完整研究报告 (1.3 MB) ↓",
      "btn_open_report_tab": "新窗口全屏打开 ↗",
      "btn_view_slides_preview": "在线翻阅汇报幻灯片 ↗",
      "slides_badge_preview_only": "在线预览",

      "section_deploy_kicker": "开源与本地复现",
      "section_deploy_title": "本地部署完整版工作台",
      "section_deploy_desc": "纯本地严谨复现。内置完整 Python GIS 引擎，可直接连接您本机的 OpenAI Codex 账号，支持任意自由提问与私密数据计算。",
      "deploy_step1": "1. 克隆代码仓库到本地",
      "deploy_step2": "2. 双击运行启动脚本（自动完成 Python 3.12 虚拟环境与 GIS 科学计算依赖安装）",
      "deploy_step3": "3. 本地浏览器自动开启交互工作台（监听 http://127.0.0.1:8764/）",
      "btn_copy": "复制命令",
      "btn_copied": "已复制！",
      "map_caption_baseline": "全岛 148 个等权基线候选优先核查网格空间分布",
      "map_caption_changes": "就医情景重算对比（绿色：保留 146 格；洋红：新增 12 格；青灰：移出 2 格）",
      "slides_filename_desc": "(21 幻灯页 · 包含研究背景、方法论与 Demo 录屏演示)",
      "btn_download_full_slides": "下载完整幻灯片 (6.6 MB) ↓",
      "deploy_card1_title": "无依赖烦恼",
      "deploy_card1_desc": "start.py 会自动检查 Python 3.12 并自动创建 .venv 隔离环境，自动解压 GIS 图层并安装科学计算包。",
      "deploy_card2_title": "免费 Codex 连接",
      "deploy_card2_desc": "无需额外充值 API，直接复用您在命令行登录的 codex login 凭证运行研究 Agent 对话。",
      "deploy_card3_title": "完全数据主权",
      "deploy_card3_desc": "所有 GIS 原始数据、指标权重调优及 CSV 导出皆在本地确定性执行，支持完全离线研究。",
      "footer_desc": "新加坡公共交通供需缺口情景分析研究 Agent 工作台。\n结合 400 米空间网格评价模型与大语言模型研究协同机制。",
      "footer_quick_nav": "快速导航",
      "footer_link_overview": "研究背景与基线",
      "footer_link_framework": "7步人机协同架构",
      "footer_link_demo": "交互演示工作台",
      "footer_link_report": "报告与成果",
      "footer_link_deploy": "GitHub 本地部署",
      "footer_sources_title": "数据源与致谢",
      "footer_course": "NUS AR5958A · 城市规划人工智能 · 2026",
      "footer_team": "Group 2：韩颖洁、毛美、王沐晴、谢茈芊、岳婧秋、周千雅（按首字母排序）",
      "footer_institution": "新加坡国立大学 · 设计与工程学院 · 建筑与城市规划系"
    }
  };

  // --- Segmented Control Glider Animator ---
  function updateGliders() {
    document.querySelectorAll('.btn-control-group').forEach(group => {
      const glider = group.querySelector('.control-glider');
      if (!glider) return;
      const activeBtn = group.querySelector('.btn-control.active');
      if (activeBtn) {
        glider.style.width = `${activeBtn.offsetWidth}px`;
        glider.style.transform = `translateX(${activeBtn.offsetLeft}px)`;
        glider.style.opacity = '1';
      }
    });
  }

  // --- Theme Controller (Dark default, Light, Auto) ---
  const themeButtons = document.querySelectorAll('[data-theme-btn]');
  const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)');
  let themeTransitionTimer = null;

  function getStoredTheme() {
    try {
      return localStorage.getItem('transit-atlas-theme') || 'dark';
    } catch {
      return 'dark';
    }
  }

  function applyTheme(theme, smooth = false) {
    let effective = theme;
    if (theme === 'auto') {
      effective = systemPrefersDark.matches ? 'dark' : 'light';
    }

    if (smooth) {
      document.documentElement.classList.add('theme-transitioning');
      clearTimeout(themeTransitionTimer);
      themeTransitionTimer = setTimeout(() => {
        document.documentElement.classList.remove('theme-transitioning');
      }, 420);
    }

    document.documentElement.dataset.theme = effective;
    themeButtons.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.themeBtn === theme);
      btn.setAttribute('aria-pressed', String(btn.dataset.themeBtn === theme));
    });

    // Update sliding indicator position
    requestAnimationFrame(updateGliders);
  }

  function setTheme(theme) {
    try {
      localStorage.setItem('transit-atlas-theme', theme);
    } catch {}
    applyTheme(theme, true);
  }

  themeButtons.forEach(btn => {
    btn.addEventListener('click', () => setTheme(btn.dataset.themeBtn));
  });

  systemPrefersDark.addEventListener('change', () => {
    if (getStoredTheme() === 'auto') {
      applyTheme('auto', true);
    }
  });

  // Apply initial theme
  applyTheme(getStoredTheme(), false);

  // --- Language Controller (English is ALWAYS prioritized on open) ---
  const langButtons = document.querySelectorAll('[data-lang-btn]');

  // Purge any persistent localStorage that might have pinned 'zh' on open
  try {
    localStorage.removeItem('transit-atlas-lang');
  } catch {}

  function getStoredLang() {
    try {
      return sessionStorage.getItem('transit-atlas-lang') || 'en';
    } catch {
      return 'en';
    }
  }

  function applyLanguage(lang, smooth = false) {
    const targetLang = (lang === 'zh') ? 'zh' : 'en';
    const dict = I18N[targetLang];
    const elements = document.querySelectorAll('[data-i18n-key]');

    if (smooth) {
      // Gentle text fade-out before switching content
      elements.forEach(el => {
        el.style.transition = 'opacity 0.14s ease, transform 0.14s ease';
        el.style.opacity = '0.35';
        el.style.transform = 'translateY(1px)';
      });

      setTimeout(() => {
        elements.forEach(el => {
          const key = el.dataset.i18nKey;
          if (dict[key]) {
            el.textContent = dict[key];
          }
          el.style.opacity = '1';
          el.style.transform = 'translateY(0)';
        });
        document.documentElement.lang = targetLang === 'en' ? 'en' : 'zh-CN';
        langButtons.forEach(btn => {
          btn.classList.toggle('active', btn.dataset.langBtn === targetLang);
          btn.setAttribute('aria-pressed', String(btn.dataset.langBtn === targetLang));
        });
        requestAnimationFrame(updateGliders);

        // Reset transition styles after animation completes
        setTimeout(() => {
          elements.forEach(el => {
            el.style.transition = '';
            el.style.transform = '';
          });
        }, 200);
      }, 120);
    } else {
      elements.forEach(el => {
        const key = el.dataset.i18nKey;
        if (dict[key]) {
          el.textContent = dict[key];
        }
      });
      document.documentElement.lang = targetLang === 'en' ? 'en' : 'zh-CN';
      langButtons.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.langBtn === targetLang);
        btn.setAttribute('aria-pressed', String(btn.dataset.langBtn === targetLang));
      });
      requestAnimationFrame(updateGliders);
    }
  }

  function setLanguage(lang) {
    try {
      sessionStorage.setItem('transit-atlas-lang', lang);
    } catch {}
    applyLanguage(lang, true);
  }

  langButtons.forEach(btn => {
    btn.addEventListener('click', () => setLanguage(btn.dataset.langBtn));
  });

  // Apply initial language (strictly English prioritized)
  applyLanguage(getStoredLang(), false);

  // Re-align gliders on window resize or load
  window.addEventListener('resize', updateGliders, { passive: true });
  window.addEventListener('load', updateGliders, { passive: true });
  setTimeout(updateGliders, 50);

  // --- Deliverables Tab Switcher (Report vs Slides) ---
  const deliverableTabs = document.querySelectorAll('[data-deliverable-tab]');
  const deliverablePanels = document.querySelectorAll('[data-deliverable-panel]');

  deliverableTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.deliverableTab;
      deliverableTabs.forEach(t => {
        t.classList.toggle('active', t === tab);
        t.setAttribute('aria-pressed', String(t === tab));
      });
      deliverablePanels.forEach(panel => {
        panel.hidden = panel.dataset.deliverablePanel !== target;
      });
    });
  });

  // --- Copy Code Snippets ---
  const copyButtons = document.querySelectorAll('.copy-btn');
  copyButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.dataset.copyTarget;
      const targetEl = document.getElementById(targetId);
      if (!targetEl) return;
      const textToCopy = targetEl.innerText.replace(/^#.*$/gm, '').trim();
      navigator.clipboard.writeText(textToCopy).then(() => {
        const lang = getStoredLang();
        const originalText = btn.textContent;
        btn.textContent = I18N[lang].btn_copied;
        setTimeout(() => {
          btn.textContent = originalText;
        }, 1800);
      });
    });
  });

  // --- Jump to Presentation Slides Tab ---
  const jumpBtn = document.getElementById('btn-jump-to-slides');
  if (jumpBtn) {
    jumpBtn.addEventListener('click', () => {
      const slidesTabBtn = document.querySelector('[data-deliverable-tab="slides"]');
      if (slidesTabBtn) {
        slidesTabBtn.click();
        const deliverablesEl = document.getElementById('deliverables');
        if (deliverablesEl) {
          deliverablesEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    });
  }

  // --- Ambient Mouse Glow Follower ---
  const ambientGlow = document.getElementById('ambient-glow');
  if (ambientGlow && window.matchMedia('(pointer: fine)').matches) {
    let targetX = -1000, targetY = -1000;
    let currentX = -1000, currentY = -1000;
    let isMoving = false;

    function renderGlow() {
      // Smooth lerp interpolation for silky motion
      currentX += (targetX - currentX) * 0.16;
      currentY += (targetY - currentY) * 0.16;
      ambientGlow.style.transform = `translate(${currentX}px, ${currentY}px) translate(-50%, -50%)`;
      if (Math.abs(targetX - currentX) > 0.4 || Math.abs(targetY - currentY) > 0.4) {
        requestAnimationFrame(renderGlow);
      } else {
        isMoving = false;
      }
    }

    window.addEventListener('pointermove', (e) => {
      targetX = e.clientX;
      targetY = e.clientY;
      ambientGlow.style.opacity = '1';
      if (!isMoving) {
        isMoving = true;
        requestAnimationFrame(renderGlow);
      }
    }, { passive: true });

    document.addEventListener('mouseleave', () => {
      ambientGlow.style.opacity = '0';
    });
  }

  // --- Card Mouse Hover Spotlight Effect ---
  const spotlightCards = document.querySelectorAll(
    '.stat-card, .feature-card, .workflow-card, .report-placeholder-card, .deploy-card'
  );
  spotlightCards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      card.style.setProperty('--mouse-x', `${x}px`);
      card.style.setProperty('--mouse-y', `${y}px`);
    }, { passive: true });
  });

  // --- Back to Top Floating Button ---
  const backToTopBtn = document.getElementById('back-to-top');
  if (backToTopBtn) {
    window.addEventListener('scroll', () => {
      if (window.scrollY > 380) {
        backToTopBtn.classList.add('visible');
      } else {
        backToTopBtn.classList.remove('visible');
      }
    }, { passive: true });

    backToTopBtn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // --- Scroll-Driven Kinetic Reveal for Headings, Cards & Containers ---
  const revealTargets = document.querySelectorAll(
    '.section-kicker, .section-title, .section-desc, .feature-card, .workflow-card, .demo-window, .deliverables-container, .deploy-card, .philosophy-banner'
  );

  revealTargets.forEach(el => {
    el.classList.add('scroll-reveal');
  });

  if ('IntersectionObserver' in window) {
    const revealObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-revealed');
        } else {
          // When scrolling completely out of screen bounds (above or below),
          // reset so scrolling back up/down re-triggers the fluid entrance animation!
          const rect = entry.boundingClientRect;
          if (rect.top > window.innerHeight || rect.bottom < 0) {
            entry.target.classList.remove('is-revealed');
          }
        }
      });
    }, {
      root: null,
      threshold: [0, 0.12],
      rootMargin: '0px 0px -40px 0px'
    });

    revealTargets.forEach(el => revealObserver.observe(el));
  } else {
    revealTargets.forEach(el => el.classList.add('is-revealed'));
  }
})();
