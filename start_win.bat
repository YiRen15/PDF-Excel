@echo off
title 动态心电图 PDF 转 Excel Web 启动工具

echo ==================================================
echo    动态心电图 PDF 转 Excel 工具 正在启动...
echo ==================================================
echo.

if not exist "app.py" (
    echo.
    echo [错误] 未在当前文件夹找到 app.py 主程序！
    echo --------------------------------------------------
    echo 请务必将 ZIP 压缩包【解压到文件夹后】，再双击运行本脚本！
    echo （不能在压缩包内部直接双击运行）
    echo --------------------------------------------------
    echo.
    pause
    goto :end
)

if exist .active_port del .active_port

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [错误] 未在当前电脑检测到 Python 环境！
    echo --------------------------------------------------
    echo 请先安装 Python: https://www.python.org/downloads/
    echo 安装时请勾选 "Add python.exe to PATH"
    echo --------------------------------------------------
    echo.
    pause
    goto :end
)

echo [提示] 正在启动后台服务引擎...
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

:end