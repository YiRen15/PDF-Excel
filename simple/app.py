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
    "batches": [],
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
    batches = []
    all_results = []
    
    try:
        if zip_files:
            for idx, zf in enumerate(zip_files):
                if zf.filename:
                    base_name = os.path.splitext(os.path.basename(zf.filename))[0] or f"压缩包_{idx+1}"
                    zip_sub_dir = os.path.join(temp_dir, f"zip_{idx}")
                    os.makedirs(zip_sub_dir, exist_ok=True)
                    zf_path = os.path.join(zip_sub_dir, zf.filename)
                    zf.save(zf_path)
                    
                    pdf_paths = list(dict.fromkeys(extract_zip(zf_path, zip_sub_dir)))
                    if pdf_paths:
                        results = parse_pdf_batch(pdf_paths)
                        batches.append({
                            'source_name': base_name,
                            'data': results
                        })
                        all_results.extend(results)
        elif files:
            pdf_paths = []
            for file in files:
                if file.filename and file.filename.lower().endswith(".pdf"):
                    save_path = os.path.join(temp_dir, file.filename)
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    file.save(save_path)
                    pdf_paths.append(save_path)
                    
            if pdf_paths:
                pdf_paths = list(dict.fromkeys(pdf_paths))
                results = parse_pdf_batch(pdf_paths)
                batches.append({
                    'source_name': '随访心电记录仪检测记录',
                    'data': results
                })
                all_results.extend(results)
                
        if not all_results:
            return jsonify({"success": False, "error": "未检测到有效的 PDF 报告文件"}), 400
            
        PARSED_CACHE["batches"] = batches
        PARSED_CACHE["data"] = all_results
        PARSED_CACHE["total"] = len(all_results)
        
        sinus_cnt = sum(1 for r in all_results if "1" in str(r.get("ECGORRES", "")).replace("[", "").replace("]", "").split(","))
        afib_cnt = sum(1 for r in all_results if "2" in str(r.get("ECGORRES", "")).replace("[", "").replace("]", "").split(","))
        svt_cnt = sum(1 for r in all_results if "3" in str(r.get("ECGORRES", "")).replace("[", "").replace("]", "").split(","))
        multi_cnt = sum(1 for r in all_results if "," in str(r.get("ECGORRES", "")).replace("[", "").replace("]", ""))
        warning_cnt = sum(1 for r in all_results if r.get("has_warning") or "人工检查" in str(r.get("ECGATBURD")) or "人工检查" in str(r.get("ECGAFBURD")) or (r.get("warnings") and len(r.get("warnings")) > 0))
        
        stats = {
            "total": len(all_results),
            "sinus_1": sinus_cnt,
            "afib_2": afib_cnt,
            "svt_3": svt_cnt,
            "multi": multi_cnt,
            "warning_count": warning_cnt
        }
        
        return jsonify({
            "success": True,
            "total": len(all_results),
            "batch_count": len(batches),
            "stats": stats,
            "data": all_results
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@app.route("/api/download", methods=["GET"])
def download():
    global PARSED_CACHE
    batches = PARSED_CACHE.get("batches", [])
    data_list = PARSED_CACHE.get("data", [])
    if not batches and not data_list:
        return "暂无可导出的解析数据，请先上传 PDF 报告文件。", 400
        
    template_path = os.path.join(BASE_DIR, "随访心电记录仪检测记录_空模板.xlsx")
    if not os.path.exists(template_path):
        template_path = os.path.join(os.path.dirname(BASE_DIR), "随访心电记录仪检测记录_空模板.xlsx")
        
    if len(batches) == 1:
        # 单个 ZIP / 单组批次 -> 直接导出对应 Excel (如 01001.xlsx)
        b = batches[0]
        s_name = b['source_name']
        temp_excel = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        temp_excel.close()
        try:
            write_all_to_excel(b['data'], template_path, temp_excel.name)
            return send_file(
                temp_excel.name,
                as_attachment=True,
                download_name=f"{s_name}.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            return f"生成 Excel 时出错: {e}", 500
    elif len(batches) > 1:
        # 多个 ZIP 批次 -> 为每一个 ZIP 独立生成同名 Excel (如 01001.xlsx, 01002.xlsx)，打成 ZIP 压缩包供一键下载
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        temp_zip.close()
        
        try:
            with zipfile.ZipFile(temp_zip.name, 'w') as zout:
                for b in batches:
                    s_name = b['source_name']
                    t_excel = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                    t_excel.close()
                    try:
                        write_all_to_excel(b['data'], template_path, t_excel.name)
                        zout.write(t_excel.name, arcname=f"{s_name}.xlsx")
                    finally:
                        if os.path.exists(t_excel.name):
                            os.remove(t_excel.name)
                            
            return send_file(
                temp_zip.name,
                as_attachment=True,
                download_name="随访心电记录仪检测记录_批量表格.zip",
                mimetype="application/zip"
            )
        except Exception as e:
            return f"打包生成多表格 ZIP 时出错: {e}", 500
    else:
        temp_excel = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        temp_excel.close()
        try:
            write_all_to_excel(data_list, template_path, temp_excel.name)
            return send_file(
                temp_excel.name,
                as_attachment=True,
                download_name="随访心电记录仪检测记录_合并汇总.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            return f"生成 Excel 时出错: {e}", 500

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
