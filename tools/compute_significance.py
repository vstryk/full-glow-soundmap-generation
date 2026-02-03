"""
Statistical significance analysis for soundmap generation models.

Computes paired scene-wise comparisons between baseline and conditional models,
including 95% confidence intervals via bootstrap, significance tests (Wilcoxon
and bootstrap), Holm-Bonferroni correction, and effect sizes (Cliff's delta).
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, List, Tuple
import warnings

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Set random seed for reproducibility
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)


def load_regime_data(results_dir: str, regime: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load metrics and SSIM data for a specific regime.

    Args:
        results_dir: Base directory containing evaluation results
        regime: Regime name (baseline, diffraction, reflection)

    Returns:
        Tuple of (metrics_df, ssim_df)
    """
    regime_folder = f"urban_sound_25k_{regime}"

    # Load metrics
    metrics_path = os.path.join(results_dir, regime_folder, "evaluation_results", regime_folder, "metrics", "detailed_results.csv")
    metrics_df = pd.read_csv(metrics_path)

    # Load SSIM - try multiple possible paths
    ssim_paths = [
        # New structure: inside evaluation_results
        os.path.join(results_dir, regime_folder, "evaluation_results", regime, "ssim_analysis", "detailed_results.csv"),
        # Alternative: direct ssim_analysis folder
        os.path.join(results_dir, "ssim_analysis", regime, "detailed_results.csv"),
        os.path.join(results_dir, "ssim_analysis", regime, "ssim_analysis", "detailed_results.csv"),
    ]

    ssim_df = None
    for ssim_path in ssim_paths:
        if os.path.exists(ssim_path):
            ssim_df = pd.read_csv(ssim_path)
            print(f"  Loaded SSIM from: {ssim_path}")
            break

    if ssim_df is None:
        warnings.warn(f"SSIM data not found for {regime}, proceeding without SSIM metric")
        # Return only metrics data
        return metrics_df

    # Check if sample_id in SSIM is just an index (0, 1, 2, ...)
    # while metrics has real IDs (23748, 23750, ...)
    # In that case, we need to align by index instead
    if len(ssim_df) > 0 and len(metrics_df) > 0:
        # Check if SSIM sample_id looks like indices
        ssim_sample_ids = ssim_df['sample_id'].values
        metrics_sample_ids = metrics_df['sample_id'].values

        # If SSIM starts at 0 and is sequential, and metrics doesn't, it's likely an index
        if (ssim_sample_ids[0] == 0 and
            len(ssim_sample_ids) > 1 and
            ssim_sample_ids[1] == 1 and
            metrics_sample_ids[0] != 0):
            # SSIM uses indices, metrics uses real IDs
            # Reset index for both and merge by position
            print(f"  Note: SSIM uses index-based sample_id, merging by position")
            ssim_df_aligned = ssim_df.copy()
            ssim_df_aligned['sample_id'] = metrics_df['sample_id'].values[:len(ssim_df)]
            merged_df = pd.merge(metrics_df, ssim_df_aligned[['sample_id', 'ssim']],
                               on='sample_id', how='inner')
        else:
            # Both use same ID scheme, merge normally
            merged_df = pd.merge(metrics_df, ssim_df[['sample_id', 'ssim']],
                               on='sample_id', how='inner')
    else:
        # One is empty, just return what we have
        if len(ssim_df) == 0:
            return metrics_df
        else:
            return ssim_df

    return merged_df


def compute_paired_differences(baseline_df: pd.DataFrame, flow_df: pd.DataFrame,
                               metric: str, higher_is_better: bool = False) -> np.ndarray:
    """
    Compute paired scene-wise differences.

    For most metrics (MAE, wMAPE): d = baseline - flow (positive = improvement)
    For SSIM: d = flow - baseline (positive = improvement)

    Args:
        baseline_df: Baseline model results
        flow_df: Flow model (conditional) results
        metric: Metric column name
        higher_is_better: If True, compute flow - baseline

    Returns:
        Array of paired differences (NaN/Inf filtered)
    """
    # Align by sample_id
    merged = pd.merge(
        baseline_df[['sample_id', metric]],
        flow_df[['sample_id', metric]],
        on='sample_id',
        suffixes=('_baseline', '_flow')
    )

    baseline_vals = merged[f'{metric}_baseline'].values
    flow_vals = merged[f'{metric}_flow'].values

    if higher_is_better:
        differences = flow_vals - baseline_vals
    else:
        differences = baseline_vals - flow_vals

    # Filter NaN and Inf
    valid_mask = np.isfinite(differences)
    differences_clean = differences[valid_mask]

    n_dropped = len(differences) - len(differences_clean)
    if n_dropped > 0:
        warnings.warn(f"Dropped {n_dropped} NaN/Inf values for metric {metric}")

    return differences_clean


