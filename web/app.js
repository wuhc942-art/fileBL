const els = {
  dateInput: document.querySelector("#dateInput"),
  dropZone: document.querySelector("#dropZone"),
  chooseBtn: document.querySelector("#chooseBtn"),
  clearBtn: document.querySelector("#clearBtn"),
  fileInput: document.querySelector("#fileInput"),
  fileCount: document.querySelector("#fileCount"),
  fileList: document.querySelector("#fileList"),
  statusPanel: document.querySelector("#statusPanel"),
  results: document.querySelector("#results"),
  resultTitle: document.querySelector("#resultTitle"),
  kpiRows: document.querySelector("#kpiRows"),
  kpiCustomers: document.querySelector("#kpiCustomers"),
  kpiQuantity: document.querySelector("#kpiQuantity"),
  kpiAmount: document.querySelector("#kpiAmount"),
  comparisonGrid: document.querySelector("#comparisonGrid"),
  businessAlertGrid: document.querySelector("#businessAlertGrid"),
  taxStructureChart: document.querySelector("#taxStructureChart"),
  companyStructureChart: document.querySelector("#companyStructureChart"),
  insightPanel: document.querySelector("#insightPanel"),
  insightList: document.querySelector("#insightList"),
  fileCheckPanel: document.querySelector("#fileCheckPanel"),
  fileCheckSummary: document.querySelector("#fileCheckSummary"),
  fileCheckList: document.querySelector("#fileCheckList"),
  customerChart: document.querySelector("#customerChart"),
  modelChart: document.querySelector("#modelChart"),
  sourceChart: document.querySelector("#sourceChart"),
  materialCategoryChart: document.querySelector("#materialCategoryChart"),
  customerTable: document.querySelector("#customerTable"),
  detailTable: document.querySelector("#detailTable"),
  customerSummaryCount: document.querySelector("#customerSummaryCount"),
  detailCount: document.querySelector("#detailCount"),
  anomalyPanel: document.querySelector("#anomalyPanel"),
  anomalySummary: document.querySelector("#anomalySummary"),
  anomalyChips: document.querySelector("#anomalyChips"),
  searchInput: document.querySelector("#searchInput"),
  onlyAnomalyInput: document.querySelector("#onlyAnomalyInput"),
  sortButtons: document.querySelectorAll(".sort-button"),
  customerDrawer: document.querySelector("#customerDrawer"),
  drawerTitle: document.querySelector("#drawerTitle"),
  drawerStats: document.querySelector("#drawerStats"),
  drawerHead: document.querySelector("#drawerHead"),
  drawerRows: document.querySelector("#drawerRows"),
  drawerCloseBtn: document.querySelector("#drawerCloseBtn"),
  dataDirBtn: document.querySelector("#dataDirBtn"),
  downloadPngBtn: document.querySelector("#downloadPngBtn"),
  saveReportBtn: document.querySelector("#saveReportBtn"),
  downloadCsvBtn: document.querySelector("#downloadCsvBtn"),
  downloadJsonBtn: document.querySelector("#downloadJsonBtn"),
  templateButtons: document.querySelectorAll(".template-button"),
  importCheckPanel: document.querySelector("#importCheckPanel"),
  importCheckSummary: document.querySelector("#importCheckSummary"),
  importSummaryCards: document.querySelector("#importSummaryCards"),
  importCheckList: document.querySelector("#importCheckList"),
  anomalyReviewList: document.querySelector("#anomalyReviewList"),
  ruleSummary: document.querySelector("#ruleSummary"),
  currentDataDir: document.querySelector("#currentDataDir"),
  welcomePanel: document.querySelector("#welcomePanel"),
  backupBtn: document.querySelector("#backupBtn"),
  restoreBtn: document.querySelector("#restoreBtn"),
  materialCatalogBtn: document.querySelector("#materialCatalogBtn"),
  customerLookupTopBtn: document.querySelector("#customerLookupTopBtn"),
  customerLookupPanel: document.querySelector("#customerLookupPanel"),
  lookupTabs: document.querySelectorAll("[data-lookup-tab]"),
  customerLookupPane: document.querySelector("#customerLookupPane"),
  modelLookupPane: document.querySelector("#modelLookupPane"),
  customerProfileInput: document.querySelector("#customerProfileInput"),
  customerProfileList: document.querySelector("#customerProfileList"),
  customerProfileBtn: document.querySelector("#customerProfileBtn"),
  customerProfileResult: document.querySelector("#customerProfileResult"),
  modelLookupInput: document.querySelector("#modelLookupInput"),
  modelLookupList: document.querySelector("#modelLookupList"),
  modelLookupBtn: document.querySelector("#modelLookupBtn"),
  modelLookupResult: document.querySelector("#modelLookupResult"),
  appVersion: document.querySelector("#appVersion"),
};

function setLookupMode(mode) {
  const isModel = mode === "model";
  els.lookupTabs.forEach((button) => {
    button.classList.toggle("active", button.dataset.lookupTab === mode);
  });
  els.customerLookupPane?.classList.toggle("active", !isModel);
  els.modelLookupPane?.classList.toggle("active", isModel);
  window.setTimeout(() => (isModel ? els.modelLookupInput : els.customerProfileInput)?.focus(), 80);
}

let selectedFiles = [];
let currentPayload = null;
let viewState = {
  query: "",
  onlyAnomaly: false,
  sortKey: "amount",
  sortDirection: "desc",
  template: "boss",
};

