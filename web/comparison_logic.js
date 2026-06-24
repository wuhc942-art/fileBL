(function (global) {
  function buildComparisonMetricView(metric, fallbackCurrent) {
    if (!metric) {
      const fallback = Number(fallbackCurrent || 0);
      return {
        hasData: true,
        delta: fallback,
        percentText: "",
      };
    }
    const hasBaseline = Boolean(metric.hasBaseline);
    const delta = hasBaseline ? Number(metric.delta || 0) : Number(metric.current || fallbackCurrent || 0);
    const sign = delta > 0 ? "+" : "";
    const percentText = hasBaseline && metric.percent !== null && metric.percent !== undefined
      ? ` (${sign}${Number(metric.percent || 0).toLocaleString("zh-CN", { maximumFractionDigits: 2 })}%)`
      : "";
    return {
      hasData: true,
      delta,
      percentText,
    };
  }

  global.buildComparisonMetricView = buildComparisonMetricView;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { buildComparisonMetricView };
  }
})(typeof window !== "undefined" ? window : globalThis);
