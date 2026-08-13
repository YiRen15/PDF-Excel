import os
import sys
import socket
import shutil
import tempfile
import zipfile
import json
import webbrowser
import threading
from flask import Flask, render_template, request, jsonify, send_file
from parser_engine import parse_pdf_batch, write_all_to_excel, extract_zip

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.config["MAX_CONTENT_LENGTH"] = 4096 * 1024 * 1024

APP_VERSION = "PDF-Excel 1.01.00-simple"

PARSED_CACHE = {
    "data": [],
    "total": 0
}

def find_available_port(start_port=5050, max_attempts=50):
    for p in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", p))
                return p
            except OSError:
                continue
    return start_port


@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/")
def index():
    return render_template("index.html", version=APP_VERSION)

@app.route("/api/upload", methods=["POST"])
def upload():
    global PARSED_CACHE
    files = request.files.getlist("files")
    zip_files = request.files.getlist("zip_files")
    
    temp_dir = tempfile.mkdtemp()
    pdf_paths = []
    
    try:
        if zip_files:
            for idx, zf in enumerate(zip_files):
                if zf.filename:
                    zip_sub_dir = os.path.join(temp_dir, f"zip_{idx}")
                    os.makedirs(zip_sub_dir, exist_ok=True)
                    zf_path = os.path.join(zip_sub_dir, zf.filename)
                    zf.save(zf_path)
                    extracted = extract_zip(zf_path, zip_sub_dir)
                    pdf_paths.extend(extracted)
            pdf_paths = list(dict.fromkeys(pdf_paths))
        elif files:
            for f in files:
                if f.filename and f.filename.lower().endswith(".pdf"):
                    f_path = os.path.join(temp_dir, f.filename)
                    f.save(f_path)
                    pdf_paths.append(f_path)
                    
        if not pdf_paths:
            return jsonify({"success": False, "error": "未检测到有效的 PDF 报告文件"}), 400
            
        parsed_results = parse_pdf_batch(pdf_paths)
        PARSED_CACHE["data"] = parsed_results
        PARSED_CACHE["total"] = len(parsed_results)
        
        sinus_cnt = sum(1 for r in parsed_results if "1" in str(r.get("ECGORRES", "")).replace("[", "").replace("]", "").split(","))
        afib_cnt = sum(1 for r in parsed_results if "2" in str(r.get("ECGORRES", "")).replace("[", "").replace("]", "").split(","))
        svt_cnt = sum(1 for r in parsed_results if "3" in str(r.get("ECGORRES", "")).replace("[", "").replace("]", "").split(","))
        multi_cnt = sum(1 for r in parsed_results if "," in str(r.get("ECGORRES", "")).replace("[", "").replace("]", ""))
        warning_cnt = sum(1 for r in parsed_results if r.get("has_warning") or (r.get("warnings") and len(r.get("warnings")) > 0))
        
        stats = {
            "total": len(parsed_results),
            "sinus_1": sinus_cnt,
            "afib_2": afib_cnt,
            "svt_3": svt_cnt,
            "multi": multi_cnt,
            "warning_count": warning_cnt
        }
        
        return jsonify({
            "success": True,
            "total": len(parsed_results),
            "stats": stats,
            "data": parsed_results
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@app.route("/api/download", methods=["GET"])
def download():
    global PARSED_CACHE
    data_list = PARSED_CACHE.get("data", [])
    if not data_list:
        return "暂无可导出的解析数据，请先上传 PDF 报告文件。", 400
        
    template_path = os.path.join(BASE_DIR, "随访心电记录仪检测记录_空模板.xlsx")
    if not os.path.exists(template_path):
        template_path = os.path.join(os.path.dirname(BASE_DIR), "随访心电记录仪检测记录_空模板.xlsx")
        
    temp_excel = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    temp_excel.close()
    try:
        write_all_to_excel(data_list, template_path, temp_excel.name)
        return send_file(
            temp_excel.name,
            as_attachment=True,
            download_name="随访心电记录仪检测记录.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return f"生成 Excel 导出文件出错: {e}", 500

if __name__ == "__main__":
    port = find_available_port(5050)
    active_port_file = os.path.join(BASE_DIR, ".active_port")
    with open(active_port_file, "w") as f:
        f.write(str(port))
        
    print(f"========== 动态心电图 PDF 转 Excel 医生端系统 ({APP_VERSION}) ==========")
    print(f"访问网址: http://127.0.0.1:{port}")
    print("提示: 启动成功后请保留本命令行窗口，不要关闭。")
    print("===============================================================")
    
    threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    app.run(host="0.0.0.0", port=port, debug=False)