function todayIso() {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

function formatNumber(value) {
  return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(Number(value || 0));
}

function formatMoney(value) {
  return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(Number(value || 0));
}

function setStatus(kind, title, text) {
  els.statusPanel.className = `status-panel ${kind}`;
  els.statusPanel.innerHTML = `<strong>${escapeHtml(title)}</strong><span>${escapeHtml(text)}</span>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function updateFileList() {
  els.fileCount.textContent = selectedFiles.length;
  updateWelcomeVisibility(Boolean(currentPayload) || selectedFiles.length > 0);
  if (!selectedFiles.length) {
    els.fileList.innerHTML = `<li class="muted">还没有选择文件</li>`;
    return;
  }
  els.fileList.innerHTML = selectedFiles
    .map((file) => `<li title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</li>`)
    .join("");
}

function acceptFiles(files) {
  selectedFiles = Array.from(files).filter((file) => file.name.toLowerCase().endsWith(".xlsx"));
  updateFileList();
  if (!selectedFiles.length) {
    setStatus("error", "没有可用文件", "请上传 .xlsx 格式的发货统计表。");
    return;
  }
  summarize();
}

async function summarize() {
  if (!selectedFiles.length) return;
  const form = new FormData();
  selectedFiles.forEach((file) => form.append("files", file));
  setStatus("loading", "正在读取", "正在分析发货明细，请稍等。");
  setBusy(true);
  try {
    const response = await fetch(`/api/summarize?date=${encodeURIComponent(els.dateInput.value)}`, {
      method: "POST",
      body: form,
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "分析失败。");
    currentPayload = payload;
    updateWelcomeVisibility(true);
    render(payload);
    const importMessage = payload.importSummary?.message ? `${payload.importSummary.message} ` : "";
    setStatus("ready", "已生成", `${importMessage}当前日期找到 ${payload.kpis.rows} 笔发货记录，金额 ${formatMoney(payload.kpis.amount)}。`);
  } catch (error) {
    currentPayload = null;
    updateWelcomeVisibility(false);
    els.results.hidden = true;
    setStatus("error", "分析失败", error.message);
    if (error.message.includes("read-only") || error.message.includes("只读")) {
      loadHistorySummary();
    }
  } finally {
    setBusy(false);
  }
}

async function loadHistorySummary() {
  setStatus("loading", "正在读取历史库", "正在从本机历史库生成看板。");
  setBusy(true);
  try {
    const response = await fetch(`/api/history-summary?date=${encodeURIComponent(els.dateInput.value)}`);
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "读取历史库失败。");
    currentPayload = payload;
    render(payload);
    const totalRows = payload.history?.rows || 0;
    updateWelcomeVisibility(totalRows > 0);
    setStatus("ready", "已读取历史库", `历史库共 ${formatNumber(totalRows)} 条记录，当前日期 ${formatNumber(payload.kpis.rows)} 条。`);
  } catch (error) {
    currentPayload = null;
    updateWelcomeVisibility(false);
    els.results.hidden = true;
    setStatus("empty", "等待文件", "还没有可用历史数据。请在本地管理员模式下先上传 Excel。");
  } finally {
    setBusy(false);
  }
}

function setBusy(isBusy) {
  els.chooseBtn.disabled = isBusy;
  els.clearBtn.disabled = isBusy;
  els.dateInput.disabled = isBusy;
  els.dataDirBtn.disabled = isBusy;
  els.backupBtn.disabled = isBusy;
  els.restoreBtn.disabled = isBusy;
  els.materialCatalogBtn.disabled = isBusy;
}

function updateWelcomeVisibility(hasData) {
  if (!els.welcomePanel) return;
  els.welcomePanel.hidden = Boolean(hasData);
}

function render(payload) {
  els.results.hidden = false;
  if (payload.appVersion && els.appVersion) {
    els.appVersion.textContent = payload.appVersion;
  }
  els.resultTitle.textContent = `${payload.date} 发货汇总`;
  els.kpiRows.textContent = formatNumber(payload.kpis.rows);
  els.kpiCustomers.textContent = formatNumber(payload.kpis.customers);
  els.kpiQuantity.textContent = formatNumber(payload.kpis.quantity);
  els.kpiAmount.textContent = formatMoney(payload.kpis.amount);
  renderComparisons(payload.comparisons || {});
  renderBusinessAlerts(payload.businessAlerts || {});
  renderStructure(els.taxStructureChart, payload.amountStructure?.taxType || []);
  renderStructure(els.companyStructureChart, payload.amountStructure?.company || []);
  renderBars(els.customerChart, payload.charts.customers, "amount", "customer");
  renderBars(els.modelChart, payload.charts.models, "amount", "model");
  renderBars(els.sourceChart, payload.charts.sources, "amount");
  renderBars(els.materialCategoryChart, payload.charts.materialCategories || [], "amount");
  renderInsights(payload.insights || []);
  renderFileCheck(payload.fileCheck);
  renderImportChecks(payload.importChecks);
  renderImportSummary(payload.importSummary);
  renderAnomalies(payload.anomalies);
  renderRules();
  renderCustomerProfileOptions(payload);
  renderCustomerProfile();
  renderCustomerTable(payload.customers);
  renderDetailTable(getVisibleRows());
  applyTemplate(viewState.template);
}

function renderInsights(insights) {
  els.insightPanel.hidden = false;
  els.insightList.innerHTML = insights.length
    ? insights.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
    : `<li>暂无可用结论。</li>`;
}

function renderFileCheck(fileCheck) {
  if (!fileCheck) {
    els.fileCheckPanel.hidden = true;
    return;
  }
  els.fileCheckPanel.hidden = false;
  els.fileCheckPanel.classList.toggle("warning", fileCheck.status === "warning");
  els.fileCheckSummary.textContent = fileCheck.message;
  els.fileCheckList.innerHTML = (fileCheck.files || [])
    .map((file) => `<span class="file-badge">${escapeHtml(file)}</span>`)
    .join("");
}

function renderImportChecks(importChecks) {
  if (!importChecks) {
    els.importCheckPanel.hidden = true;
    return;
  }
  els.importCheckPanel.hidden = false;
  els.importCheckPanel.classList.toggle("warning", importChecks.status !== "ready");
  els.importCheckSummary.textContent = `${importChecks.files?.length || 0} 个文件，${importChecks.errorCount || 0} 个错误，${importChecks.warningCount || 0} 个提醒`;
  els.importCheckList.innerHTML = (importChecks.files || [])
    .map((item) => `
      <div class="import-check-item ${escapeHtml(item.status)}">
        <strong>${escapeHtml(item.file)}</strong>
        <span>${escapeHtml((item.messages || []).join("；"))}</span>
        <div class="sheet-checks">
          ${renderSheetCheck("发货历史记录", item.sheets?.["发货历史记录"])}
          ${renderSheetCheck("发货明细", item.sheets?.["发货明细"])}
        </div>
        <small>日期列：${item.hasDateColumn ? "已识别" : "未识别"} · 月份：${item.monthMatched ? "匹配" : "需核对"}</small>
      </div>
    `)
    .join("");
}

function renderSheetCheck(name, sheet) {
  const ok = sheet?.hasSheet && sheet?.hasDateColumn;
  const tone = ok ? "ok" : "warn";
  let status = "缺少工作表";
  if (sheet?.hasSheet && !sheet?.hasDateColumn) status = "缺少日期列";
  if (ok && !sheet?.monthMatched) status = "月份需核对";
  if (ok && sheet?.monthMatched) status = "检查通过";
  return `<span class="sheet-check ${tone}" title="${escapeHtml(sheet?.message || "")}">${escapeHtml(name)}：${status}</span>`;
}

function renderImportSummary(summary) {
  if (!els.importSummaryCards) return;
  if (!summary) {
    els.importSummaryCards.innerHTML = "";
    return;
  }
  const cards = [
    ["读取", summary.readRows],
    ["新增", summary.insertedRows],
    ["跳过重复", summary.skippedDuplicateRows],
    ["错误文件", summary.errorRows],
  ];
  els.importSummaryCards.innerHTML = cards
    .map(([label, value]) => `
      <div class="import-summary-card">
        <span>${label}</span>
        <strong>${formatNumber(value)}</strong>
      </div>
    `)
    .join("");
}

function renderComparisons(comparisons) {
  const blocks = [
    ["yesterday", "较昨天"],
    ["lastWeek", "较上周同日"],
    ["last7Average", "较近 7 天日均"],
    ["last30Average", "较近 30 天日均"],
  ];
  const metrics = [
    ["amount", "金额", formatMoney],
    ["quantity", "数量", formatNumber],
    ["customers", "客户数", formatNumber],
  ];
  const fallback = currentPayload?.kpis || {};
  els.comparisonGrid.innerHTML = blocks
    .map(([key, title]) => {
      const comparison = comparisons[key] || {};
      return `
        <article class="comparison-card">
          <h4>${title}</h4>
          ${metrics.map(([metric, label, formatter]) => renderComparisonMetric(label, comparison[metric], formatter, fallback[metric])).join("")}
        </article>
      `;
    })
    .join("");
}

function renderComparisonMetric(label, metric, formatter, fallbackCurrent = 0) {
  const view = window.buildComparisonMetricView(metric, fallbackCurrent);
  if (!view.hasData) {
    return `
      <div class="comparison-line muted-line">
        <span>${label}</span>
        <strong>无可比数据</strong>
      </div>
    `;
  }
  const delta = Number(view.delta || 0);
  const tone = delta > 0 ? "up" : delta < 0 ? "down" : "flat";
  const sign = delta > 0 ? "+" : "";
  return `
    <div class="comparison-line ${tone}">
      <span>${label}</span>
      <strong>${sign}${formatter(delta)}${view.percentText}</strong>
    </div>
  `;
}

function renderBusinessAlerts(alerts) {
  const highValue = alerts.highValueCustomers || [];
  const newCustomers = alerts.newCustomers || [];
  const silentCustomers = alerts.silentCustomers || [];
  const returningCustomers = alerts.returningCustomers || [];
  const atRiskCustomers = alerts.atRiskCustomers || [];
  const newEmptyText = alerts.historyMode
    ? "没有基于全量历史发现今日首次发货客户。"
    : "没有发现相对昨天/上周新增的客户。";
  const silentEmptyText = alerts.historyMode
    ? "没有基于近 30 天历史发现今日未发的客户。"
    : "没有发现昨天/上周发货而今天未发的客户。";
  els.businessAlertGrid.innerHTML = `
    <article class="business-card">
      <h4>大客户提醒</h4>
      ${highValue.length ? highValue.slice(0, 5).map((row) => `
        <button class="alert-row" type="button" data-customer="${escapeHtml(row.customer)}">
          <span>${escapeHtml(row.customer)}</span><strong>${formatMoney(row.amount)}</strong>
        </button>
      `).join("") : `<p class="empty-chart">暂无超过 ${formatMoney(alerts.highValueThreshold || 100000)} 的客户。</p>`}
    </article>
    <article class="business-card">
      <h4>新客户</h4>
      ${newCustomers.length ? newCustomers.slice(0, 8).map((name) => `
        <button class="tag-button" type="button" data-customer="${escapeHtml(name)}">${escapeHtml(name)}</button>
      `).join("") : `<p class="empty-chart">${newEmptyText}</p>`}
    </article>
    <article class="business-card">
      <h4>沉默客户</h4>
      ${silentCustomers.length ? silentCustomers.slice(0, 8).map((name) => `
        <span class="tag-muted">${escapeHtml(name)}</span>
      `).join("") : `<p class="empty-chart">${silentEmptyText}</p>`}
    </article>
    <article class="business-card">
      <h4>回流客户</h4>
      ${returningCustomers.length ? returningCustomers.slice(0, 8).map((name) => `
        <button class="tag-button" type="button" data-customer="${escapeHtml(name)}">${escapeHtml(name)}</button>
      `).join("") : `<p class="empty-chart">没有发现沉默后今日重新发货的客户。</p>`}
    </article>
    <article class="business-card">
      <h4>流失风险</h4>
      ${atRiskCustomers.length ? atRiskCustomers.slice(0, 8).map((name) => `
        <span class="tag-muted">${escapeHtml(name)}</span>
      `).join("") : `<p class="empty-chart">没有发现超过 14 天未发货的历史客户。</p>`}
    </article>
  `;
}

function renderCustomerProfileOptions(payload) {
  if (!els.customerProfileList) return;
  const names = Array.from(new Set([
    ...(payload.customers || []).map((row) => row.customer).filter(Boolean),
    ...Object.keys(payload.customerHistoryProfiles || {}),
    ...Object.keys(payload.customerHistoryDetails || {}),
  ]));
  els.customerProfileList.innerHTML = names
    .map((name) => `<option value="${escapeHtml(name)}"></option>`)
    .join("");
  const modelMap = new Map();
  [
    ...(payload.rows || []).map((row) => row.model).filter(Boolean),
    ...Object.keys(payload.modelHistoryProfiles || {}),
  ].forEach((name) => {
    const key = String(name).trim().toLowerCase();
    if (key && !modelMap.has(key)) modelMap.set(key, String(name).trim());
  });
  const models = Array.from(modelMap.values());
  if (els.modelLookupList) {
    els.modelLookupList.innerHTML = models
      .map((name) => `<option value="${escapeHtml(name)}"></option>`)
      .join("");
  }
}

function findCustomerName(query) {
  if (!currentPayload) return "";
  const text = String(query || "").trim().toLowerCase();
  if (!text) return "";
  const names = Object.keys(currentPayload.customerHistoryProfiles || currentPayload.customerHistoryDetails || currentPayload.customerDetails || {});
  return (
    names.find((name) => name.toLowerCase() === text) ||
    names.find((name) => name.toLowerCase().includes(text)) ||
    ""
  );
}

function findModelName(query) {
  if (!currentPayload) return "";
  const text = String(query || "").trim().toLowerCase();
  if (!text) return "";
  const names = Object.keys(currentPayload.modelHistoryProfiles || {});
  return (
    names.find((name) => name.toLowerCase() === text) ||
    names.find((name) => name.toLowerCase().includes(text)) ||
    ""
  );
}

function customerProfileSummaryText(customer, profile) {
  const category = profile.primaryCategory?.name || "暂无";
  const categoryShare = profile.primaryCategory ? `${formatNumber(profile.primaryCategory.share)}%` : "0%";
  const model = profile.primaryModel?.name || "暂无";
  const modelShare = profile.primaryModel ? `${formatNumber(profile.primaryModel.share)}%` : "0%";
  return `${customer} 主发 ${category}，金额占比 ${categoryShare}；主发型号 ${model}，金额占比 ${modelShare}。`;
}

function renderProfileTopList(items, emptyText) {
  if (!items.length) return `<p class="empty-chart">${escapeHtml(emptyText)}</p>`;
  return `
    <div class="profile-list">
      ${items.slice(0, 6).map((item) => `
        <div class="profile-row" title="${escapeHtml(item.name)}">
          <span>${escapeHtml(item.name)}</span>
          <strong>${formatMoney(item.amount)}</strong>
          <em>${formatNumber(item.share)}%</em>
          <small>${formatNumber(item.quantity)} / ${formatNumber(item.rows)} 笔</small>
        </div>
      `).join("")}
    </div>
  `;
}

function renderCustomerProfile(customerName = "") {
  if (!els.customerProfileResult) return;
  if (!currentPayload) {
    els.customerProfileResult.innerHTML = `<p class="empty-chart">导入 Excel 或读取历史库后，可以查询客户材料画像。</p>`;
    return;
  }
  const query = customerName || els.customerProfileInput.value;
  const customer = findCustomerName(query);
  if (!customer) {
    els.customerProfileResult.innerHTML = `<p class="empty-chart">输入客户名称后，会自动总结主发大类和主发型号。</p>`;
    return;
  }
  const rows = currentPayload.customerHistoryDetails?.[customer] || currentPayload.customerDetails?.[customer] || [];
  const profile = currentPayload.customerHistoryProfiles?.[customer] || window.buildCustomerProfile(rows);
  els.customerProfileInput.value = customer;
  els.customerProfileResult.innerHTML = `
    <div class="profile-summary">
      <article>
        <span>客户</span>
        <strong>${escapeHtml(customer)}</strong>
      </article>
      <article>
        <span>主发大类</span>
        <strong>${escapeHtml(profile.primaryCategory?.name || "暂无")}</strong>
        <em>${profile.primaryCategory ? `${formatNumber(profile.primaryCategory.share)}% · ${formatMoney(profile.primaryCategory.amount)}` : "无金额"}</em>
      </article>
      <article>
        <span>主发型号</span>
        <strong>${escapeHtml(profile.primaryModel?.name || "暂无")}</strong>
        <em>${profile.primaryModel ? `${formatNumber(profile.primaryModel.share)}% · ${formatMoney(profile.primaryModel.amount)}` : "无金额"}</em>
      </article>
      <article>
        <span>合计</span>
        <strong>${formatMoney(profile.total.amount)}</strong>
        <em>${formatNumber(profile.total.quantity)} / ${formatNumber(profile.total.rows)} 笔</em>
      </article>
    </div>
    <p class="profile-conclusion">${escapeHtml(`${customerProfileSummaryText(customer, profile)} 统计口径：历史至今。`)}</p>
    <div class="profile-breakdowns">
      <section>
        <h4>材料大类</h4>
        ${renderProfileTopList(profile.categories, "暂无材料大类数据。")}
      </section>
      <section>
        <h4>常发型号</h4>
        ${renderProfileTopList(profile.models, "暂无型号数据。")}
      </section>
    </div>
  `;
}

function modelLookupSummaryText(model, profile) {
  const customer = profile.primaryCustomer?.name || "暂无";
  const customerShare = profile.primaryCustomer ? `${formatNumber(profile.primaryCustomer.share)}%` : "0%";
  const category = profile.primaryCategory?.name || "暂无";
  const categoryShare = profile.primaryCategory ? `${formatNumber(profile.primaryCategory.share)}%` : "0%";
  return `${model} 主要发给 ${customer}，金额占比 ${customerShare}；主材料大类 ${category}，金额占比 ${categoryShare}。`;
}

function renderModelLookup(modelName = "") {
  if (!els.modelLookupResult) return;
  if (!currentPayload) {
    els.modelLookupResult.innerHTML = `<p class="empty-chart">导入 Excel 或读取历史库后，可以按型号反查客户。</p>`;
    return;
  }
  const query = modelName || els.modelLookupInput.value;
  const model = findModelName(query);
  if (!model) {
    els.modelLookupResult.innerHTML = `<p class="empty-chart">输入型号后，会自动反查历史至今哪些客户发过。</p>`;
    return;
  }
  const profile = currentPayload.modelHistoryProfiles?.[model];
  els.modelLookupInput.value = model;
  els.modelLookupResult.innerHTML = `
    <div class="profile-summary">
      <article>
        <span>型号</span>
        <strong>${escapeHtml(model)}</strong>
      </article>
      <article>
        <span>主要客户</span>
        <strong>${escapeHtml(profile.primaryCustomer?.name || "暂无")}</strong>
        <em>${profile.primaryCustomer ? `${formatNumber(profile.primaryCustomer.share)}% · ${formatMoney(profile.primaryCustomer.amount)}` : "无金额"}</em>
      </article>
      <article>
        <span>材料大类</span>
        <strong>${escapeHtml(profile.primaryCategory?.name || "暂无")}</strong>
        <em>${profile.primaryCategory ? `${formatNumber(profile.primaryCategory.share)}% · ${formatMoney(profile.primaryCategory.amount)}` : "无金额"}</em>
      </article>
      <article>
        <span>合计</span>
        <strong>${formatMoney(profile.total.amount)}</strong>
        <em>${formatNumber(profile.total.quantity)} / ${formatNumber(profile.total.rows)} 笔</em>
      </article>
    </div>
    <p class="profile-conclusion">${escapeHtml(`${modelLookupSummaryText(model, profile)} 统计口径：历史至今。`)}</p>
    <div class="profile-breakdowns">
      <section>
        <h4>发货客户</h4>
        ${renderProfileTopList(profile.customers, "暂无客户数据。")}
      </section>
      <section>
        <h4>材料大类</h4>
        ${renderProfileTopList(profile.categories, "暂无材料大类数据。")}
      </section>
    </div>
  `;
}

function renderAnomalies(anomalies) {
  const labels = {
    missingCustomer: "空客户",
    missingModel: "空型号",
    zeroQuantity: "数量为 0",
    zeroAmount: "金额为 0",
    negativeAmount: "金额为负",
    negativeQuantity: "数量为负",
    missingDeliveryNo: "缺送货单号",
    missingPrice: "缺单价",
    duplicateShipment: "疑似重复",
  };
  if (!anomalies || !anomalies.total) {
    els.anomalyPanel.hidden = false;
    els.anomalySummary.textContent = "未发现异常";
    els.anomalyChips.innerHTML = `<div class="anomaly-chip"><strong>0</strong><span>需要人工核对的记录</span></div>`;
    els.anomalyReviewList.innerHTML = "";
    return;
  }
  els.anomalyPanel.hidden = false;
  els.anomalySummary.textContent = `${anomalies.total} 个提醒`;
  els.anomalyChips.innerHTML = Object.entries(labels)
    .map(([key, label]) => {
      const count = anomalies.counts?.[key] || 0;
      return `<button class="anomaly-chip" type="button" data-anomaly="${key}"><strong>${formatNumber(count)}</strong><span>${label}</span></button>`;
    })
    .join("");
  els.anomalyReviewList.innerHTML = `
    <div class="mini-table">
      ${(anomalies.items || []).slice(0, 30).map((item) => `
        <button class="review-row" type="button" data-anomaly-row="${item.rowIndex}">
          <span>${escapeHtml(item.customer || "未填写客户")}</span>
          <span>${escapeHtml(item.model || "未填写型号")}</span>
          <strong>${formatMoney(item.amount)}</strong>
          <em>${escapeHtml((item.labels || []).join("、"))}</em>
        </button>
      `).join("")}
    </div>
  `;
}

function renderRules() {
  els.ruleSummary.innerHTML = `
    <span>已内置：纯胶膜、覆盖膜、保护膜、离型膜可使用规格作为产品名称。</span>
    <span>材料大类可在 <code>shipment_config.json</code> 的 material_categories 中维护关键词。</span>
    <span>客户/型号别名可在 <code>shipment_config.json</code> 的 aliases 中维护。</span>
  `;
}

function applyTemplate(template) {
  viewState.template = template || "boss";
  els.templateButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.template === viewState.template);
  });
  els.results.dataset.template = viewState.template;
}

function renderStructure(container, rows) {
  renderBars(container, rows, "amount");
}

function renderBars(container, rows, field, kind = "") {
  if (!rows.length) {
    container.innerHTML = `<p class="empty-chart">当前日期没有发货记录。</p>`;
    return;
  }
  const max = Math.max(...rows.map((row) => Number(row[field] || 0)), 1);
  container.innerHTML = rows
    .map((row) => {
      const width = Math.max(2, (Number(row[field] || 0) / max) * 100);
      const name = escapeHtml(row.name);
      const nameNode = kind
        ? `<button class="bar-name bar-link" type="button" data-${kind}="${name}" title="${name}">${name}</button>`
        : `<div class="bar-name" title="${name}">${name}</div>`;
      return `
        <div class="bar-row">
          ${nameNode}
          <div class="bar-track" aria-hidden="true"><div class="bar-fill" style="width:${width}%"></div></div>
          <div class="bar-value">${formatMoney(row[field])}${row.share !== undefined ? ` · ${formatNumber(row.share)}%` : ""}</div>
        </div>
      `;
    })
    .join("");
}

function renderCustomerTable(rows) {
  els.customerSummaryCount.textContent = `${rows.length} 个客户`;
  els.customerTable.innerHTML = rows
    .map(
      (row) => `
        <tr>
          <td><button class="customer-link" type="button" data-customer="${escapeHtml(row.customer)}">${escapeHtml(row.customer)}</button></td>
          <td>${renderCategoryPill(row.primaryMaterialCategory)}</td>
          <td>${renderCategoryBreakdown(row.materialCategories || [])}</td>
          <td class="num">${formatNumber(row.rows)}</td>
          <td class="num">${formatNumber(row.quantity)}</td>
          <td class="num">${formatMoney(row.amount)}</td>
        </tr>
      `,
    )
    .join("");
}

function renderDetailTable(rows) {
  els.detailCount.textContent = `${rows.length} 笔明细`;
  els.detailTable.innerHTML = rows
    .map(
      (row) => `
        <tr>
          <td>${escapeHtml(row.customer)}</td>
          <td>${escapeHtml(row.model)}</td>
          <td>${renderCategoryPill(row.materialCategory)}</td>
          <td>${escapeHtml(row.spec)}</td>
          <td>${escapeHtml(row.unit)}</td>
          <td class="num">${formatNumber(row.quantity)}</td>
          <td class="num">${formatMoney(row.price)}</td>
          <td class="num">${formatMoney(row.amount)}</td>
          <td>${escapeHtml(row.deliveryNo)}</td>
          <td>${escapeHtml(row.orderNo)}</td>
          <td>${escapeHtml(row.source)}</td>
          <td>${renderFlags(row.anomalies)}</td>
        </tr>
      `,
    )
    .join("");
}

function renderFlags(flags = []) {
  const labels = {
    zeroAmount: "金额 0",
    negativeQuantity: "负数量",
    missingDeliveryNo: "缺单号",
    missingPrice: "缺单价",
  };
  if (!flags.length) return "";
  return `<div class="flag-list">${flags.map((flag) => `<span class="flag">${labels[flag] || flag}</span>`).join("")}</div>`;
}

function renderCategoryPill(category) {
  return `<span class="category-pill">${escapeHtml(category || "其他")}</span>`;
}

function renderCategoryBreakdown(categories = []) {
  if (!categories.length) return `<span class="muted-inline">-</span>`;
  return `
    <div class="category-list">
      ${categories.slice(0, 4).map((item) => `
        <span class="category-chip" title="${escapeHtml(item.name)}：${formatMoney(item.amount)}">
          ${escapeHtml(item.name)} ${formatNumber(item.share)}%
        </span>
      `).join("")}
    </div>
  `;
}

function getVisibleRows() {
  if (!currentPayload) return [];
  const query = viewState.query.trim().toLowerCase();
  const rows = currentPayload.rows.filter((row) => {
    if (viewState.onlyAnomaly && !(row.anomalies || []).length) return false;
    if (!query) return true;
    return [row.customer, row.model, row.materialCategory, row.spec, row.deliveryNo, row.orderNo, row.source]
      .some((value) => String(value || "").toLowerCase().includes(query));
  });
  const direction = viewState.sortDirection === "asc" ? 1 : -1;
  return rows.sort((a, b) => {
    const av = a[viewState.sortKey];
    const bv = b[viewState.sortKey];
    if (typeof av === "number" || typeof bv === "number") return (Number(av || 0) - Number(bv || 0)) * direction;
    return String(av || "").localeCompare(String(bv || ""), "zh-CN") * direction;
  });
}

function updateSortButtons() {
  els.sortButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.sort === viewState.sortKey);
    button.classList.toggle("asc", button.dataset.sort === viewState.sortKey && viewState.sortDirection === "asc");
    button.classList.toggle("desc", button.dataset.sort === viewState.sortKey && viewState.sortDirection === "desc");
  });
}

function openCustomerDrawer(customer) {
  if (!currentPayload) return;
  const rows = currentPayload.customerDetails?.[customer] || [];
  renderCustomerProfile(customer);
  const totalQuantity = rows.reduce((sum, row) => sum + Number(row.quantity || 0), 0);
  const totalAmount = rows.reduce((sum, row) => sum + Number(row.amount || 0), 0);
  els.drawerTitle.textContent = customer;
  els.drawerHead.innerHTML = `
    <tr>
      <th>型号/品名</th>
      <th>材料大类</th>
      <th>规格</th>
      <th>数量</th>
      <th>金额</th>
      <th>送货单号</th>
    </tr>
  `;
  els.drawerStats.innerHTML = `
    <div class="drawer-stat"><span>发货笔数</span><strong>${formatNumber(rows.length)}</strong></div>
    <div class="drawer-stat"><span>数量</span><strong>${formatNumber(totalQuantity)}</strong></div>
    <div class="drawer-stat"><span>金额</span><strong>${formatMoney(totalAmount)}</strong></div>
  `;
  els.drawerRows.innerHTML = rows
    .map(
      (row) => `
        <tr>
          <td>${escapeHtml(row.model)}</td>
          <td>${renderCategoryPill(row.materialCategory)}</td>
          <td>${escapeHtml(row.spec)}</td>
          <td class="num">${formatNumber(row.quantity)}</td>
          <td class="num">${formatMoney(row.amount)}</td>
          <td>${escapeHtml(row.deliveryNo)}</td>
        </tr>
      `,
    )
    .join("");
  els.customerDrawer.hidden = false;
}

function openModelDrawer(model) {
  if (!currentPayload) return;
  const rows = currentPayload.modelDetails?.[model] || [];
  const totalRows = rows.reduce((sum, row) => sum + Number(row.rows || 0), 0);
  const totalQuantity = rows.reduce((sum, row) => sum + Number(row.quantity || 0), 0);
  const totalAmount = rows.reduce((sum, row) => sum + Number(row.amount || 0), 0);
  els.drawerTitle.textContent = model;
  els.drawerHead.innerHTML = `
    <tr>
      <th>客户</th>
      <th>笔数</th>
      <th>数量</th>
      <th>金额</th>
      <th>占比</th>
    </tr>
  `;
  els.drawerStats.innerHTML = `
    <div class="drawer-stat"><span>客户数</span><strong>${formatNumber(rows.length)}</strong></div>
    <div class="drawer-stat"><span>数量</span><strong>${formatNumber(totalQuantity)}</strong></div>
    <div class="drawer-stat"><span>金额</span><strong>${formatMoney(totalAmount)}</strong></div>
  `;
  els.drawerRows.innerHTML = rows
    .map((row) => {
      const share = totalAmount ? (Number(row.amount || 0) / totalAmount) * 100 : 0;
      return `
        <tr>
          <td><button class="customer-link" type="button" data-customer="${escapeHtml(row.customer)}">${escapeHtml(row.customer)}</button></td>
          <td class="num">${formatNumber(row.rows)}</td>
          <td class="num">${formatNumber(row.quantity)}</td>
          <td class="num">${formatMoney(row.amount)}</td>
          <td class="num">${formatNumber(share)}%</td>
        </tr>
      `;
    })
    .join("");
  els.customerDrawer.hidden = false;
}

function closeCustomerDrawer() {
  els.customerDrawer.hidden = true;
}

function toCsv(rows) {
  const headers = ["客户", "型号/品名", "材料大类", "规格", "单位", "数量", "单价", "金额", "送货单号", "订单号", "来源文件", "备注"];
  const keys = ["customer", "model", "materialCategory", "spec", "unit", "quantity", "price", "amount", "deliveryNo", "orderNo", "source", "note"];
  const lines = [headers.join(",")];
  rows.forEach((row) => {
    lines.push(keys.map((key) => csvCell(row[key])).join(","));
  });
  return `\ufeff${lines.join("\n")}`;
}

function csvCell(value) {
  const text = String(value ?? "");
  if (/[",\n]/.test(text)) return `"${text.replaceAll('"', '""')}"`;
  return text;
}

function download(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

async function saveExportFile(filename, content, encoding = "text") {
  if (window.pywebview?.api?.save_export_file) {
    const result = await window.pywebview.api.save_export_file(filename, content, encoding);
    if (result?.cancelled) {
      setStatus("ready", "已取消导出", "没有保存文件。");
      return;
    }
    setStatus("ready", "导出已保存", result.path);
    return;
  }
  const response = await fetch("/api/export-file", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename, content, encoding }),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "导出失败");
  setStatus("ready", "导出已保存", result.path);
}