def bootstrap_ci(data: np.ndarray, n_bootstrap: int = 10000,
                 confidence_level: float = 0.95) -> Tuple[float, float, float]:
    """
    Compute bootstrap confidence interval for mean.

    Args:
        data: Array of observations
        n_bootstrap: Number of bootstrap resamples
        confidence_level: Confidence level (default 0.95)

    Returns:
        Tuple of (mean, ci_lower, ci_upper)
    """
    rng = np.random.RandomState(RANDOM_SEED)
    n = len(data)
    bootstrap_means = np.zeros(n_bootstrap)

    for i in range(n_bootstrap):
        resample = rng.choice(data, size=n, replace=True)
        bootstrap_means[i] = np.mean(resample)

    mean = np.mean(data)
    alpha = 1 - confidence_level
    ci_lower = np.percentile(bootstrap_means, 100 * alpha / 2)
    ci_upper = np.percentile(bootstrap_means, 100 * (1 - alpha / 2))

    return mean, ci_lower, ci_upper


def bootstrap_pvalue(data: np.ndarray, n_bootstrap: int = 10000) -> float:
    """
    Compute bootstrap p-value for H0: mean(data) = 0.

    Args:
        data: Array of paired differences
        n_bootstrap: Number of bootstrap resamples

    Returns:
        Two-sided p-value
    """
    rng = np.random.RandomState(RANDOM_SEED)
    n = len(data)
    observed_mean = np.mean(data)

    # Bootstrap under null (center data at zero)
    centered_data = data - observed_mean
    bootstrap_means = np.zeros(n_bootstrap)

    for i in range(n_bootstrap):
        resample = rng.choice(centered_data, size=n, replace=True)
        bootstrap_means[i] = np.mean(resample)

    # Two-sided p-value
    p_value = np.mean(np.abs(bootstrap_means) >= np.abs(observed_mean))

    return p_value


def cliffs_delta(data: np.ndarray) -> float:
    """
    Compute Cliff's delta effect size.

    Cliff's delta measures how often values in one group are larger than in another.
    Here, we compare differences against zero.

    Args:
        data: Array of paired differences

    Returns:
        Cliff's delta (range: -1 to 1)
    """
    n = len(data)
    if n == 0:
        return np.nan

    # Count how many differences are > 0 vs < 0
    n_positive = np.sum(data > 0)
    n_negative = np.sum(data < 0)

    delta = (n_positive - n_negative) / n
    return delta


def holm_bonferroni_correction(p_values: List[float]) -> List[float]:
    """
    Apply Holm-Bonferroni correction for multiple testing.

    Args:
        p_values: List of p-values

    Returns:
        List of corrected p-values
    """
    n = len(p_values)
    if n == 0:
        return []

    # Sort p-values with their original indices
    sorted_indices = np.argsort(p_values)
    sorted_p = np.array(p_values)[sorted_indices]

    # Holm correction
    corrected_p = np.zeros(n)
    for i in range(n):
        corrected_p[sorted_indices[i]] = min(1.0, sorted_p[i] * (n - i))

    # Ensure monotonicity
    for i in range(1, n):
        idx = sorted_indices[i]
        prev_idx = sorted_indices[i - 1]
        corrected_p[idx] = max(corrected_p[idx], corrected_p[prev_idx])

    return corrected_p.tolist()


