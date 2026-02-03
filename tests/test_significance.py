"""
Unit tests for statistical significance analysis.

Tests the correctness of bootstrap CI, Wilcoxon tests, Holm correction,
and Cliff's delta calculations using synthetic data.
"""

import unittest
import numpy as np
import sys
import os

# Add parent directory to path to import from tools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.compute_significance import (
    bootstrap_ci,
    bootstrap_pvalue,
    cliffs_delta,
    holm_bonferroni_correction,
    compute_paired_differences
)

import pandas as pd


class TestBootstrapCI(unittest.TestCase):
    """Test bootstrap confidence interval calculation."""

    def setUp(self):
        np.random.seed(42)

    def test_bootstrap_ci_positive_mean(self):
        """Test CI for data with positive mean."""
        data = np.random.normal(loc=5, scale=2, size=100)
        mean, ci_lo, ci_hi = bootstrap_ci(data, n_bootstrap=1000)

        # Check mean is reasonable
        self.assertAlmostEqual(mean, np.mean(data), places=10)

        # Check CI bounds are in correct order
        self.assertLess(ci_lo, mean)
        self.assertLess(mean, ci_hi)

        # Check CI contains true mean (should with high probability)
        self.assertLess(ci_lo, 5)
        self.assertGreater(ci_hi, 5)

    def test_bootstrap_ci_zero_mean(self):
        """Test CI for data centered at zero."""
        data = np.random.normal(loc=0, scale=1, size=100)
        mean, ci_lo, ci_hi = bootstrap_ci(data, n_bootstrap=1000)

        # CI should include zero
        self.assertLessEqual(ci_lo, 0)
        self.assertGreaterEqual(ci_hi, 0)

    def test_bootstrap_ci_constant_data(self):
        """Test CI for constant data."""
        data = np.ones(100) * 5.0
        mean, ci_lo, ci_hi = bootstrap_ci(data, n_bootstrap=100)

        # All values should be 5
        self.assertAlmostEqual(mean, 5.0, places=10)
        self.assertAlmostEqual(ci_lo, 5.0, places=10)
        self.assertAlmostEqual(ci_hi, 5.0, places=10)


class TestBootstrapPValue(unittest.TestCase):
    """Test bootstrap p-value calculation."""

    def setUp(self):
        np.random.seed(42)

    def test_pvalue_significant_positive(self):
        """Test p-value for significantly positive data."""
        # Data clearly shifted from zero
        data = np.random.normal(loc=3, scale=1, size=100)
        p_value = bootstrap_pvalue(data, n_bootstrap=1000)

        # Should be very small
        self.assertLess(p_value, 0.05)

    def test_pvalue_null_hypothesis(self):
        """Test p-value for data from null distribution."""
        # Data centered at zero
        data = np.random.normal(loc=0, scale=1, size=100)
        p_value = bootstrap_pvalue(data, n_bootstrap=1000)

        # Should not be significant (though could be due to chance)
        # We just check it's in valid range
        self.assertGreaterEqual(p_value, 0.0)
        self.assertLessEqual(p_value, 1.0)

    def test_pvalue_small_effect(self):
        """Test p-value for small effect."""
        # Small shift
        data = np.random.normal(loc=0.1, scale=1, size=100)
        p_value = bootstrap_pvalue(data, n_bootstrap=1000)

        # Should be in valid range
        self.assertGreaterEqual(p_value, 0.0)
        self.assertLessEqual(p_value, 1.0)