async function chooseDataDirectory() {
  if (!window.pywebview?.api?.choose_data_directory) {
    setStatus("ready", "数据目录", "浏览器模式下数据保存在软件目录。");
    return;
  }
  try {
    const result = await window.pywebview.api.choose_data_directory();
    if (result?.cancelled) {
      setStatus("ready", "已取消", "数据目录没有改变。");
      return;
    }
    setStatus("ready", "数据目录已切换", result.storageRoot || result.dataDir);
    await refreshSettings();
    selectedFiles = [];
    els.fileInput.value = "";
    updateFileList();
    loadHistorySummary();
  } catch (error) {
    setStatus("error", "切换数据目录失败", error.message);
  }
}

async function refreshSettings() {
  if (!window.pywebview?.api?.get_settings) {
    els.currentDataDir.textContent = "数据目录：浏览器模式下保存在软件目录";
    return;
  }
  try {
    const settings = await window.pywebview.api.get_settings();
    const dataDir = settings?.dataDir || "";
    const catalogText = settings?.materialCatalogRows
      ? ` · 材料类型 ${formatNumber(settings.materialCatalogRows)} 条`
      : " · 未选择材料类型表";
    els.currentDataDir.textContent = `数据目录：${dataDir}${catalogText}`;
    els.currentDataDir.title = dataDir || "当前数据保存位置";
  } catch (error) {
    els.currentDataDir.textContent = "数据目录：读取失败";
    els.currentDataDir.title = error.message;
  }
}