def analyze_regime_comparison(baseline_df: pd.DataFrame, flow_df: pd.DataFrame,
                               regime: str, metrics: List[str]) -> List[Dict]:
    """
    Analyze all metrics for a single regime comparison.

    Args:
        baseline_df: Baseline model results
        flow_df: Flow model results
        regime: Regime name
        metrics: List of metric column names

    Returns:
        List of result dictionaries
    """
    results = []
    p_values_for_correction = []

    # Define which metrics have "higher is better" semantics
    higher_is_better_metrics = {'ssim'}

    for metric in metrics:
        if metric not in baseline_df.columns or metric not in flow_df.columns:
            warnings.warn(f"Metric {metric} not found in dataframes, skipping")
            continue

        higher_is_better = metric.lower() in higher_is_better_metrics
        differences = compute_paired_differences(baseline_df, flow_df, metric, higher_is_better)

        if len(differences) == 0:
            warnings.warn(f"No valid differences for {regime}/{metric}")
            continue

        # Compute statistics
        mean_diff, ci_lo, ci_hi = bootstrap_ci(differences)
        median_diff = np.median(differences)

        # Wilcoxon signed-rank test
        try:
            wilcoxon_result = stats.wilcoxon(differences, alternative='two-sided')
            p_wilcoxon = wilcoxon_result.pvalue
        except Exception as e:
            warnings.warn(f"Wilcoxon test failed for {regime}/{metric}: {e}")
            p_wilcoxon = np.nan

        # Bootstrap p-value
        p_bootstrap = bootstrap_pvalue(differences)

        # Effect size
        delta = cliffs_delta(differences)

        result = {
            'regime': regime,
            'metric': metric,
            'n_scenes': len(differences),
            'mean_diff': mean_diff,
            'ci_lo': ci_lo,
            'ci_hi': ci_hi,
            'p_wilcoxon': p_wilcoxon,
            'p_bootstrap': p_bootstrap,
            'cliffs_delta': delta,
            'median_diff': median_diff
        }

        results.append(result)
        p_values_for_correction.append(p_wilcoxon)

    # Apply Holm correction
    p_holm = holm_bonferroni_correction(p_values_for_correction)
    for i, result in enumerate(results):
        result['p_holm'] = p_holm[i]

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Compute statistical significance analysis for soundmap models"
    )
    parser.add_argument(
        "--results_dir",
        type=str,
        default="E:/ba_ergebnisse",
        help="Directory containing evaluation results"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./",
        help="Output directory for results, figures, and reports"
    )
    parser.add_argument(
        "--regimes",
        nargs='+',
        default=['baseline', 'diffraction', 'reflection'],
        help="List of regimes to analyze"
    )
    parser.add_argument(
        "--metrics",
        nargs='+',
        default=['MAE', 'LoS_MAE', 'NLoS_MAE', 'LoS_wMAPE', 'NLoS_wMAPE', 'ssim'],
        help="List of metrics to analyze"
    )

    args = parser.parse_args()

    # Create output directories
    results_dir_out = os.path.join(args.output_dir, 'results')
    figures_dir = os.path.join(args.output_dir, 'figures')
    reports_dir = os.path.join(args.output_dir, 'reports')

    os.makedirs(results_dir_out, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)

    print("=" * 80)
    print("Statistical Significance Analysis for Soundmap Generation")
    print("=" * 80)
    print(f"\nResults directory: {args.results_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Regimes: {args.regimes}")
    print(f"Metrics: {args.metrics}")
    print(f"Random seed: {RANDOM_SEED}")
    print(f"Bootstrap resamples: 10,000")
    print(f"Confidence level: 95%\n")

    all_results = []

    # Note: For this analysis, we compare each regime against itself as "baseline"
    # The user's setup has separate models (baseline, diffraction, reflection)
    # We'll compare diffraction vs baseline and reflection vs baseline

    # Load baseline data (this is the "no extra conditions" model)
    print("Loading baseline model data...")
    baseline_data = load_regime_data(args.results_dir, 'baseline')
    print(f"  Columns in baseline data: {list(baseline_data.columns)}")
    print(f"  Number of rows: {len(baseline_data)}")

    for regime in args.regimes:
        if regime == 'baseline':
            # Skip baseline vs baseline comparison
            continue

        print(f"\n{'=' * 80}")
        print(f"Analyzing: {regime.upper()} vs BASELINE")
        print(f"{'=' * 80}")

        # Load flow model data
        flow_data = load_regime_data(args.results_dir, regime)

        print(f"Baseline samples: {len(baseline_data)}")
        print(f"{regime.capitalize()} samples: {len(flow_data)}")
        print(f"  Columns in {regime} data: {list(flow_data.columns)}")

        # Analyze comparison
        regime_results = analyze_regime_comparison(
            baseline_data, flow_data, regime, args.metrics
        )

        all_results.extend(regime_results)

        # Print results for this regime
        print(f"\nResults for {regime}:")
        for res in regime_results:
            print(f"  {res['metric']:12s}: mean_diff={res['mean_diff']:7.4f}, "
                  f"CI=[{res['ci_lo']:7.4f}, {res['ci_hi']:7.4f}], "
                  f"p_holm={res['p_holm']:.4f}, delta={res['cliffs_delta']:6.3f}")

    # Create DataFrame and save results
    results_df = pd.DataFrame(all_results)

    # Check if we have results
    if len(results_df) == 0:
        print("\n" + "=" * 80)
        print("WARNING: No results generated!")
        print("=" * 80)
        print("\nPossible reasons:")
        print("  - No valid metric comparisons found")
        print("  - All differences contained NaN/Inf values")
        print("  - Data loading failed")
        print("\nPlease check the warnings above for details.")
        return

    # Save CSV
    csv_path = os.path.join(results_dir_out, 'significance_summary.csv')
    results_df.to_csv(csv_path, index=False, encoding='utf-8')
    print(f"\n✓ Results saved to: {csv_path}")

    # Generate LaTeX table
    latex_path = os.path.join(reports_dir, 'table_significance.tex')
    generate_latex_table(results_df, latex_path)
    print(f"✓ LaTeX table saved to: {latex_path}")

    # Generate Markdown report
    md_path = os.path.join(reports_dir, 'significance_report.md')
    generate_markdown_report(results_df, md_path)
    print(f"✓ Markdown report saved to: {md_path}")

    print(f"\n{'=' * 80}")
    print("Analysis complete!")
    print(f"{'=' * 80}\n")


