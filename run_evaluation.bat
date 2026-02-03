@echo off
chcp 65001 >nul
REM Statistical Evaluation Pipeline - Quick Start Script
REM Run complete statistical analysis and generate all outputs

echo ================================================================================
echo Statistical Evaluation Pipeline for Soundmap Generation
echo ================================================================================
echo.

REM Set paths (modify these if needed)
set RESULTS_DIR=E:\ba_ergebnisse
set OUTPUT_DIR=.

REM Create output directories
echo Creating output directories...
if not exist "results" mkdir results
if not exist "figures" mkdir figures
if not exist "reports" mkdir reports
echo.

REM Step 1: Run statistical significance analysis
echo ================================================================================
echo Step 1: Computing Statistical Significance
echo ================================================================================
echo.
python tools\compute_significance.py ^
    --results_dir "%RESULTS_DIR%" ^
    --output_dir "%OUTPUT_DIR%" ^
    --regimes baseline diffraction reflection ^
    --metrics MAE LoS_MAE NLoS_MAE LoS_wMAPE NLoS_wMAPE ssim

if errorlevel 1 (
    echo.
    echo ERROR: Significance computation failed!
    echo Please check that:
    echo   1. Python environment is activated
    echo   2. All dependencies are installed: pip install -r requirements.txt
    echo   3. Results directory exists: %RESULTS_DIR%
    echo   4. All required CSV files are present
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo Step 2: Generating Visualizations
echo ================================================================================
echo.
python tools\plot_ci.py ^
    --results_csv ".\results\significance_summary.csv" ^
    --output_dir ".\figures"

if errorlevel 1 (
    echo.
    echo ERROR: Plotting failed!
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo Pipeline Complete!
echo ================================================================================
echo.
echo Generated files:
echo   - results\significance_summary.csv
echo   - reports\significance_report.md
echo   - reports\table_significance.tex
echo   - figures\ci_plot_*.png
echo   - figures\forest_plot.png
echo.
echo Next steps:
echo   1. Review the Markdown report: reports\significance_report.md
echo   2. View the plots in the figures\ directory
echo   3. Use the LaTeX table in your paper: reports\table_significance.tex
echo.
pause