async function chooseMaterialCatalogFile() {
  if (!window.pywebview?.api?.choose_material_catalog_file) {
    setStatus("ready", "材料类型表仅桌面版可用", "请在桌面 App 中选择材料类型表。");
    return;
  }
  try {
    const result = await window.pywebview.api.choose_material_catalog_file();
    if (result?.cancelled) {
      setStatus("ready", "已取消", "材料类型表没有改变。");
      return;
    }
    setStatus("ready", "材料类型表已读取", `识别 ${formatNumber(result.materialCatalogRows || 0)} 条产品类型。`);
    await refreshSettings();
    loadHistorySummary();
  } catch (error) {
    setStatus("error", "读取材料类型表失败", error.message);
  }
}

async function createBackup() {
  if (!window.pywebview?.api?.create_backup_file) {
    setStatus("ready", "备份仅桌面版可用", "请在桌面 App 中使用备份功能。");
    return;
  }
  try {
    const result = await window.pywebview.api.create_backup_file();
    if (result?.cancelled) {
      setStatus("ready", "已取消备份", "没有保存备份文件。");
      return;
    }
    setStatus("ready", "备份已保存", result.path);
  } catch (error) {
    setStatus("error", "备份失败", error.message);
  }
}

async function restoreBackup() {
  if (!window.pywebview?.api?.restore_backup_file) {
    setStatus("ready", "恢复仅桌面版可用", "请在桌面 App 中使用恢复功能。");
    return;
  }
  if (!confirm("恢复会覆盖当前数据目录里的历史数据库，确定继续吗？")) return;
  try {
    const result = await window.pywebview.api.restore_backup_file();
    if (result?.cancelled) {
      setStatus("ready", "已取消恢复", "历史数据没有改变。");
      return;
    }
    setStatus("ready", "恢复完成", result.historyDb);
    await refreshSettings();
    loadHistorySummary();
  } catch (error) {
    setStatus("error", "恢复失败", error.message);
  }
}