def generate_latex_table(df: pd.DataFrame, output_path: str):
    """Generate LaTeX table for publication."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\\begin{table}[htbp]\n")
        f.write("\\centering\n")
        f.write("\\caption{Statistical Significance Analysis: Flow Models vs. Baseline}\n")
        f.write("\\label{tab:significance}\n")
        f.write("\\begin{tabular}{llrrrrr}\n")
        f.write("\\hline\n")
        f.write("Regime & Metric & $n$ & $\\bar{d}$ & 95\\% CI & $p_{\\text{Holm}}$ & $\\delta$ \\\\\n")
        f.write("\\hline\n")

        for _, row in df.iterrows():
            regime = row['regime'].capitalize()
            metric = row['metric']
            n = int(row['n_scenes'])
            mean_diff = row['mean_diff']
            ci_lo = row['ci_lo']
            ci_hi = row['ci_hi']
            p_holm = row['p_holm']
            delta = row['cliffs_delta']

            # Format p-value with significance stars
            if p_holm < 0.001:
                p_str = f"{p_holm:.4f}***"
            elif p_holm < 0.01:
                p_str = f"{p_holm:.4f}**"
            elif p_holm < 0.05:
                p_str = f"{p_holm:.4f}*"
            else:
                p_str = f"{p_holm:.4f}"

            ci_str = f"[{ci_lo:.2f}, {ci_hi:.2f}]"

            f.write(f"{regime} & {metric} & {n} & {mean_diff:.3f} & {ci_str} & {p_str} & {delta:.2f} \\\\\n")

        f.write("\\hline\n")
        f.write("\\end{tabular}\n")
        f.write("\\begin{tablenotes}\n")
        f.write("\\small\n")
        f.write("\\item Note: $\\bar{d}$ = mean scene-wise difference (positive = improvement), ")
        f.write("CI = bootstrap confidence interval, ")
        f.write("$p_{\\text{Holm}}$ = Holm-adjusted p-value, ")
        f.write("$\\delta$ = Cliff's delta effect size. ")
        f.write("Significance: *** $p<0.001$, ** $p<0.01$, * $p<0.05$.\n")
        f.write("\\end{tablenotes}\n")
        f.write("\\end{table}\n")


def generate_markdown_report(df: pd.DataFrame, output_path: str):
    """Generate Markdown report with interpretations."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Statistical Significance Analysis Report\n\n")
        f.write("## Methodology\n\n")
        f.write("- **Comparison**: Flow models (Diffraction, Reflection) vs. Baseline (no extra conditions)\n")
        f.write("- **Metrics**: MAE, LoS_MAE, NLoS_MAE, LoS_wMAPE, NLoS_wMAPE, SSIM\n")
        f.write("- **Differences**: For MAE/wMAPE: d = baseline - flow (positive = improvement)\n")
        f.write("- **Differences**: For SSIM: d = flow - baseline (positive = improvement)\n")
        f.write("- **Confidence Intervals**: 95% bootstrap CI (10,000 resamples)\n")
        f.write("- **Significance Tests**: Wilcoxon signed-rank (two-sided) + bootstrap test\n")
        f.write("- **Multiple Testing Correction**: Holm-Bonferroni\n")
        f.write("- **Effect Size**: Cliff's δ\n")
        f.write("- **Reproducibility**: Random seed = 42\n\n")

        f.write("## Results by Regime\n\n")

        for regime in df['regime'].unique():
            regime_df = df[df['regime'] == regime]
            f.write(f"### {regime.capitalize()} vs. Baseline\n\n")

            for _, row in regime_df.iterrows():
                metric = row['metric']
                n = int(row['n_scenes'])
                mean_diff = row['mean_diff']
                ci_lo = row['ci_lo']
                ci_hi = row['ci_hi']
                p_wilcoxon = row['p_wilcoxon']
                p_holm = row['p_holm']
                delta = row['cliffs_delta']
                median_diff = row['median_diff']

                # Interpret effect size (Cliff's delta)
                if abs(delta) < 0.147:
                    effect_size = "negligible"
                elif abs(delta) < 0.33:
                    effect_size = "small"
                elif abs(delta) < 0.474:
                    effect_size = "medium"
                else:
                    effect_size = "large"

                # Interpret significance
                if p_holm < 0.05:
                    sig_text = f"**statistically significant** (p={p_holm:.4f})"
                else:
                    sig_text = f"not statistically significant (p={p_holm:.4f})"

                # Direction
                if mean_diff > 0:
                    direction = "improvement"
                elif mean_diff < 0:
                    direction = "degradation"
                else:
                    direction = "no change"

                f.write(f"**{metric}**: Mean scene-wise {direction} = {mean_diff:.4f}, ")
                f.write(f"95% CI [{ci_lo:.4f}, {ci_hi:.4f}], ")
                f.write(f"median = {median_diff:.4f}, ")
                f.write(f"n={n} scenes. ")
                f.write(f"Wilcoxon p={p_wilcoxon:.4f}, ")
                f.write(f"Holm-adjusted p={p_holm:.4f} ({sig_text}). ")
                f.write(f"Cliff's δ={delta:.3f} ({effect_size} effect size).\n\n")

        f.write("## Interpretation Guide\n\n")
        f.write("- **Mean difference (d̄)**: Average improvement per scene. Positive values indicate the flow model performs better.\n")
        f.write("- **95% CI**: If the confidence interval excludes zero, the difference is likely real.\n")
        f.write("- **p-value (Holm-adjusted)**: Probability of observing this difference by chance. p<0.05 typically considered significant.\n")
        f.write("- **Cliff's δ**: Non-parametric effect size. |δ|<0.147: negligible, 0.147-0.33: small, 0.33-0.474: medium, >0.474: large.\n\n")

        f.write("---\n")
        f.write("*Generated with Claude Code - Statistical Evaluation Pipeline*\n")


if __name__ == "__main__":
    main()
