@echo off
title 动态心电图 PDF 转 Excel Web 启动工具

echo ==================================================
echo    动态心电图 PDF 转 Excel 工具 正在启动...
echo ==================================================
echo.

if not exist "app.py" (
    echo [错误] 未找到 app.py 文件，请将本脚本放在项目主文件夹中运行！
    pause
    goto :end
)

if exist .active_port del .active_port

:: 1. 检查当前电脑系统 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未在当前电脑检测到 Python 环境！
    echo 请先安装 Python: https://www.python.org/downloads/
    echo （安装时务必勾选 "Add python.exe to PATH"）
    pause
    goto :end
)

:: 2. 自动诊断旧 venv 是否兼容当前电脑 (防跨电脑路径报错)
if exist "venv\pyvenv.cfg" (
    for /f "tokens=1,* delims==" %%A in (venv\pyvenv.cfg) do (
        if "%%A"=="home " (
            if not exist "%%B" (
                echo [提示] 检测到文件夹中残留有其他人电脑上的旧环境，正在自动清理...
                rmdir /s /q venv >nul 2>&1
            )
        )
        if "%%A"=="home" (
            if not exist "%%B" (
                echo [提示] 检测到文件夹中残留有其他人电脑上的旧环境，正在自动清理...
                rmdir /s /q venv >nul 2>&1
            )
        )
    )
)

:: 3. 如果无 venv 或已清理，自动配置本台电脑的专属环境
if not exist "venv\Scripts\python.exe" (
    echo [提示] 正在为您自动配置本台电脑的专属解析环境 (约需 5-10 秒)...
    if exist venv rmdir /s /q venv >nul 2>&1
    python -m venv venv
    echo [1/2] 专属环境创建完成！
    echo [2/2] 正在自动安装核心组件包 (Flask/OpenPyXL/PyMuPDF)...
    "venv\Scripts\python.exe" -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple flask openpyxl pymupdf pdfplumber
    echo [提示] 组件配置完成！
    echo --------------------------------------------------
)

:: 4. 启动后台解析服务
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