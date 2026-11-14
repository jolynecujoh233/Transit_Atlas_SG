const $ = s => document.querySelector(s);
const t = text => window.I18n.t(text);

const pages = {
  overview: ['新加坡公共交通供需图谱', '在 400 米网格上，对照出行需求与公共交通供给。', 'OVERVIEW'],
  research: ['研究对话', '提出研究问题，核对证据，再决定哪些参数进入计算。', 'RESEARCH'],
  processing: ['数据与方法', '追溯公开来源与网格指标的计算口径。', 'METHODS'],
  results: ['情景对照', '查看保留、新增和退出的候选网格。', 'RESULTS']
};

const questions = {
  senior: '优先考虑老年人前往基层诊所的公共交通可达性，哪些需求和供给指标值得调整？请列出文献、可复用的数据和权重理由，先生成提案。',
  weekend: '周末下午哪些地区客流相对于公交运力更紧张？需要哪些数据支撑？'
};

const labels = {
  baseline: '基线候选',
  grids: '研究网格',
  retained: '保留',
  entered: '新增',
  exited: '退出',
  neither: '未入选'
};

const layers = { areas: true, routes: true, network: true, grids: true };
let zoom = 1, changes = null, view = 'overview', example = 'senior';
let selectedCell = null, fullContext = false, pendingSection = null;
let researchProposed = false, researchSection = 'idea', weightReviewed = false, scenarioRunCompleted = false;

function pick(cell) {
  selectedCell = cell;
  const out = $('#picked');
  if (!out) return;
  delete out.dataset.i18n;
  out.hidden = !cell;
  if (cell) {
    const statusLabel = labels[cell.change] || (cell.candidate ? '基线候选' : '研究网格');
    out.textContent = [cell.area, cell.grid_id, t(statusLabel)].join(' · ');
  }
}

function notice(element, text) {
  if (!element) return;
  element.dataset.i18n = text;
  element.textContent = t(text);
}

function draw() {
  const comparison = view === 'results';
  const keys = comparison ? ['retained', 'entered', 'exited'] : ['baseline', 'grids'];
  const legend = $('#legend');
  if (legend) {
    legend.replaceChildren();
    for (const key of keys) {
      const swatch = document.createElement('i');
      swatch.style.background = 'var(--atlas-' + key + ')';
      legend.append(swatch, document.createTextNode(t(labels[key]) + ' '));
    }
  }
  const mode = $('#mapMode');
  if (mode) {
    mode.textContent = t(comparison ? (changes ? '情景对照' : '正在加载情景数据…') : '基线视图');
  }
  const context = $('#mapContext');
  if (context) {
    context.hidden = !comparison;
    context.textContent = t(fullContext ? '弱化线路与站点' : '显示完整线路与站点');
    context.setAttribute('aria-pressed', String(fullContext));
  }
  const canvas = $('#atlas');
  if (!canvas || !window.drawAtlas) return Promise.resolve();
  return window.drawAtlas(canvas, {
    layers,
    zoom,
    comparison: comparison && !fullContext,
    changes: comparison ? (changes || {}) : null,
    onPick: pick
  });
}

function drawSafely() {
  return draw().catch(() => {
    const out = $('#picked');
    if (out) {
      out.hidden = false;
      notice(out, '地图加载失败，请刷新重试。');
    }
  });
}

function selectPreset(name) {
  example = name;
  document.querySelectorAll('[data-preset]').forEach(b => {
    const isActive = b.dataset.preset === name;
    b.classList.toggle('active', isActive);
    b.setAttribute('aria-pressed', String(isActive));
  });
  const input = $('#questionInput');
  if (input) {
    input.value = t(questions[name] || '');
  }
  updateProposalVisibility();
}

function updateProposalVisibility() {
  document.querySelectorAll('[data-example]').forEach(el => {
    el.hidden = el.dataset.example !== example;
  });
  const seniorFlow = $('#seniorActionFlow');
  const weekendFlow = $('#weekendActionFlow');
  if (seniorFlow) seniorFlow.hidden = example !== 'senior';
  if (weekendFlow) weekendFlow.hidden = example !== 'weekend';
}

function setProposalSection(section) {
  researchSection = section;
  document.querySelectorAll('[data-section]').forEach(b => {
    b.setAttribute('aria-pressed', String(b.dataset.section === section));
  });
  document.querySelectorAll('[data-panel]').forEach(panel => {
    panel.hidden = panel.dataset.panel !== section;
  });
}

function headings() {
  const [title, subtitle, crumb] = pages[view] || pages.overview;
  const h1 = $('#title');
  const sub = $('#subtitle');
  const cr = $('#crumb');
  if (h1) h1.innerHTML = t(title) + '<span>.</span>';
  if (sub) sub.textContent = t(subtitle);
  if (cr) cr.textContent = crumb;
}

