# Statistical Significance Analysis Report

## Methodology

- **Comparison**: Flow models (Diffraction, Reflection) vs. Baseline (no extra conditions)
- **Metrics**: MAE, LoS_MAE, NLoS_MAE, LoS_wMAPE, NLoS_wMAPE, SSIM
- **Differences**: For MAE/wMAPE: d = baseline - flow (positive = improvement)
- **Differences**: For SSIM: d = flow - baseline (positive = improvement)
- **Confidence Intervals**: 95% bootstrap CI (10,000 resamples)
- **Significance Tests**: Wilcoxon signed-rank (two-sided) + bootstrap test
- **Multiple Testing Correction**: Holm-Bonferroni
- **Effect Size**: Cliff's δ
- **Reproducibility**: Random seed = 42

## Results by Regime

### Diffraction vs. Baseline

**MAE**: Mean scene-wise improvement = 0.0791, 95% CI [-0.0169, 0.1658], median = 0.3925, n=1243 scenes. Wilcoxon p=0.0000, Holm-adjusted p=0.0000 (**statistically significant** (p=0.0000)). Cliff's δ=0.512 (large effect size).

**LoS_MAE**: Mean scene-wise improvement = 1.0496, 95% CI [0.9682, 1.1247], median = 1.1265, n=1243 scenes. Wilcoxon p=0.0000, Holm-adjusted p=0.0000 (**statistically significant** (p=0.0000)). Cliff's δ=0.958 (large effect size).

**NLoS_MAE**: Mean scene-wise degradation = -1.9735, 95% CI [-2.1001, -1.8530], median = -1.4952, n=1243 scenes. Wilcoxon p=0.0000, Holm-adjusted p=0.0000 (**statistically significant** (p=0.0000)). Cliff's δ=-0.899 (large effect size).

**LoS_wMAPE**: Mean scene-wise improvement = 6.4024, 95% CI [6.0706, 6.7159], median = 6.0640, n=1243 scenes. Wilcoxon p=0.0000, Holm-adjusted p=0.0000 (**statistically significant** (p=0.0000)). Cliff's δ=0.958 (large effect size).

**NLoS_wMAPE**: Mean scene-wise degradation = -6.6001, 95% CI [-7.3925, -5.8520], median = -3.1582, n=1243 scenes. Wilcoxon p=0.0000, Holm-adjusted p=0.0000 (**statistically significant** (p=0.0000)). Cliff's δ=-0.648 (large effect size).

**ssim**: Mean scene-wise improvement = 0.0359, 95% CI [0.0336, 0.0381], median = 0.0357, n=1243 scenes. Wilcoxon p=0.0000, Holm-adjusted p=0.0000 (**statistically significant** (p=0.0000)). Cliff's δ=0.765 (large effect size).

### Reflection vs. Baseline

**MAE**: Mean scene-wise degradation = -1.0399, 95% CI [-1.0788, -1.0011], median = -0.9101, n=1244 scenes. Wilcoxon p=0.0000, Holm-adjusted p=0.0000 (**statistically significant** (p=0.0000)). Cliff's δ=-0.969 (large effect size).

**LoS_MAE**: Mean scene-wise degradation = -0.2176, 95% CI [-0.2328, -0.2023], median = -0.2086, n=1244 scenes. Wilcoxon p=0.0000, Holm-adjusted p=0.0000 (**statistically significant** (p=0.0000)). Cliff's δ=-0.609 (large effect size).

**NLoS_MAE**: Mean scene-wise degradation = -2.9900, 95% CI [-3.0870, -2.8955], median = -2.7121, n=1244 scenes. Wilcoxon p=0.0000, Holm-adjusted p=0.0000 (**statistically significant** (p=0.0000)). Cliff's δ=-0.989 (large effect size).

**LoS_wMAPE**: Mean scene-wise degradation = -0.1431, 95% CI [-0.2324, -0.0545], median = -0.1995, n=1244 scenes. Wilcoxon p=0.0000, Holm-adjusted p=0.0000 (**statistically significant** (p=0.0000)). Cliff's δ=-0.119 (negligible effect size).

**NLoS_wMAPE**: Mean scene-wise degradation = -18.1738, 95% CI [-18.7621, -17.6125], median = -16.2280, n=1244 scenes. Wilcoxon p=0.0000, Holm-adjusted p=0.0000 (**statistically significant** (p=0.0000)). Cliff's δ=-0.990 (large effect size).

**ssim**: Mean scene-wise degradation = -0.0723, 95% CI [-0.0749, -0.0697], median = -0.0637, n=1244 scenes. Wilcoxon p=0.0000, Holm-adjusted p=0.0000 (**statistically significant** (p=0.0000)). Cliff's δ=-0.969 (large effect size).

## Interpretation Guide

- **Mean difference (d̄)**: Average improvement per scene. Positive values indicate the flow model performs better.
- **95% CI**: If the confidence interval excludes zero, the difference is likely real.
- **p-value (Holm-adjusted)**: Probability of observing this difference by chance. p<0.05 typically considered significant.
- **Cliff's δ**: Non-parametric effect size. |δ|<0.147: negligible, 0.147-0.33: small, 0.33-0.474: medium, >0.474: large.

---
*Generated with Claude Code - Statistical Evaluation Pipeline*
