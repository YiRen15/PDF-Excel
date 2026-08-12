@echo off
chcp 936 >nul
title 动态心电图 PDF 转 Excel Web 启动工具

echo ==================================================
echo    动态心电图 PDF 转 Excel 工具 正在启动...
echo ==================================================
echo.

if exist .active_port del .active_port

:: 1. 检查当前电脑是否安装了系统 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未在当前电脑检测到 Python 环境！
    echo --------------------------------------------------
    echo 请先安装 Python:
    echo 1. 下载地址: https://www.python.org/downloads/
    echo 2. 安装时请务必勾选 "Add python.exe to PATH"
    echo 3. 安装完成后双击本脚本即可自动启动。
    echo --------------------------------------------------
    echo.
    pause
    exit /b 1
)

:: 2. 检测并确保 Flask / OpenPyXL / PyMuPDF 依赖已安装
echo [提示] 正在检查后台解析组件 (Flask / OpenPyXL / PyMuPDF)...
python -c "import flask, openpyxl, fitz, pdfplumber" >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 检测到当前电脑缺失解析组件，正在自动下载安装 (约需 5-10 秒)...
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple flask openpyxl pymupdf pdfplumber
    echo [提示] 依赖组件安装完成！
    echo --------------------------------------------------
)

:: 3. 启动 Flask Web 后台引擎
echo [提示] 正在启动后台解析引擎...
start /b python app.py

timeout /t 3 /nobreak >nul

set PORT=5050
if exist .active_port (
    set /p PORT=<.active_port
)

start http://127.0.0.1:%PORT%

echo.
echo ==================================================
echo    系统已成功启动！
echo    浏览器已自动打开网页: http://127.0.0.1:%PORT%
echo    提示: 使用完毕后直接关闭本窗口即可退出程序。
echo ==================================================
echo.

pause