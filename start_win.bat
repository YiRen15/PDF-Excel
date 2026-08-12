@echo off
if "%~1"=="RUN" goto :main
cmd /k ""%~f0" RUN"
exit /b

:main
title 动态心电图 PDF 转 Excel Web 启动工具

echo ==================================================
echo    动态心电图 PDF 转 Excel 工具 正在启动...
echo ==================================================
echo.

if not exist "app.py" (
    echo [错误] 未在当前文件夹找到 app.py 文件，请先将 ZIP 压缩包解压后再运行！
    pause
    exit /b
)

if exist .active_port del .active_port

:: 自动寻找电脑上的 Python 路径
set "PY_EXE="
if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if "%PY_EXE%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if "%PY_EXE%"=="" if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if "%PY_EXE%"=="" where python >nul 2>&1 && set "PY_EXE=python"
if "%PY_EXE%"=="" where py >nul 2>&1 && set "PY_EXE=py"

if "%PY_EXE%"=="" (
    echo [错误] 未在当前电脑检测到 Python 环境！
    echo 请先安装 Python: https://www.python.org/downloads/
    echo 安装时务必勾选 "Add python.exe to PATH"
    pause
    exit /b
)

echo [提示] 调起 Python 解释器: "%PY_EXE%"
echo [提示] 正在启动后台服务引擎...
echo --------------------------------------------------

"%PY_EXE%" app.py
if %errorlevel% neq 0 (
    echo.
    echo [提示] 正在为您自动安装必备依赖组件 (Flask/OpenPyXL/PyMuPDF)...
    "%PY_EXE%" -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple flask openpyxl pymupdf pdfplumber
    echo [提示] 组件安装完成，正在重新调起服务...
    "%PY_EXE%" app.py
)

echo.
echo ==================================================
echo    系统已退出。按任意键关闭窗口。
echo ==================================================
echo.

pause