els.dateInput.value = todayIso();
updateFileList();

els.chooseBtn.addEventListener("click", () => els.fileInput.click());
els.fileInput.addEventListener("change", () => acceptFiles(els.fileInput.files));
els.clearBtn.addEventListener("click", () => {
  selectedFiles = [];
  currentPayload = null;
  els.fileInput.value = "";
  els.results.hidden = true;
  updateFileList();
  loadHistorySummary();
});
els.dateInput.addEventListener("change", () => {
  if (selectedFiles.length) {
    summarize();
  } else {
    loadHistorySummary();
  }
});

["dragenter", "dragover"].forEach((eventName) => {
  els.dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    els.dropZone.classList.add("dragging");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  els.dropZone.addEventListener(eventName, () => {
    els.dropZone.classList.remove("dragging");
  });
});

els.dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  acceptFiles(event.dataTransfer.files);
});

els.dropZone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    els.fileInput.click();
  }
});

els.dataDirBtn.addEventListener("click", () => {
  chooseDataDirectory();
});

els.materialCatalogBtn.addEventListener("click", () => {
  chooseMaterialCatalogFile();
});

els.customerLookupTopBtn.addEventListener("click", () => {
  setLookupMode("customer");
  els.customerLookupPanel?.scrollIntoView({ behavior: "smooth", block: "start" });
  window.setTimeout(() => els.customerProfileInput?.focus(), 250);
});

