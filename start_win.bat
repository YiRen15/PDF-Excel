@echo off
title 动态心电图 PDF 转 Excel Web 工具

echo ==================================================
echo    动态心电图 PDF 转 Excel 工具 正在启动...
echo ==================================================
echo.

if exist .active_port del .active_port

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python 环境！
    echo --------------------------------------------------
    echo 请先下载并安装 Python:
    echo 1. 官网下载地址: https://www.python.org/downloads/
    echo 2. 安装时请务必勾选 "Add Python.exe to PATH"
    echo 3. 安装完成后重新双击本脚本即可。
    echo --------------------------------------------------
    echo.
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo [提示] 首次运行正在自动初始化 Python 运行环境，请稍候...
    if exist venv rmdir /s /q venv
    python -m venv venv
    echo [1/2] 虚拟环境创建完成，正在安装依赖组件...
    call venv\Scripts\activate.bat
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pdfplumber openpyxl flask pymupdf
    echo [2/2] 依赖组件安装完成！
    echo --------------------------------------------------
)

echo [提示] 正在启动后台解析引擎...
start /b venv\Scripts\python.exe app.py

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
echo    提示：使用完毕后直接关闭本窗口即可退出程序。
echo ==================================================
echo.

pause
