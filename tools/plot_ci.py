"""
Visualization of confidence intervals for statistical significance analysis.

Creates errorbar plots showing mean scene-wise improvements with 95% bootstrap
confidence intervals for each metric and regime.
"""

import os
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from typing import List


def plot_confidence_intervals(df: pd.DataFrame, regime: str, output_dir: str):
    """
    Create errorbar plot for a single regime showing all metrics.

    Args:
        df: DataFrame with significance results for one regime
        regime: Regime name
        output_dir: Output directory for figures
    """
    if len(df) == 0:
        print(f"Warning: No data for regime {regime}")
        return

    # Prepare data
    metrics = df['metric'].tolist()
    mean_diffs = df['mean_diff'].tolist()
    ci_lows = df['ci_lo'].tolist()
    ci_highs = df['ci_hi'].tolist()
    p_values = df['p_holm'].tolist()

    # Calculate error bars (distance from mean to CI bounds)
    errors_low = [mean - ci_lo for mean, ci_lo in zip(mean_diffs, ci_lows)]
    errors_high = [ci_hi - mean for mean, ci_hi in zip(mean_diffs, ci_highs)]
    errors = [errors_low, errors_high]

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))

    # Create positions for each metric
    positions = np.arange(len(metrics))

    # Color code by significance
    colors = ['#2ecc71' if p < 0.05 else '#95a5a6' for p in p_values]

    # Plot error bars - matplotlib doesn't support list of colors for errorbar
    # So we plot each point individually
    for i, pos in enumerate(positions):
        ax.errorbar(
            pos,
            mean_diffs[i],
            yerr=[[errors[0][i]], [errors[1][i]]],
            fmt='o',
            markersize=8,
            capsize=5,
            capthick=2,
            linewidth=2,
            ecolor=colors[i],
            markerfacecolor=colors[i],
            markeredgecolor='black',
            markeredgewidth=1
        )

    # Add zero line (null hypothesis)
    ax.axhline(y=0, color='red', linestyle='--', linewidth=1.5, alpha=0.7, label='H₀: no difference')

    # Customize plot
    ax.set_xticks(positions)
    ax.set_xticklabels(metrics, rotation=45, ha='right')
    ax.set_xlabel('Metric', fontsize=12, fontweight='bold')
    ax.set_ylabel('Mean Scene-wise Improvement', fontsize=12, fontweight='bold')
    ax.set_title(f'{regime.capitalize()} vs. Baseline: 95% Confidence Intervals',
                 fontsize=14, fontweight='bold', pad=20)

    # Add grid
    ax.grid(True, axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2ecc71', edgecolor='black', label='p < 0.05 (significant)'),
        Patch(facecolor='#95a5a6', edgecolor='black', label='p ≥ 0.05 (not significant)'),
        plt.Line2D([0], [0], color='red', linestyle='--', linewidth=1.5, label='H₀: no difference')
    ]
    ax.legend(handles=legend_elements, loc='best', framealpha=0.9)

    # Adjust layout
    plt.tight_layout()

    # Save figure
    output_path = os.path.join(output_dir, f'ci_plot_{regime}.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Saved plot: {output_path}")


def plot_all_regimes_combined(df: pd.DataFrame, output_dir: str):
    """
    Create a combined plot showing all regimes side-by-side for comparison.

    Args:
        df: Complete DataFrame with all regimes
        output_dir: Output directory for figures
    """
    regimes = df['regime'].unique()
    metrics = df['metric'].unique()

    # Create figure with subplots
    n_metrics = len(metrics)
    fig, axes = plt.subplots(1, n_metrics, figsize=(4 * n_metrics, 6), sharey=True)

    if n_metrics == 1:
        axes = [axes]

    for i, metric in enumerate(metrics):
        ax = axes[i]
        metric_df = df[df['metric'] == metric]

        # Prepare data
        regime_names = []
        mean_diffs = []
        errors_low = []
        errors_high = []
        colors = []

        for regime in regimes:
            regime_data = metric_df[metric_df['regime'] == regime]
            if len(regime_data) == 0:
                continue

            row = regime_data.iloc[0]
            regime_names.append(regime.capitalize())
            mean_diffs.append(row['mean_diff'])
            errors_low.append(row['mean_diff'] - row['ci_lo'])
            errors_high.append(row['ci_hi'] - row['mean_diff'])
            colors.append('#2ecc71' if row['p_holm'] < 0.05 else '#95a5a6')

        positions = np.arange(len(regime_names))

        # Plot error bars - plot each individually to support different colors
        for i, pos in enumerate(positions):
            ax.errorbar(
                pos,
                mean_diffs[i],
                yerr=[[errors_low[i]], [errors_high[i]]],
                fmt='o',
                markersize=10,
                capsize=6,
                capthick=2,
                linewidth=2.5,
                ecolor=colors[i],
                markerfacecolor=colors[i],
                markeredgecolor='black',
                markeredgewidth=1.5
            )

        # Add zero line
        ax.axhline(y=0, color='red', linestyle='--', linewidth=1.5, alpha=0.7)

        # Customize subplot
        ax.set_xticks(positions)
        ax.set_xticklabels(regime_names, rotation=45, ha='right')
        ax.set_title(metric, fontsize=12, fontweight='bold')
        ax.grid(True, axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)

        if i == 0:
            ax.set_ylabel('Mean Improvement', fontsize=12, fontweight='bold')

    # Overall title
    fig.suptitle('Comparison Across All Regimes: 95% Confidence Intervals',
                 fontsize=14, fontweight='bold', y=1.02)

    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2ecc71', edgecolor='black', label='p < 0.05'),
        Patch(facecolor='#95a5a6', edgecolor='black', label='p ≥ 0.05'),
        plt.Line2D([0], [0], color='red', linestyle='--', linewidth=1.5, label='H₀')
    ]
    fig.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(0.98, 0.98),
               framealpha=0.9)

    # Adjust layout
    plt.tight_layout()

    # Save figure
    output_path = os.path.join(output_dir, 'ci_plot_all_regimes.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Saved combined plot: {output_path}")


def create_forest_plot(df: pd.DataFrame, output_dir: str):
    """
    Create a forest plot showing all results in publication-ready format.

    Args:
        df: Complete DataFrame with all regimes
        output_dir: Output directory for figures
    """
    # Sort by regime and metric
    df_sorted = df.sort_values(['regime', 'metric'])

    # Create figure
    fig, ax = plt.subplots(figsize=(12, len(df_sorted) * 0.5))

    # Plot each result as a horizontal error bar
    y_positions = np.arange(len(df_sorted))

    for i, (_, row) in enumerate(df_sorted.iterrows()):
        mean_diff = row['mean_diff']
        ci_lo = row['ci_lo']
        ci_hi = row['ci_hi']
        p_holm = row['p_holm']

        # Color by significance
        color = '#2ecc71' if p_holm < 0.05 else '#95a5a6'

        # Plot error bar
        ax.plot([ci_lo, ci_hi], [i, i], color=color, linewidth=3, alpha=0.7)
        ax.plot(mean_diff, i, 'o', color=color, markersize=10,
                markeredgecolor='black', markeredgewidth=1.5)

    # Add zero line
    ax.axvline(x=0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='H₀')

    # Labels
    labels = [f"{row['regime'].capitalize()}: {row['metric']}"
              for _, row in df_sorted.iterrows()]
    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel('Mean Scene-wise Improvement (95% CI)', fontsize=12, fontweight='bold')
    ax.set_title('Forest Plot: All Regimes and Metrics', fontsize=14, fontweight='bold', pad=20)

    # Grid
    ax.grid(True, axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2ecc71', edgecolor='black', label='Significant (p < 0.05)'),
        Patch(facecolor='#95a5a6', edgecolor='black', label='Not significant'),
        plt.Line2D([0], [0], color='red', linestyle='--', linewidth=2, label='No effect')
    ]
    ax.legend(handles=legend_elements, loc='best', framealpha=0.9)

    # Adjust layout
    plt.tight_layout()

    # Save
    output_path = os.path.join(output_dir, 'forest_plot.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Saved forest plot: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Create confidence interval plots from significance analysis"
    )
    parser.add_argument(
        "--results_csv",
        type=str,
        default="./results/significance_summary.csv",
        help="Path to significance summary CSV file"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./figures",
        help="Output directory for plots"
    )

    args = parser.parse_args()

    # Check if input file exists
    if not os.path.exists(args.results_csv):
        print(f"Error: Results file not found: {args.results_csv}")
        print("Please run compute_significance.py first.")
        return

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    print("=" * 80)
    print("Confidence Interval Plotting")
    print("=" * 80)
    print(f"\nInput file: {args.results_csv}")
    print(f"Output directory: {args.output_dir}\n")

    # Load results
    df = pd.read_csv(args.results_csv)
    print(f"Loaded {len(df)} results")

    # Create plots for each regime
    regimes = df['regime'].unique()
    print(f"\nCreating individual plots for {len(regimes)} regimes...")

    for regime in regimes:
        regime_df = df[df['regime'] == regime]
        plot_confidence_intervals(regime_df, regime, args.output_dir)

    # Create combined plots
    print("\nCreating combined plots...")
    plot_all_regimes_combined(df, args.output_dir)
    create_forest_plot(df, args.output_dir)

    print(f"\n{'=' * 80}")
    print("Plotting complete!")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    main()