els.lookupTabs.forEach((button) => {
  button.addEventListener("click", () => setLookupMode(button.dataset.lookupTab));
});

els.backupBtn.addEventListener("click", () => {
  createBackup();
});

els.restoreBtn.addEventListener("click", () => {
  restoreBackup();
});

els.downloadCsvBtn.addEventListener("click", () => {
  if (!currentPayload) return;
  saveExportFile(`每日发货明细-${currentPayload.date}.csv`, toCsv(getVisibleRows())).catch((error) => {
    setStatus("error", "导出失败", error.message);
  });
});

els.downloadJsonBtn.addEventListener("click", () => {
  if (!currentPayload) return;
  saveExportFile(
    `每日发货看板-${currentPayload.date}.json`,
    JSON.stringify(currentPayload, null, 2),
  ).catch((error) => {
    setStatus("error", "导出失败", error.message);
  });
});

els.downloadPngBtn.addEventListener("click", () => {
  if (!currentPayload) return;
  exportPngReport(currentPayload);
});

els.saveReportBtn.addEventListener("click", async () => {
  if (!currentPayload) return;
  els.saveReportBtn.disabled = true;
  try {
    const response = await fetch("/api/save-report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentPayload),
    });
    const manifest = await response.json();
    if (!response.ok) throw new Error(manifest.error || "保存失败");
    setStatus("ready", "日报包已保存", manifest.directory);
  } catch (error) {
    setStatus("error", "保存日报包失败", error.message);
  } finally {
    els.saveReportBtn.disabled = false;
  }
});

