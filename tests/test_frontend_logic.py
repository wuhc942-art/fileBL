import subprocess
import unittest


class FrontendLogicTest(unittest.TestCase):
    def test_missing_comparison_metric_uses_current_value_fallback(self):
        script = """
        const { buildComparisonMetricView } = require('./web/comparison_logic.js');
        const view = buildComparisonMetricView(undefined, 553108.52);
        if (!view.hasData) throw new Error('expected fallback data');
        if (view.delta !== 553108.52) throw new Error(`unexpected delta ${view.delta}`);
        if (view.percentText !== '') throw new Error(`unexpected percent ${view.percentText}`);
        """
        subprocess.run(["node", "-e", script], cwd=".", check=True)


if __name__ == "__main__":
    unittest.main()
