@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv
  if errorlevel 1 goto fail
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto fail
if not exist data\processed\customer_predictions.csv (
  .venv\Scripts\python.exe -m src.pipeline
  if errorlevel 1 goto fail
)
.venv\Scripts\python.exe powerbi\build_project.py
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m streamlit run app.py
goto :eof
:fail
echo Setup failed. Read the error above. Python 3.12 is required.
pause
exit /b 1
