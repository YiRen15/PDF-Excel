@echo off
title 动态心电图 PDF 转 Excel Web 启动工具

echo ==================================================
echo    动态心电图 PDF 转 Excel 工具 正在启动...
echo ==================================================
echo.

if not exist "app.py" (
    echo [错误] 未找到 app.py 文件，请先将 ZIP 压缩包解压后再运行！
    pause
    goto :end
)

if exist .active_port del .active_port

:: 1. 检查 Python 是否可用
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未在当前电脑检测到 Python 环境！
    echo 请先安装 Python: https://www.python.org/downloads/
    echo （安装时务必勾选 "Add python.exe to PATH"）
    pause
    goto :end
)

:: 2. 如果当前文件夹没有 venv 虚拟环境，自动为本台电脑创建专属 venv
if not exist "venv\Scripts\python.exe" (
    echo [提示] 正在在当前电脑创建专属解析环境 (首次配置约需 5-10 秒)...
    if exist venv rmdir /s /q venv >nul 2>&1
    python -m venv venv
    echo [1/2] 专属解析环境创建完成！
    echo [2/2] 正在自动安装核心组件 (Flask/OpenPyXL/PyMuPDF)...
    call venv\Scriptsctivate.bat
    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple flask openpyxl pymupdf pdfplumber
    echo [提示] 所有环境与组件配置完毕！
    echo --------------------------------------------------
)

:: 3. 启动后台解析服务
echo [提示] 正在启动后台服务引擎...
if exist "venv\Scripts\python.exe" (
    start /b venv\Scripts\python.exe app.py
) else (
    start /b python app.py
)

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

:end