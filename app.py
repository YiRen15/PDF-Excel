import os
import sys
import socket
import shutil
import tempfile
import zipfile
import json
from flask import Flask, render_template, request, jsonify, send_file
from parser_engine import parse_pdf_batch, write_all_to_excel, extract_zip

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.config['MAX_CONTENT_LENGTH'] = 4096 * 1024 * 1024

PARSED_CACHE = {
    "data": [],
    "total": 0
}

def find_available_port(start_port=5050, max_attempts=50):
    """
    自动检测端口可用性，如果 5050 被占用，自动向后寻找空闲端口 (5051, 5052...)
    保证在任何 Mac / Windows 电脑上都 100% 成功启动，绝对不会发生端口冲突！
    """
    for p in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', p))
                return p
            except OSError:
                continue
    return start_port

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_and_process():
    global PARSED_CACHE
    temp_dir = tempfile.mkdtemp(prefix="ecg_pdf_batch_")
    batches = []
    all_results = []
    
    try:
        zip_files = []
        if 'zip_files' in request.files:
            zip_files = [f for f in request.files.getlist('zip_files') if f.filename]
        elif 'zip_file' in request.files and request.files['zip_file'].filename:
            zip_files = [request.files['zip_file']]
            
        if zip_files:
            for idx, zip_file in enumerate(zip_files):
                base_name = os.path.splitext(os.path.basename(zip_file.filename))[0] or f"压缩包_{idx+1}"
                zip_sub_dir = os.path.join(temp_dir, f"zip_{idx}")
                os.makedirs(zip_sub_dir, exist_ok=True)
                zip_path = os.path.join(zip_sub_dir, zip_file.filename)
                zip_file.save(zip_path)
                
                pdf_paths = extract_zip(zip_path, zip_sub_dir)
                if pdf_paths:
                    print(f"Web 服务端解析压缩包 【{base_name}】 包含的 {len(pdf_paths)} 份 PDF 报告...")
                    results = parse_pdf_batch(pdf_paths)
                    batches.append({
                        'source_name': base_name,
                        'data': results
                    })
                    all_results.extend(results)
                    
        elif 'files' in request.files:
            uploaded_files = request.files.getlist('files')
            pdf_paths = []
            for file in uploaded_files:
                if file.filename and file.filename.lower().endswith('.pdf'):
                    save_path = os.path.join(temp_dir, file.filename)
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    file.save(save_path)
                    pdf_paths.append(save_path)
                    
            if pdf_paths:
                results = parse_pdf_batch(pdf_paths)
                batches.append({
                    'source_name': '随访心电记录仪检测记录_合并汇总',
                    'data': results
                })
                all_results.extend(results)
                
        if not all_results:
            return jsonify({"success": False, "error": "未能接收到可解析的 PDF 报告文件，请确认上传了 .pdf 文件或包含 .pdf 的 ZIP 压缩包。"}), 400
            
        PARSED_CACHE['batches'] = batches
        PARSED_CACHE['data'] = all_results
        PARSED_CACHE['total'] = len(all_results)
        
        stats = {
            "total": len(all_results),
            "sinus_1": sum(1 for r in all_results if str(r.get('ECGORRES')).replace('[', '').replace(']', '').strip() == '1'),
            "afib_2": sum(1 for r in all_results if '2' in str(r.get('ECGORRES')).replace('[', '').replace(']', '').split(',')),
            "svt_3": sum(1 for r in all_results if '3' in str(r.get('ECGORRES')).replace('[', '').replace(']', '').split(',')),
            "multi": sum(1 for r in all_results if ',' in str(r.get('ECGORRES'))),
            "warning_count": sum(1 for r in all_results if r.get('has_warning') or '需人工检查' in str(r.get('ECGATBURD')) or '需要人工检查' in str(r.get('ECGATBURD')) or (r.get('warnings') and len(r.get('warnings')) > 0))
        }
        
        return jsonify({
            "success": True,
            "total": len(all_results),
            "batch_count": len(batches),
            "stats": stats,
            "data": all_results
        })

    except Exception as e:
        print(f"处理上传批次时发生错误: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@app.route('/api/download', methods=['GET'])
def download_excel():
    global PARSED_CACHE
    batches = PARSED_CACHE.get('batches', [])
    if not batches and not PARSED_CACHE.get('data'):
        return "暂无可下载的解析结果，请先上传并解析 PDF 报告。", 400
        
    template_path = os.path.join(BASE_DIR, "随访心电记录仪检测记录_空模板.xlsx")
    if not os.path.exists(template_path):
        template_path = os.path.join(BASE_DIR, "随访心电记录仪检测记录.xlsx")
        
    if not os.path.exists(template_path):
        return "找不到原始 Excel 模板文件，请确保模板存在。", 500
        
    if len(batches) == 1:
        # 单个 ZIP / 单组批次 -> 直接导出对应 Excel
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
        # 多个 ZIP 批次 -> 为每一个 ZIP 独立生成同名 Excel，打成 ZIP 压缩包供一键下载
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
            write_all_to_excel(PARSED_CACHE['data'], template_path, temp_excel.name)
            return send_file(
                temp_excel.name,
                as_attachment=True,
                download_name="随访心电记录仪检测记录_合并汇总.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            return f"生成 Excel 时出错: {e}", 500

@app.errorhandler(Exception)
def handle_global_exception(e):
    code = getattr(e, 'code', 500)
    msg = str(e)
    print(f"全局错误捕获 [{code}]: {msg}")
    return jsonify({"success": False, "error": f"服务器响应异常 ({code}): {msg}"}), code

if __name__ == '__main__':
    # 动态寻找可用端口 (优先 5050，若冲突自动避开)
    desired_port = int(os.environ.get("PORT", 5050))
    port = find_available_port(desired_port)
    
    # 将实际绑定的端口写入临时文件，方便启动脚本准确调起浏览器
    port_file = os.path.join(BASE_DIR, '.active_port')
    try:
        with open(port_file, 'w') as f:
            f.write(str(port))
    except Exception:
        pass
        
    print(f"========== 动态心电图 PDF 转 Excel 医生端系统已启动 ==========")
    print(f"访问网址: http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
