@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
if errorlevel 1 goto directory_error

echo ========================================================
echo Agentic Skills MCP Dependency Installer
echo ========================================================
echo Project directory: %CD%
echo.

set "PYTHON_CMD="
where python >nul 2>&1
if errorlevel 1 goto try_py
python --version >nul 2>&1
if errorlevel 1 goto try_py
set "PYTHON_CMD=python"
goto python_found

:try_py
where py >nul 2>&1
if errorlevel 1 goto python_error
py -3 --version >nul 2>&1
if errorlevel 1 goto python_error
set "PYTHON_CMD=py -3"

:python_found
echo Python interpreter:
%PYTHON_CMD% -c "import sys; print(sys.executable); print(sys.version)"
if errorlevel 1 goto python_error

echo.
echo Checking pip...
%PYTHON_CMD% -m pip --version
if errorlevel 1 goto pip_error

echo.
echo Installing dependencies from "%SCRIPT_DIR%requirements.txt"
%PYTHON_CMD% -m pip install -r "%SCRIPT_DIR%requirements.txt"
if errorlevel 1 goto install_error

echo.
echo Checking dependency consistency...
%PYTHON_CMD% -m pip check
if errorlevel 1 echo [WARNING] Unrelated packages in this Python environment may have version conflicts.

echo.
echo ========================================================
echo [SUCCESS] Agentic Skills dependencies are ready.
echo Restart your MCP client to load the updated servers.
echo ========================================================
goto success

:directory_error
echo [ERROR] Could not enter project directory: "%SCRIPT_DIR%"
goto failure

:python_error
echo [ERROR] Python was not found. Install Python 3.10+ and add it to PATH.
goto failure

:pip_error
echo [ERROR] pip was not found in the selected Python installation.
echo Try: %PYTHON_CMD% -m ensurepip --upgrade
goto failure

:install_error
echo [ERROR] Package installation failed. Review the pip output above.
goto failure

:failure
echo.
if /I not "%~1"=="--no-pause" pause
exit /b 1

:success
if /I not "%~1"=="--no-pause" pause
exit /b 0