function bindResearchView() {
  const input = $('#questionInput');
  if (input) {
    input.value = t(questions[example] || '');
  }
  document.querySelectorAll('[data-preset]').forEach(b => {
    b.classList.toggle('active', b.dataset.preset === example);
    b.setAttribute('aria-pressed', String(b.dataset.preset === example));
    b.onclick = () => selectPreset(b.dataset.preset);
  });

  const form = $('#askForm');
  const statusBox = $('#dialogueStatus');
  const proposal = $('#proposalContainer');
  const statusText = $('#dialogueStatusText');

  if (form) {
    form.onsubmit = e => {
      e.preventDefault();
      if (statusBox) statusBox.hidden = false;
      const btn = $('#btnSubmitQuestion');
      if (btn) btn.disabled = true;

      setTimeout(() => {
        if (statusBox) statusBox.hidden = true;
        if (btn) btn.disabled = false;
        researchProposed = true;
        if (proposal) proposal.hidden = false;
        setProposalSection('idea');
        updateProposalVisibility();
        window.I18n.apply(proposal);
      }, 900);
    };
  }

  const btnReset = $('#btnResetQuestion');
  if (btnReset) {
    btnReset.onclick = () => {
      researchProposed = false;
      weightReviewed = false;
      scenarioRunCompleted = false;
      if (proposal) proposal.hidden = true;
      const step1 = $('#stepReviewWeights');
      const step2 = $('#stepWeightInputs');
      const step3 = $('#stepRunProgress');
      const step4 = $('#stepRunSuccess');
      if (step1) step1.hidden = false;
      if (step2) step2.hidden = true;
      if (step3) step3.hidden = true;
      if (step4) step4.hidden = true;
    };
  }

  document.querySelectorAll('[data-section]').forEach(b => {
    b.onclick = () => setProposalSection(b.dataset.section);
  });

  const btnReview = $('#btnGoWeightReview');
  const stepReview = $('#stepReviewWeights');
  const stepInputs = $('#stepWeightInputs');
  if (btnReview) {
    btnReview.onclick = () => {
      if (stepReview) stepReview.hidden = true;
      if (stepInputs) {
        stepInputs.hidden = false;
        window.I18n.apply(stepInputs);
      }
    };
  }

  const btnApprove = $('#btnApproveRun');
  const stepProgress = $('#stepRunProgress');
  const stepSuccess = $('#stepRunSuccess');
  if (btnApprove) {
    btnApprove.onclick = () => {
      if (stepInputs) stepInputs.hidden = true;
      if (stepProgress) stepProgress.hidden = false;
      setTimeout(() => {
        if (stepProgress) stepProgress.hidden = true;
        if (stepSuccess) {
          stepSuccess.hidden = false;
          window.I18n.apply(stepSuccess);
        }
        scenarioRunCompleted = true;
      }, 850);
    };
  }

  const btnGoResults = $('#btnViewResultSenior');
  if (btnGoResults) {
    btnGoResults.onclick = () => {
      location.hash = 'results';
    };
  }

  if (researchProposed && proposal) {
    proposal.hidden = false;
    setProposalSection(researchSection);
    updateProposalVisibility();
  }
}

function bindHelpModal() {
  const modal = $('#helpModal');
  const openBtn = $('#openHelp');
  const closeBtn = $('#closeHelp');
  if (!modal) return;
  if (openBtn) {
    openBtn.onclick = () => {
      modal.showModal();
      window.I18n.apply(modal);
    };
  }
  if (closeBtn) {
    closeBtn.onclick = () => modal.close();
  }
  modal.addEventListener('click', e => {
    if (e.target === modal) modal.close();
  });
}

function render() {
  const hash = location.hash.slice(1);
  view = Object.hasOwn(pages, hash) ? hash : 'overview';
  headings();

  const panelTpl = $('#panel-' + view);
  if (panelTpl) {
    $('#side').replaceChildren(panelTpl.content.cloneNode(true));
  }
  const notes = $('#notes-' + view);
  $('#lower').replaceChildren(...(notes ? [notes.content.cloneNode(true)] : []));

  window.I18n.apply($('#lower'));
  window.I18n.apply($('#side'));
  pick(null);

  document.querySelectorAll('[data-view]').forEach(b => {
    const isActive = b.dataset.view === view;
    b.classList.toggle('active', isActive);
    b.setAttribute('aria-current', isActive ? 'page' : 'false');
  });
  document.body.classList.toggle('research-mode', view === 'research');
  document.body.dataset.view = view;

  if (view === 'research') {
    bindResearchView();
  }

  drawSafely();

  if (pendingSection) {
    const section = pendingSection;
    pendingSection = null;
    requestAnimationFrame(() => showSection(section));
  }
}

function showSection(id) {
  const section = document.getElementById(id);
  if (section) {
    if (section.tagName === 'DETAILS') section.open = true;
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    section.focus({ preventScroll: true });
  }
}

document.addEventListener('click', event => {
  const b = event.target.closest('button');
  if (!b) return;
  if (b.dataset.methodSection) {
    if (view === 'processing') showSection(b.dataset.methodSection);
    else {
      pendingSection = b.dataset.methodSection;
      location.hash = 'processing';
    }
    return;
  }
  if (b.dataset.view || b.dataset.open) {
    location.hash = b.dataset.view || b.dataset.open;
    return;
  }
  if (b.dataset.layer) {
    const key = b.dataset.layer;
    layers[key] = !layers[key];
    b.setAttribute('aria-pressed', String(layers[key]));
  } else if (b.id === 'mapContext') {
    fullContext = !fullContext;
  } else if (b.id === 'zoomin') {
    zoom = Math.min(5, zoom * 1.4);
  } else if (b.id === 'zoomout') {
    zoom = Math.max(1, zoom / 1.4);
  } else if (b.id === 'reset') {
    zoom = 1;
  } else {
    return;
  }
  drawSafely();
});

window.addEventListener('languagechange', () => {
  headings();
  pick(selectedCell);
  if (view === 'research') {
    const input = $('#questionInput');
    if (input) input.value = t(questions[example] || '');
  }
  drawSafely();
});

window.addEventListener('hashchange', render);

bindHelpModal();
render();

fetch('./changes.json')
  .then(r => {
    if (!r.ok) throw Error();
    return r.json();
  })
  .then(data => {
    changes = data;
    drawSafely();
  })
  .catch(() => {
    notice($('#side'), '研究数据加载失败，请刷新重试。');
  });
