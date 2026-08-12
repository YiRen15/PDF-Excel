#!/bin/bash
DIR=""
cd ""
echo "=================================================="
echo "   正在启动 动态心电图 PDF 转 Excel 基础精简版"
echo "=================================================="
echo "正在启动 Web 服务器..."
/Users/chenyiren/.gemini/antigravity/scratch/pdf_parser/venv/bin/python3.12 app.py
read -p "按回车键退出..."