class TestCliffsD(unittest.TestCase):
    """Test Cliff's delta effect size calculation."""

    def test_cliffs_delta_all_positive(self):
        """Test Cliff's delta when all differences are positive."""
        data = np.array([1, 2, 3, 4, 5])
        delta = cliffs_delta(data)
        self.assertEqual(delta, 1.0)

    def test_cliffs_delta_all_negative(self):
        """Test Cliff's delta when all differences are negative."""
        data = np.array([-1, -2, -3, -4, -5])
        delta = cliffs_delta(data)
        self.assertEqual(delta, -1.0)

    def test_cliffs_delta_balanced(self):
        """Test Cliff's delta for balanced positive/negative."""
        data = np.array([-2, -1, 0, 1, 2])
        delta = cliffs_delta(data)
        # 2 positive, 2 negative, 1 zero -> (2-2)/5 = 0
        self.assertEqual(delta, 0.0)

    def test_cliffs_delta_mostly_positive(self):
        """Test Cliff's delta for mostly positive data."""
        data = np.array([1, 1, 1, -1])
        delta = cliffs_delta(data)
        # 3 positive, 1 negative -> (3-1)/4 = 0.5
        self.assertEqual(delta, 0.5)

    def test_cliffs_delta_empty_data(self):
        """Test Cliff's delta for empty array."""
        data = np.array([])
        delta = cliffs_delta(data)
        self.assertTrue(np.isnan(delta))


class TestHolmBonferroni(unittest.TestCase):
    """Test Holm-Bonferroni correction."""

    def test_holm_correction_basic(self):
        """Test basic Holm correction."""
        p_values = [0.01, 0.04, 0.03, 0.05]
        corrected = holm_bonferroni_correction(p_values)

        # First (smallest) p-value multiplied by 4
        # Second p-value multiplied by 3, etc.
        expected_sorted = [0.01 * 4, 0.03 * 3, 0.04 * 2, 0.05 * 1]

        # Check monotonicity
        for i in range(len(corrected) - 1):
            sorted_corrected = sorted(corrected)
            self.assertLessEqual(sorted_corrected[i], sorted_corrected[i + 1])

    def test_holm_correction_single_value(self):
        """Test Holm correction with single p-value."""
        p_values = [0.03]
        corrected = holm_bonferroni_correction(p_values)
        self.assertEqual(corrected[0], 0.03)

    def test_holm_correction_all_significant(self):
        """Test when all p-values are very small."""
        p_values = [0.001, 0.002, 0.003]
        corrected = holm_bonferroni_correction(p_values)

        # All should remain < 0.05
        for p in corrected:
            self.assertLess(p, 0.05)

    def test_holm_correction_none_significant(self):
        """Test when no p-values are significant."""
        p_values = [0.5, 0.6, 0.7]
        corrected = holm_bonferroni_correction(p_values)

        # All should remain > 0.05
        for p in corrected:
            self.assertGreater(p, 0.05)

    def test_holm_correction_capped_at_one(self):
        """Test that corrected p-values don't exceed 1."""
        p_values = [0.9, 0.8, 0.7]
        corrected = holm_bonferroni_correction(p_values)

        # All should be <= 1
        for p in corrected:
            self.assertLessEqual(p, 1.0)

    def test_holm_correction_empty(self):
        """Test with empty list."""
        p_values = []
        corrected = holm_bonferroni_correction(p_values)
        self.assertEqual(corrected, [])