els.templateButtons.forEach((button) => {
  button.addEventListener("click", () => {
    viewState.template = button.dataset.template;
    applyTemplate(viewState.template);
  });
});

els.searchInput.addEventListener("input", () => {
  viewState.query = els.searchInput.value;
  renderDetailTable(getVisibleRows());
});

els.onlyAnomalyInput.addEventListener("change", () => {
  viewState.onlyAnomaly = els.onlyAnomalyInput.checked;
  renderDetailTable(getVisibleRows());
});

els.sortButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const key = button.dataset.sort;
    if (viewState.sortKey === key) {
      viewState.sortDirection = viewState.sortDirection === "asc" ? "desc" : "asc";
    } else {
      viewState.sortKey = key;
      viewState.sortDirection = key === "customer" || key === "model" ? "asc" : "desc";
    }
    updateSortButtons();
    renderDetailTable(getVisibleRows());
  });
});

els.customerTable.addEventListener("click", (event) => {
  const button = event.target.closest("[data-customer]");
  if (button) openCustomerDrawer(button.dataset.customer);
});

els.customerChart.addEventListener("click", (event) => {
  const button = event.target.closest("[data-customer]");
  if (button) openCustomerDrawer(button.dataset.customer);
});

els.modelChart.addEventListener("click", (event) => {
  const button = event.target.closest("[data-model]");
  if (button) openModelDrawer(button.dataset.model);
});

els.businessAlertGrid.addEventListener("click", (event) => {
  const button = event.target.closest("[data-customer]");
  if (button) openCustomerDrawer(button.dataset.customer);
});

els.customerProfileBtn.addEventListener("click", () => {
  setLookupMode("customer");
  renderCustomerProfile();
});

els.customerProfileInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    setLookupMode("customer");
    renderCustomerProfile();
  }
});

els.customerProfileInput.addEventListener("change", () => {
  setLookupMode("customer");
  renderCustomerProfile();
});

els.modelLookupBtn.addEventListener("click", () => {
  setLookupMode("model");
  renderModelLookup();
});

els.modelLookupInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    setLookupMode("model");
    renderModelLookup();
  }
});

els.modelLookupInput.addEventListener("change", () => {
  setLookupMode("model");
  renderModelLookup();
});

