# Statistical Evaluation Pipeline

Comprehensive statistical evaluation for soundmap generation models with confidence intervals, significance tests, and effect sizes.

## Overview

This pipeline provides rigorous statistical analysis comparing flow-based models (Diffraction, Reflection) against the Baseline model, including:

- **95% Confidence Intervals** via paired bootstrap (10,000 resamples)
- **Significance Tests**: Wilcoxon signed-rank + bootstrap p-values
- **Multiple Testing Correction**: Holm-Bonferroni
- **Effect Sizes**: Cliff's δ
- **Reproducible Results**: Fixed random seed (42)

## Requirements

All dependencies are listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```

Key packages:
- `numpy >= 1.26.3`
- `pandas >= 2.2.3`
- `scipy >= 1.14.1`
- `matplotlib >= 3.10.0`

## Data Structure

Expected directory structure in your results folder (e.g., `E:\ba_ergebnisse`):

```
ba_ergebnisse/
├── urban_sound_25k_baseline/
│   └── metrics/
│       └── detailed_results.csv  # MAE, wMAPE, LoS metrics
├── urban_sound_25k_diffraction/
│   └── metrics/
│       └── detailed_results.csv
├── urban_sound_25k_reflection/
│   └── metrics/
│       └── detailed_results.csv
└── ssim_analysis/
    ├── baseline/
    │   └── detailed_results.csv  # SSIM values
    ├── diffraction/
    │   └── detailed_results.csv
    └── reflection/
        └── detailed_results.csv
```

### Expected CSV Format

**metrics/detailed_results.csv**:
```csv
sample_id,MAE,MAPE,LoS_MAE,NLoS_MAE,LoS_wMAPE,NLoS_wMAPE
23748,1.168817,5.643411,1.3413476,0.46775228,4.338699,10.94502
...
```

**ssim_analysis/{regime}/detailed_results.csv**:
```csv
sample_id,ssim,true_path,pred_path
0,0.9682078,path/to/true.png,path/to/pred.png
...
```

## Usage

### 1. Run Statistical Analysis

Compute paired scene-wise comparisons with bootstrap CI and significance tests:

```bash
python tools/compute_significance.py \
    --results_dir "E:/ba_ergebnisse" \
    --output_dir "./" \
    --regimes baseline diffraction reflection \
    --metrics MAE LoS_MAE NLoS_MAE LoS_wMAPE NLoS_wMAPE ssim
```

**Outputs**:
- `results/significance_summary.csv` - Complete results table
- `reports/significance_report.md` - Markdown report with interpretations
- `reports/table_significance.tex` - LaTeX table for publications

### 2. Generate Visualizations

Create confidence interval plots from the computed results:

```bash
python tools/plot_ci.py \
    --results_csv "./results/significance_summary.csv" \
    --output_dir "./figures"
