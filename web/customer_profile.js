function toNumber(value) {
  const number = Number(value || 0);
  return Number.isFinite(number) ? number : 0;
}

function normalizeName(value, fallback) {
  const text = String(value || "").trim();
  return text || fallback;
}

function round2(value) {
  return Math.round(value * 100) / 100;
}

function summarizeGroup(rows, key, fallback) {
  const groups = new Map();
  rows.forEach((row) => {
    const name = normalizeName(row[key], fallback);
    const current = groups.get(name) || { name, rows: 0, quantity: 0, amount: 0, share: 0 };
    current.rows += 1;
    current.quantity += toNumber(row.quantity);
    current.amount += toNumber(row.amount);
    groups.set(name, current);
  });
  const totalAmount = rows.reduce((sum, row) => sum + toNumber(row.amount), 0);
  return Array.from(groups.values())
    .map((item) => ({
      ...item,
      quantity: round2(item.quantity),
      amount: round2(item.amount),
      share: totalAmount ? round2((item.amount / totalAmount) * 100) : 0,
    }))
    .sort((a, b) => b.amount - a.amount || b.quantity - a.quantity || b.rows - a.rows || a.name.localeCompare(b.name, "zh-CN"));
}

function buildCustomerProfile(rows = []) {
  const safeRows = Array.isArray(rows) ? rows : [];
  const total = safeRows.reduce(
    (summary, row) => ({
      rows: summary.rows + 1,
      quantity: summary.quantity + toNumber(row.quantity),
      amount: summary.amount + toNumber(row.amount),
    }),
    { rows: 0, quantity: 0, amount: 0 },
  );
  const categories = summarizeGroup(safeRows, "materialCategory", "其他");
  const models = summarizeGroup(safeRows, "model", "未填写型号");
  return {
    total: {
      rows: total.rows,
      quantity: round2(total.quantity),
      amount: round2(total.amount),
    },
    primaryCategory: categories[0] || null,
    primaryModel: models[0] || null,
    categories,
    models,
  };
}

if (typeof window !== "undefined") {
  window.buildCustomerProfile = buildCustomerProfile;
}

if (typeof module !== "undefined") {
  module.exports = { buildCustomerProfile };
}