els.drawerRows.addEventListener("click", (event) => {
  const button = event.target.closest("[data-customer]");
  if (button) openCustomerDrawer(button.dataset.customer);
});

els.anomalyChips.addEventListener("click", (event) => {
  const chip = event.target.closest("[data-anomaly]");
  if (!chip) return;
  els.onlyAnomalyInput.checked = true;
  viewState.onlyAnomaly = true;
  viewState.query = "";
  els.searchInput.value = "";
  renderDetailTable(getVisibleRows().filter((row) => (row.anomalies || []).includes(chip.dataset.anomaly)));
  els.detailCount.textContent = `${getVisibleRows().filter((row) => (row.anomalies || []).includes(chip.dataset.anomaly)).length} 笔明细`;
});

els.anomalyReviewList.addEventListener("click", (event) => {
  const rowButton = event.target.closest("[data-anomaly-row]");
  if (!rowButton || !currentPayload) return;
  const row = currentPayload.rows[Number(rowButton.dataset.anomalyRow)];
  if (!row) return;
  viewState.query = row.deliveryNo || row.customer || row.model || "";
  els.searchInput.value = viewState.query;
  renderDetailTable(getVisibleRows());
  document.querySelector(".detail-wrap")?.scrollIntoView({ behavior: "smooth", block: "start" });
});

els.drawerCloseBtn.addEventListener("click", closeCustomerDrawer);
els.customerDrawer.addEventListener("click", (event) => {
  if (event.target === els.customerDrawer) closeCustomerDrawer();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeCustomerDrawer();
});

function exportPngReport(payload) {
  const width = 1360;
  const height = 780;
  const topCustomers = payload.charts.customers.slice(0, 6);
  const topModels = payload.charts.models.slice(0, 6);
  const maxCustomer = Math.max(...topCustomers.map((row) => row.amount), 1);
  const maxModel = Math.max(...topModels.map((row) => row.amount), 1);
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
      <rect width="${width}" height="${height}" fill="#f4f7f8"/>
      <text x="48" y="62" fill="#172326" font-size="30" font-weight="700" font-family="Microsoft YaHei, Arial">每日发货看板</text>
      <text x="48" y="94" fill="#5f6f73" font-size="16" font-family="Microsoft YaHei, Arial">${payload.date} 生成</text>
      ${svgKpi(48, 132, "发货笔数", payload.kpis.rows)}
      ${svgKpi(324, 132, "客户数", payload.kpis.customers)}
      ${svgKpi(600, 132, "总数量", formatNumber(payload.kpis.quantity))}
      ${svgKpi(876, 132, "总金额", formatMoney(payload.kpis.amount))}
      ${svgBars(48, 270, 520, "客户金额排行", topCustomers, maxCustomer)}
      ${svgBars(632, 270, 520, "型号金额排行", topModels, maxModel)}
      <text x="48" y="704" fill="#172326" font-size="15" font-family="Microsoft YaHei, Arial">${escapeSvg((payload.insights || [])[0] || "")}</text>
      <text x="48" y="736" fill="#5f6f73" font-size="14" font-family="Microsoft YaHei, Arial">异常提醒：${payload.anomalies?.total || 0} 个  ·  来源文件：${payload.sources.join("、")}</text>
    </svg>
  `;
  const image = new Image();
  const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  image.onload = () => {
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    context.drawImage(image, 0, 0);
    URL.revokeObjectURL(url);
    canvas.toBlob((pngBlob) => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = String(reader.result || "").split(",", 2)[1] || "";
        saveExportFile(`每日发货日报-${payload.date}.png`, base64, "base64").catch((error) => {
          setStatus("error", "导出失败", error.message);
        });
      };
      reader.readAsDataURL(pngBlob);
    }, "image/png");
  };
  image.src = url;
}

function svgKpi(x, y, label, value) {
  return `
    <rect x="${x}" y="${y}" width="248" height="96" rx="8" fill="#ffffff" stroke="#d7e2e4"/>
    <text x="${x + 20}" y="${y + 34}" fill="#5f6f73" font-size="15" font-family="Microsoft YaHei, Arial">${label}</text>
    <text x="${x + 20}" y="${y + 72}" fill="#172326" font-size="30" font-weight="700" font-family="Microsoft YaHei, Arial">${value}</text>
  `;
}

function svgBars(x, y, width, title, rows, max, options = {}) {
  const panelWidth = x > 600 && width < 600 ? 600 : width;
  const isModelPanel = x > 600;
  const labelWidth = options.labelWidth ?? (isModelPanel ? 270 : 170);
  const labelUnits = options.labelUnits ?? (isModelPanel ? 24 : 16);
  const valueWidth = 96;
  const gap = 18;
  const trackX = x + labelWidth + gap;
  const trackWidth = Math.max(120, panelWidth - labelWidth - valueWidth - gap * 2);
  const valueX = x + panelWidth - 4;
  const rowSvg = rows
    .map((row, index) => {
      const yy = y + 56 + index * 54;
      const barWidth = Math.max(3, (row.amount / max) * trackWidth);
      const label = fitSvgLabel(row.name, labelUnits);
      return `
        <text x="${x}" y="${yy + 18}" fill="#172326" font-size="14" font-family="Microsoft YaHei, Arial">${escapeSvg(label)}</text>
        <rect x="${trackX}" y="${yy + 6}" width="${trackWidth}" height="12" rx="6" fill="#eef4f4"/>
        <rect x="${trackX}" y="${yy + 6}" width="${barWidth}" height="12" rx="6" fill="#087f8c"/>
        <text x="${valueX}" y="${yy + 18}" text-anchor="end" fill="#53676c" font-size="13" font-family="Microsoft YaHei, Arial">${formatMoney(row.amount)}</text>
      `;
    })
    .join("");
  return `
    <rect x="${x - 16}" y="${y}" width="${panelWidth + 32}" height="390" rx="8" fill="#ffffff" stroke="#d7e2e4"/>
    <text x="${x}" y="${y + 32}" fill="#172326" font-size="20" font-weight="700" font-family="Microsoft YaHei, Arial">${title}</text>
    ${rowSvg}
  `;
}

function fitSvgLabel(value, maxUnits) {
  const text = String(value ?? "");
  let units = 0;
  let output = "";
  for (const char of text) {
    const unit = (char.codePointAt(0) || 0) > 255 ? 2 : 1;
    if (units + unit > maxUnits) return `${output}...`;
    output += char;
    units += unit;
  }
  return output;
}

function escapeSvg(value) {
  return escapeHtml(value).replaceAll("'", "&apos;");
}

updateSortButtons();
refreshSettings();
loadHistorySummary();