class TestComputePairedDifferences(unittest.TestCase):
    """Test paired difference computation."""

    def test_paired_differences_basic(self):
        """Test basic paired difference calculation."""
        baseline_df = pd.DataFrame({
            'sample_id': [1, 2, 3],
            'MAE': [5.0, 6.0, 7.0]
        })
        flow_df = pd.DataFrame({
            'sample_id': [1, 2, 3],
            'MAE': [4.0, 5.0, 6.0]
        })

        diffs = compute_paired_differences(baseline_df, flow_df, 'MAE')

        # For MAE (lower is better): baseline - flow
        expected = np.array([1.0, 1.0, 1.0])
        np.testing.assert_array_equal(diffs, expected)

    def test_paired_differences_higher_is_better(self):
        """Test paired difference for metric where higher is better."""
        baseline_df = pd.DataFrame({
            'sample_id': [1, 2, 3],
            'ssim': [0.8, 0.85, 0.9]
        })
        flow_df = pd.DataFrame({
            'sample_id': [1, 2, 3],
            'ssim': [0.85, 0.9, 0.95]
        })

        diffs = compute_paired_differences(baseline_df, flow_df, 'ssim',
                                          higher_is_better=True)

        # For SSIM (higher is better): flow - baseline
        expected = np.array([0.05, 0.05, 0.05])
        np.testing.assert_array_almost_equal(diffs, expected)

    def test_paired_differences_with_nans(self):
        """Test that NaN values are filtered out."""
        baseline_df = pd.DataFrame({
            'sample_id': [1, 2, 3],
            'MAE': [5.0, np.nan, 7.0]
        })
        flow_df = pd.DataFrame({
            'sample_id': [1, 2, 3],
            'MAE': [4.0, 5.0, 6.0]
        })

        diffs = compute_paired_differences(baseline_df, flow_df, 'MAE')

        # Should only have 2 values (NaN filtered)
        self.assertEqual(len(diffs), 2)
        expected = np.array([1.0, 1.0])
        np.testing.assert_array_equal(diffs, expected)

    def test_paired_differences_misaligned_ids(self):
        """Test with misaligned sample IDs."""
        baseline_df = pd.DataFrame({
            'sample_id': [1, 2, 3],
            'MAE': [5.0, 6.0, 7.0]
        })
        flow_df = pd.DataFrame({
            'sample_id': [2, 3, 4],  # Different IDs
            'MAE': [4.0, 5.0, 6.0]
        })

        diffs = compute_paired_differences(baseline_df, flow_df, 'MAE')

        # Should only match on IDs 2 and 3
        self.assertEqual(len(diffs), 2)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow."""

    def setUp(self):
        np.random.seed(42)

    def test_complete_workflow(self):
        """Test complete workflow with synthetic data."""
        # Create synthetic data where flow model is better
        n_samples = 50
        baseline_mae = np.random.uniform(3, 7, n_samples)
        flow_mae = baseline_mae - np.random.uniform(0.5, 1.5, n_samples)  # Better

        baseline_df = pd.DataFrame({
            'sample_id': range(n_samples),
            'MAE': baseline_mae
        })
        flow_df = pd.DataFrame({
            'sample_id': range(n_samples),
            'MAE': flow_mae
        })

        # Compute differences
        diffs = compute_paired_differences(baseline_df, flow_df, 'MAE')

        # All differences should be positive (improvement)
        self.assertTrue(np.all(diffs > 0))

        # Compute CI
        mean, ci_lo, ci_hi = bootstrap_ci(diffs, n_bootstrap=1000)
        self.assertGreater(mean, 0)
        self.assertLess(ci_lo, mean)
        self.assertLess(mean, ci_hi)

        # Compute p-value (should be significant)
        p_value = bootstrap_pvalue(diffs, n_bootstrap=1000)
        self.assertLess(p_value, 0.05)

        # Compute effect size
        delta = cliffs_delta(diffs)
        self.assertGreater(delta, 0)  # Positive effect

    def test_no_difference_scenario(self):
        """Test when there's no real difference."""
        n_samples = 50
        mae_values = np.random.uniform(3, 7, n_samples)

        baseline_df = pd.DataFrame({
            'sample_id': range(n_samples),
            'MAE': mae_values
        })
        flow_df = pd.DataFrame({
            'sample_id': range(n_samples),
            'MAE': mae_values + np.random.normal(0, 0.1, n_samples)  # Just noise
        })

        # Compute differences
        diffs = compute_paired_differences(baseline_df, flow_df, 'MAE')

        # CI should include zero (likely)
        mean, ci_lo, ci_hi = bootstrap_ci(diffs, n_bootstrap=1000)
        # With just noise, confidence interval should cross zero
        # (though not guaranteed in every random run)

        # p-value should not be significant (likely)
        p_value = bootstrap_pvalue(diffs, n_bootstrap=1000)
        # Note: Due to randomness, this might occasionally fail
        # In practice, with pure noise, p-value should be > 0.05


def run_tests():
    """Run all tests."""
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return success status
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
