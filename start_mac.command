#!/bin/bash
# 启动心电转换系统 医生端快捷程序

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=================================================="
echo "   正在启动 动态心电图 PDF 转 Excel 智能网页助手"
echo "=================================================="

# 1. 自动清理旧的端口记录文件与本项目残留的历史未关闭进程 (精准匹配，绝不影响任何其他程序)
rm -f .active_port
pkill -9 -f "$DIR/app.py" >/dev/null 2>&1
lsof -ti :5050 | xargs kill -9 >/dev/null 2>&1
sleep 0.5

# 2. 检查电脑是否安装了 python3
if ! command -v python3 &> /dev/null; then
    echo ""
    echo "❌【严重提示】未检测到 Python 运行环境！"
    echo "--------------------------------------------------"
    echo "系统无法运行，请按照以下步骤免费下载并安装 Python："
    echo "1. 打开浏览器下载 Python 官方 Mac 安装包："
    echo "   https://www.python.org/downloads/macos/"
    echo "2. 双击安装下载好的 .pkg 文件，一直点击“继续”直到安装完成。"
    echo "3. 安装完成后，重新双击运行本图标即可！"
    echo "--------------------------------------------------"
    echo ""
    read -p "按下回车键退出..."
    exit 1
fi

# 3. 校验虚拟环境有效性 (改名或迁移后若失效则自动重建)
if [ ! -f "venv/bin/python3" ] || ! venv/bin/python3 -c "import flask, pymupdf" >/dev/null 2>&1; then
    echo "正在初始化运行环境，请稍候..."
    rm -rf venv
    python3 -m venv venv
    venv/bin/pip install --upgrade pip >/dev/null 2>&1
    venv/bin/pip install pdfplumber openpyxl flask pymupdf
fi

echo "正在启动 Web 服务器..."
venv/bin/python3 app.py &
SERVER_PID=$!

# 4. 严格等待 Python 后端 100% 启动成功并能正常响应 HTTP 请求
PORT=5050
for i in {1..60}; do
    sleep 0.2
    if [ -f ".active_port" ]; then
        PORT=$(cat .active_port)
        if curl -s -f "http://127.0.0.1:${PORT}/" >/dev/null 2>&1; then
            break
        fi
    fi
done

# 由 app.py 统一调起 1 个标签页，此处不再重复调起

echo "=================================================="
echo "   系统网页已在浏览器中成功打开 (http://127.0.0.1:${PORT}) !"
echo "   提示：医生使用完毕后直接关闭此终端窗口即可退出服务。"
echo "=================================================="

wait $SERVER_PID
