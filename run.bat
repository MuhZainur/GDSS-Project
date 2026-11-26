@echo off
rem Runs Decision Room locally. Double-click this file.
cd /d "%~dp0"

set PYEXE=

rem Find a Python that already has Streamlit 1.50 or newer.
for %%V in (-3.10 -3.11 -3.12 -3.13) do (
  if not defined PYEXE (
    py %%V scripts\check_streamlit.py >nul 2>nul && set "PYEXE=py %%V"
  )
)
if not defined PYEXE (
  python scripts\check_streamlit.py >nul 2>nul && set "PYEXE=python"
)

if not defined PYEXE (
  echo No Python with Streamlit 1.50 or newer was found.
  echo Run once: py -3.10 -m pip install -r requirements.txt
  pause
  exit /b 1
)

echo Using: %PYEXE%
echo Opening http://localhost:8501 ... press Ctrl+C in this window to stop.
%PYEXE% -m streamlit run app/main.py --server.port 8501 --server.address localhost
pause
