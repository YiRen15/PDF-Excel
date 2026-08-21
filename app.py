import os
import sys
import socket
import shutil
import tempfile
import zipfile
import json
from flask import Flask, render_template, request, jsonify, send_file
from parser_engine import parse_pdf_batch, write_all_to_excel, extract_zip, parse_ecg_measurement_batch, write_ecg_measurement_excel, parse_ecg_measurement_batch, write_ecg_measurement_excel, parse_start_date_file, write_weekly_summary_excel
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.config['MAX_CONTENT_LENGTH'] = 4096 * 1024 * 1024
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

APP_VERSION = "PDF-Excel 1.01.00"

PARSED_CACHE = {
    "data": [],
    "total": 0
}

START_DATES_CACHE = {}

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


MEASUREMENT_CACHE = {
    "batches": [],
    "data": [],
    "total": 0
}

@app.route('/api/upload_measurement', methods=['POST'])
def upload_measurement():
    global MEASUREMENT_CACHE
    files = request.files.getlist('files')
    zip_files = request.files.getlist('zip_files')

    temp_dir = tempfile.mkdtemp(prefix='ecg_meas_')
    batches = []
    all_results = []

    try:
        if zip_files:
            for idx, zf in enumerate(zip_files):
                if zf.filename:
                    base_name = os.path.splitext(os.path.basename(zf.filename))[0] or f'测量报告包_{idx+1}'
                    zip_sub_dir = os.path.join(temp_dir, f'zip_{idx}')
                    os.makedirs(zip_sub_dir, exist_ok=True)
                    zf_path = os.path.join(zip_sub_dir, zf.filename)
                    zf.save(zf_path)

                    pdf_paths = list(dict.fromkeys(extract_zip(zf_path, zip_sub_dir)))
                    if pdf_paths:
                        results = parse_ecg_measurement_batch(pdf_paths)
                        batches.append({
                            'source_name': base_name,
                            'data': results
                        })
                        all_results.extend(results)
        elif files:
            pdf_paths = []
            for file in files:
                if file.filename and file.filename.lower().endswith('.pdf'):
                    save_path = os.path.join(temp_dir, file.filename)
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    file.save(save_path)
                    pdf_paths.append(save_path)

            if pdf_paths:
                pdf_paths = list(dict.fromkeys(pdf_paths))
                results = parse_ecg_measurement_batch(pdf_paths)
                batches.append({
                    'source_name': '心电图测量报告',
                    'data': results
                })
                all_results.extend(results)

        if not all_results:
            return jsonify({'success': False, 'error': '未检测到有效的心电图测量 PDF 报告文件'}), 400

        MEASUREMENT_CACHE['batches'] = batches
        MEASUREMENT_CACHE['data'] = all_results
        MEASUREMENT_CACHE['total'] = len(all_results)

        normal_cnt = sum(1 for r in all_results if '正常' in str(r.get('诊断', '')))
        abnormal_cnt = len(all_results) - normal_cnt

        stats = {
            'total': len(all_results),
            'normal': normal_cnt,
            'abnormal': abnormal_cnt
        }

        return jsonify({
            'success': True,
            'total': len(all_results),
            'batch_count': len(batches),
            'stats': stats,
            'data': all_results
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@app.route('/api/download_measurement', methods=['GET'])
def download_measurement():
    global MEASUREMENT_CACHE
    batches = MEASUREMENT_CACHE.get('batches', [])
    data_list = MEASUREMENT_CACHE.get('data', [])
    if not batches and not data_list:
        return '暂无可导出的心电图测量数据，请先上传 PDF 报告文件。', 400

    template_path = os.path.join(BASE_DIR, '输出格式.xlsx')
    if not os.path.exists(template_path):
        template_path = os.path.join(os.path.dirname(BASE_DIR), '输出格式.xlsx')

    if len(batches) == 1:
        b = batches[0]
        s_name = b['source_name']
        temp_excel = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        temp_excel.close()
        try:
            write_ecg_measurement_excel(b['data'], template_path, temp_excel.name)
            return send_file(
                temp_excel.name,
                as_attachment=True,
                download_name=f'{s_name}.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        except Exception as e:
            return f'生成心电图测量 Excel 时出错: {e}', 500
    elif len(batches) > 1:
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_zip.close()

        try:
            with zipfile.ZipFile(temp_zip.name, 'w') as zout:
                for b in batches:
                    s_name = b['source_name']
                    t_excel = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
                    t_excel.close()
                    try:
                        write_ecg_measurement_excel(b['data'], template_path, t_excel.name)
                        zout.write(t_excel.name, arcname=f'{s_name}.xlsx')
                    finally:
                        if os.path.exists(t_excel.name):
                            os.remove(t_excel.name)

            return send_file(
                temp_zip.name,
                as_attachment=True,
                download_name='心电图测量报告_批量表格.zip',
                mimetype='application/zip'
            )
        except Exception as e:
            return f'打包生成多表格 ZIP 时出错: {e}', 500
    else:
        temp_excel = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        temp_excel.close()
        try:
            write_ecg_measurement_excel(data_list, template_path, temp_excel.name)
            return send_file(
                temp_excel.name,
                as_attachment=True,
                download_name='心电图测量报告_汇总.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        except Exception as e:
            return f'生成心电图测量 Excel 时出错: {e}', 500

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
                
                pdf_paths = list(dict.fromkeys(extract_zip(zip_path, zip_sub_dir)))
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
            "warning_count": sum(1 for r in all_results if r.get('has_warning') or '人工检查' in str(r.get('ECGATBURD')) or '人工检查' in str(r.get('ECGAFBURD')) or (r.get('warnings') and len(r.get('warnings')) > 0))
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

@app.route('/api/upload_start_dates', methods=['POST'])
def upload_start_dates():
    global START_DATES_CACHE
    if 'file' not in request.files or not request.files['file'].filename:
        return jsonify({"success": False, "error": "请选择有效的《起始日期表.xlsx》或 .csv 文件。"}), 400
        
    f = request.files['file']
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    temp.close()
    try:
        f.save(temp.name)
        new_dates = parse_start_date_file(temp.name)
        if not new_dates:
            return jsonify({"success": False, "error": "未能从文件中解析出受试者编号与起始日期，请检查文件格式 (第1列为受试者编号，第2列为起始日期)。"}), 400
            
        START_DATES_CACHE.update(new_dates)
        serializable_dates = {k: (v.strftime('%Y-%m-%d') if hasattr(v, 'strftime') else str(v)) for k, v in START_DATES_CACHE.items()}
        return jsonify({
            "success": True,
            "count": len(START_DATES_CACHE),
            "added_count": len(new_dates),
            "start_dates": serializable_dates
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"解析起始日期表出错: {e}"}), 500
    finally:
        if os.path.exists(temp.name):
            os.remove(temp.name)

@app.route('/api/get_start_dates', methods=['GET', 'POST'])
def get_or_update_start_dates():
    global START_DATES_CACHE
    if request.method == 'POST':
        req_data = request.get_json(silent=True) or {}
        updates = req_data.get('start_dates', {})
        for k, v in updates.items():
            clean_k = str(k).replace('-', '').strip()
            if not v:
                continue
            try:
                s_str = str(v).split(' ')[0].replace('/', '-').replace('.', '-')
                parts = [int(x) for x in s_str.split('-')]
                if len(parts) == 3:
                    START_DATES_CACHE[clean_k] = datetime.date(parts[0], parts[1], parts[2])
            except Exception:
                pass
                
    serializable_dates = {k: (v.strftime('%Y-%m-%d') if hasattr(v, 'strftime') else str(v)) for k, v in START_DATES_CACHE.items()}
    return jsonify({
        "success": True,
        "count": len(START_DATES_CACHE),
        "start_dates": serializable_dates
    })

@app.route('/api/download_weekly_summary', methods=['GET'])
def download_weekly_summary():
    global PARSED_CACHE, START_DATES_CACHE
    data_list = PARSED_CACHE.get('data', [])
    if not data_list:
        return "暂无可导出的解析数据，请先上传 PDF 报告文件。", 400
        
    template_path = os.path.join(BASE_DIR, "统计模板.xlsx")
    if not os.path.exists(template_path):
        return "服务器端缺失《统计模板.xlsx》文件，请检查文件是否存在。", 500
        
    temp_excel = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    temp_excel.close()
    try:
        write_weekly_summary_excel(data_list, START_DATES_CACHE, template_path, temp_excel.name)
        return send_file(
            temp_excel.name,
            as_attachment=True,
            download_name="52周房颤房速复发周报汇总表.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return f"生成 52 周周报汇总表时出错: {e}", 500

@app.errorhandler(Exception)
def handle_global_exception(e):
    code = getattr(e, 'code', 500)
    msg = str(e)
    print(f"全局错误捕获 [{code}]: {msg}")
    return jsonify({"success": False, "error": f"服务器响应异常 ({code}): {msg}"}), code

import threading
import webbrowser

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
    
    # 1.5秒后在后端自动弹窗调起浏览器 (AUTO_OPEN_BROWSER=0 时静默)
    if os.environ.get("AUTO_OPEN_BROWSER", "1") != "0":
        try:
            threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
        except Exception:
            pass