```

**Outputs**:
- `figures/ci_plot_{regime}.png` - Individual plots per regime
- `figures/ci_plot_all_regimes.png` - Combined comparison plot
- `figures/forest_plot.png` - Publication-ready forest plot

### 3. Run Unit Tests

Verify the statistical functions work correctly:

```bash
# Using your virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate
python tests/test_significance.py
```

Tests cover:
- Bootstrap confidence interval calculation
- Bootstrap p-value computation
- Cliff's delta effect size
- Holm-Bonferroni correction
- Paired difference computation

## Output Files

### results/significance_summary.csv

Complete statistical results:

| Column | Description |
|--------|-------------|
| `regime` | Model regime (diffraction, reflection) |
| `metric` | Metric name (MAE, LoS_MAE, etc.) |
| `n_scenes` | Number of scenes analyzed |
| `mean_diff` | Mean scene-wise improvement |
| `ci_lo` | 95% CI lower bound |
| `ci_hi` | 95% CI upper bound |
| `p_wilcoxon` | Wilcoxon signed-rank p-value |
| `p_bootstrap` | Bootstrap p-value |
| `p_holm` | Holm-adjusted p-value |
| `cliffs_delta` | Cliff's δ effect size |
| `median_diff` | Median scene-wise improvement |

### reports/significance_report.md

Human-readable markdown report with:
- Methodology description
- Results by regime and metric
- Statistical interpretations
- Effect size classifications

### reports/table_significance.tex

LaTeX table ready for publication with:
- Formatted results
- Significance stars (*, **, ***)
- Professional layout
- Table notes with explanations

### Figures

**ci_plot_{regime}.png**: Errorbar plots showing mean improvements with 95% CI
- Green markers: p < 0.05 (significant)
- Gray markers: p ≥ 0.05 (not significant)
- Red dashed line: H₀ (no difference)

**forest_plot.png**: Publication-ready forest plot showing all results

## Methodology Details

### Paired Scene-wise Analysis

For each regime and metric:
1. Align baseline and flow model results by `sample_id`
2. Compute differences: `d_i = baseline_i - flow_i` (for MAE, wMAPE)
3. For SSIM (higher is better): `d_i = flow_i - baseline_i`
4. Filter NaN/Inf values

### Bootstrap Confidence Intervals

- Resample scenes (not pixels) with replacement
- Compute mean for each resample
- Extract 2.5th and 97.5th percentiles

### Significance Tests

**Wilcoxon Signed-Rank Test**:
- Non-parametric test for paired differences
- H₀: median(d) = 0
- Two-sided alternative

**Bootstrap Test**:
- Resample centered differences under null
- Compare to observed mean
- Two-sided p-value

### Multiple Testing Correction

**Holm-Bonferroni**:
- Controls family-wise error rate
- More powerful than Bonferroni
- Applied across all metric × regime tests

### Effect Size

**Cliff's Delta (δ)**:
- Non-parametric effect size
- Range: -1 to 1
- Interpretation:
  - |δ| < 0.147: negligible
  - 0.147 ≤ |δ| < 0.33: small
  - 0.33 ≤ |δ| < 0.474: medium
  - |δ| ≥ 0.474: large

## Example Workflow

Complete analysis workflow:

```bash
# 1. Create output directories
mkdir -p results figures reports

# 2. Run statistical analysis
python tools/compute_significance.py \
    --results_dir "E:/ba_ergebnisse" \
    --output_dir "./"

# 3. Generate plots
python tools/plot_ci.py

# 4. Check results
cat reports/significance_report.md
```

## Interpreting Results

### Example Result

```
MAE (Diffraction): mean scene-wise improvement = 0.83 dB,
95% CI [0.55, 1.10], p_wilcoxon=0.004 (Holm-adjusted=0.012),
Cliff's δ=0.62 (large effect size).
```

**Interpretation**:
- The Diffraction model improves MAE by 0.83 dB on average per scene
- We're 95% confident the true improvement is between 0.55 and 1.10 dB
- This improvement is statistically significant (p=0.012 < 0.05)
- The effect size is large (δ=0.62), indicating a substantial improvement

### Statistical Significance

- **p < 0.001**: Highly significant (***) - very strong evidence
- **p < 0.01**: Very significant (**) - strong evidence
- **p < 0.05**: Significant (*) - sufficient evidence
- **p ≥ 0.05**: Not significant - insufficient evidence

### Confidence Intervals

- **CI excludes zero**: Evidence of real difference
- **CI includes zero**: Difference may be due to chance
- **Narrow CI**: Precise estimate
- **Wide CI**: Uncertain estimate

## Troubleshooting

### Missing Data

If you get warnings about missing metrics or regimes:
- Check that all CSV files exist in expected locations
- Verify column names match expected format
- Ensure `sample_id` is present in all CSVs

### NaN/Inf Values

The pipeline automatically filters invalid values and reports how many were dropped. If many values are dropped, check your data quality.

### Dependencies

If you encounter import errors:
```bash
pip install --upgrade numpy pandas scipy matplotlib scikit-image
```

## References

- **Bootstrap Methods**: Efron, B., & Tibshirani, R. J. (1994). An introduction to the bootstrap.
- **Wilcoxon Test**: Wilcoxon, F. (1945). Individual comparisons by ranking methods.
- **Holm Correction**: Holm, S. (1979). A simple sequentially rejective multiple test procedure.
- **Cliff's Delta**: Cliff, N. (1993). Dominance statistics: Ordinal analyses to answer ordinal questions.

## Citation

If you use this evaluation pipeline in your research, please cite:

```bibtex
@misc{soundmap_evaluation,
  title={Statistical Evaluation Pipeline for Soundmap Generation},
  author={Your Name},
  year={2025},
  note={Statistical significance analysis with bootstrap confidence intervals}
}
```

---

*Generated with Claude Code - Professional Statistical Evaluation*
