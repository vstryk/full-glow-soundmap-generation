"""
Create publication-ready error plots for NeurIPS workshop paper revision.

Addresses reviewer concerns about:
1. Missing error bars on main results
2. Lack of statistical validation
3. Need for deeper analysis of performance
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys

# Use publication style
plt.style.use('seaborn-v0_8-paper')
plt.rcParams.update({
    'font.size': 9,
    'axes.labelsize': 10,
    'axes.titlesize': 11,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'font.family': 'serif',
})


def load_data(base_dir):
    """Load evaluation results for all regimes."""
    regimes = ['baseline', 'diffraction', 'reflection']
    data = {}

    for regime in regimes:
        metrics_path = Path(base_dir) / f'urban_sound_25k_{regime}' / 'evaluation_results' / f'urban_sound_25k_{regime}' / 'metrics' / 'detailed_results.csv'
        if metrics_path.exists():
            data[regime] = pd.read_csv(metrics_path)
            print(f"Loaded {regime}: {len(data[regime])} samples")
        else:
            print(f"Warning: {metrics_path} not found")

    return data


def bootstrap_ci(data, n_bootstrap=1000, ci=95):
    """Calculate bootstrap confidence interval."""
    np.random.seed(42)
    bootstrap_means = []

    for _ in range(n_bootstrap):
        sample = np.random.choice(data, size=len(data), replace=True)
        bootstrap_means.append(np.mean(sample))

    lower = np.percentile(bootstrap_means, (100 - ci) / 2)
    upper = np.percentile(bootstrap_means, 100 - (100 - ci) / 2)

    return np.mean(data), lower, upper


def plot1_model_comparison_with_ci(data, output_dir):
    """Plot 1: Main results with error bars (addresses Review concern #1)."""

    # Baseline values from other models (from Table 1)
    baseline_models = {
        'UNet': {'LoS_MAE': 2.29, 'NLoS_MAE': 1.73},
        'Pix2Pix': {'LoS_MAE': 1.73, 'NLoS_MAE': 1.19},
        'DDPM': {'LoS_MAE': 2.42, 'NLoS_MAE': 3.26},
    }

    diffraction_models = {
        'UNet': {'LoS_MAE': 0.94, 'NLoS_MAE': 3.27},
        'Pix2Pix': {'LoS_MAE': 0.91, 'NLoS_MAE': 3.36},
        'DDPM': {'LoS_MAE': 1.59, 'NLoS_MAE': 3.27},
    }

    reflection_models = {
        'UNet': {'LoS_MAE': 2.29, 'NLoS_MAE': 5.72},
        'Pix2Pix': {'LoS_MAE': 2.14, 'NLoS_MAE': 4.79},
        'DDPM': {'LoS_MAE': 2.74, 'NLoS_MAE': 7.93},
    }

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    scenarios = [
        ('baseline', baseline_models, 'Baseline'),
        ('diffraction', diffraction_models, 'Diffraction'),
        ('reflection', reflection_models, 'Reflection')
    ]

    for idx, (regime, models, title) in enumerate(scenarios):
        ax = axes[idx]

        if regime not in data:
            continue

        df = data[regime]

        # Calculate Full Glow results with CI
        los_mean, los_lower, los_upper = bootstrap_ci(df['LoS_MAE'].values)
        nlos_mean, nlos_lower, nlos_upper = bootstrap_ci(df['NLoS_MAE'].values)

        # Prepare data for plotting
        model_names = list(models.keys()) + ['Full Glow\n(ours)']
        x_pos = np.arange(len(model_names))

        # LoS values
        los_values = [models[m]['LoS_MAE'] for m in models.keys()] + [los_mean]
        los_errors_lower = [0] * len(models) + [los_mean - los_lower]
        los_errors_upper = [0] * len(models) + [los_upper - los_mean]

        # NLoS values
        nlos_values = [models[m]['NLoS_MAE'] for m in models.keys()] + [nlos_mean]
        nlos_errors_lower = [0] * len(models) + [nlos_mean - nlos_lower]
        nlos_errors_upper = [0] * len(models) + [nlos_upper - nlos_mean]

        width = 0.35

        # Use viridis colormap for LoS/NLoS (consistent with soundmap visualization)
        viridis_cmap = plt.cm.viridis
        los_color = viridis_cmap(0.3)   # Green-teal from viridis
        nlos_color = viridis_cmap(0.7)  # Yellow from viridis

        # Plot bars - only our model gets error bars (without caps)
        bars1 = ax.bar(x_pos - width/2, los_values, width,
                       yerr=[los_errors_lower, los_errors_upper],
                       label='LoS MAE', color=los_color, alpha=0.8,
                       error_kw={'linewidth': 1.5, 'capsize': 0})

        bars2 = ax.bar(x_pos + width/2, nlos_values, width,
                       yerr=[nlos_errors_lower, nlos_errors_upper],
                       label='NLoS MAE', color=nlos_color, alpha=0.8,
                       error_kw={'linewidth': 1.5, 'capsize': 0})

        # Highlight our model with black border
        bars1[-1].set_edgecolor('black')
        bars1[-1].set_linewidth(2)
        bars2[-1].set_edgecolor('black')
        bars2[-1].set_linewidth(2)

        ax.set_xlabel('Model')
        ax.set_ylabel('MAE (dB)')
        ax.set_title(title)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(model_names, rotation=15, ha='right')
        ax.legend(loc='upper right')
        ax.grid(axis='y', alpha=0.3)
        ax.set_axisbelow(True)

    # plt.suptitle('Model Comparison with 95% Confidence Intervals',
    #              fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()

    output_path = Path(output_dir) / 'model_comparison_with_ci.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"Created: {output_path}")


def plot2_error_distributions(data, output_dir):
    """Plot 2: Error distributions per scenario (addresses robustness concerns)."""

    fig, axes = plt.subplots(2, 3, figsize=(12, 8))

    scenarios = ['baseline', 'diffraction', 'reflection']
    metrics = ['LoS_MAE', 'NLoS_MAE']

    for col, regime in enumerate(scenarios):
        if regime not in data:
            continue

        df = data[regime]

        for row, metric in enumerate(metrics):
            ax = axes[row, col]

            # Use viridis colormap for LoS/NLoS (consistent with soundmap visualization)
            viridis_cmap = plt.cm.viridis
            los_color = viridis_cmap(0.3)   # Green-teal from viridis
            nlos_color = viridis_cmap(0.7)  # Yellow from viridis

            # Violin plot with box plot overlay
            parts = ax.violinplot([df[metric].values], positions=[0],
                                  widths=0.7, showmeans=True, showmedians=True)

            # Color the violin
            for pc in parts['bodies']:
                pc.set_facecolor(los_color if 'LoS' in metric else nlos_color)
                pc.set_alpha(0.6)

            # Add box plot
            bp = ax.boxplot([df[metric].values], positions=[0], widths=0.3,
                           patch_artist=True, showcaps=False, showfliers=False)
            bp['boxes'][0].set_facecolor('white')
            bp['boxes'][0].set_alpha(0.8)

            # Statistics text
            mean_val = df[metric].mean()
            median_val = df[metric].median()
            std_val = df[metric].std()

            stats_text = f'μ={mean_val:.2f}\nσ={std_val:.2f}\nMd={median_val:.2f}'
            ax.text(0.5, 0.95, stats_text, transform=ax.transAxes,
                   fontsize=8, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

            if row == 0:
                ax.set_title(regime.capitalize(), fontweight='bold')

            if col == 0:
                ax.set_ylabel(f'{metric} (dB)')

            ax.set_xticks([])
            ax.grid(axis='y', alpha=0.3)
            ax.set_axisbelow(True)

    # plt.suptitle('Error Distribution per Scenario (n=1,244 test scenes)',
    #              fontsize=13, fontweight='bold')
    plt.tight_layout()

    output_path = Path(output_dir) / 'error_distribution_per_scenario.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"Created: {output_path}")


def plot3_los_vs_nlos_tradeoff(data, output_dir):
    """Plot 3: LoS vs NLoS trade-off visualization (failure mode analysis)."""

    fig, ax = plt.subplots(figsize=(8, 6))

    # Use viridis colormap for regimes (consistent with soundmap visualization)
    viridis_cmap = plt.cm.viridis
    colors = {
        'baseline': viridis_cmap(0.2),    # Green-ish (early viridis)
        'diffraction': viridis_cmap(0.5), # Teal (mid viridis)
        'reflection': viridis_cmap(0.8)   # Yellow (late viridis)
    }
    markers = {'baseline': 'o', 'diffraction': 's', 'reflection': '^'}

    for regime, df in data.items():
        # Scatter plot of individual scenes
        ax.scatter(df['LoS_MAE'], df['NLoS_MAE'],
                  alpha=0.15, s=20, c=[colors[regime]],
                  marker=markers[regime], label=f'{regime.capitalize()} (scenes)')

        # Mean with CI
        los_mean, los_lower, los_upper = bootstrap_ci(df['LoS_MAE'].values)
        nlos_mean, nlos_lower, nlos_upper = bootstrap_ci(df['NLoS_MAE'].values)

        # Plot mean with error bars
        ax.errorbar(los_mean, nlos_mean,
                   xerr=[[los_mean - los_lower], [los_upper - los_mean]],
                   yerr=[[nlos_mean - nlos_lower], [nlos_upper - nlos_mean]],
                   fmt='D', markersize=12, linewidth=2.5, capsize=6,
                   color=colors[regime], markeredgecolor='black',
                   markeredgewidth=1.5, label=f'{regime.capitalize()} (mean ± 95% CI)',
                   zorder=10)

    # Diagonal line (LoS = NLoS)
    max_val = max(ax.get_xlim()[1], ax.get_ylim()[1])
    ax.plot([0, max_val], [0, max_val], 'k--', alpha=0.3, linewidth=1,
           label='LoS = NLoS', zorder=0)

    ax.set_xlabel('LoS MAE (dB)', fontweight='bold')
    ax.set_ylabel('NLoS MAE (dB)', fontweight='bold')
    # ax.set_title('LoS vs. NLoS Performance Trade-off\n(showing individual scenes + mean with 95% CI)',
    #             fontweight='bold')
    ax.legend(loc='upper left', framealpha=0.95, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_axisbelow(True)

    # Add interpretation text
    textstr = 'Points above diagonal:\nNLoS harder than LoS\n\nPoints below diagonal:\nLoS harder than NLoS'
    ax.text(0.98, 0.02, textstr, transform=ax.transAxes,
           fontsize=8, verticalalignment='bottom', horizontalalignment='right',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()

    output_path = Path(output_dir) / 'los_vs_nlos_tradeoff.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"Created: {output_path}")


def main():
    base_dir = r'E:\ba_ergebnisse'
    output_dir = r'E:\Projekte\conditional-soundmap-generation\figures'

    print("="*80)
    print("Creating Review Response Plots")
    print("="*80)
    print()

    # Load data
    data = load_data(base_dir)

    if not data:
        print("ERROR: No data loaded!")
        return

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Generate plots
    print("\nGenerating plots...")
    plot1_model_comparison_with_ci(data, output_dir)
    plot2_error_distributions(data, output_dir)
    plot3_los_vs_nlos_tradeoff(data, output_dir)

    print("\n" + "="*80)
    print("All plots created successfully!")
    print("="*80)
    print("\nFiles created in:", output_dir)
    print("- model_comparison_with_ci.png (for Table 1 revision)")
    print("- error_distribution_per_scenario.png (robustness validation)")
    print("- los_vs_nlos_tradeoff.png (failure mode analysis)")
    print("\nUse these in your rebuttal and revised manuscript!")


if __name__ == '__main__':
    main()
