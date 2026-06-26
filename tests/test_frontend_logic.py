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

    def test_customer_profile_summarizes_primary_category_and_model(self):
        script = """
        const { buildCustomerProfile } = require('./web/customer_profile.js');
        const profile = buildCustomerProfile([
          { materialCategory: '覆盖膜', model: 'CVL-001', quantity: 10, amount: 1000 },
          { materialCategory: '覆盖膜', model: 'CVL-001', quantity: 5, amount: 500 },
          { materialCategory: '补强', model: 'FR4-100', quantity: 20, amount: 800 },
          { materialCategory: '', model: '', quantity: 2, amount: 20 },
        ]);
        if (profile.primaryCategory.name !== '覆盖膜') throw new Error(`unexpected category ${profile.primaryCategory.name}`);
        if (profile.primaryCategory.share !== 64.66) throw new Error(`unexpected category share ${profile.primaryCategory.share}`);
        if (profile.primaryModel.name !== 'CVL-001') throw new Error(`unexpected model ${profile.primaryModel.name}`);
        if (profile.primaryModel.rows !== 2) throw new Error(`unexpected model rows ${profile.primaryModel.rows}`);
        if (profile.total.rows !== 4) throw new Error(`unexpected total rows ${profile.total.rows}`);
        if (profile.models.length !== 3) throw new Error(`unexpected model count ${profile.models.length}`);
        """
        subprocess.run(["node", "-e", script], cwd=".", check=True)


if __name__ == "__main__":
    unittest.main()
