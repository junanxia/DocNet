
import json
import sys
import traceback
import fitz
import datetime
from flask import Blueprint, request, jsonify, current_app
from utils.util import verify_data, save_oss_file, save_download_file, md5_encrypt_string, save_api_receives, save_to_pdf

upload_api = Blueprint('upload', __name__, url_prefix='/struct')


@upload_api.route('/upload_contract_pdf', methods=['POST'])
def upload_contract_pdf():
    try:
        # 校验code
        v_flag, message = verify_data(request.form)
        if not v_flag:
            return jsonify({"error": message}), 500
        # 获取请求参数
        oss_path = request.form.get("filePath")
        if not oss_path:
            return jsonify({"error": "请传入文件地址!"}), 500
        print('oss_path:', oss_path)
        save_path = save_oss_file(oss_path)
        
        # 获取pdf页数
        doc_contract = fitz.open(save_path)
        length = len(doc_contract)
        # 创建对应的json文件夹
        data = {
            'cover_index_list': [],
            'directory_index_list': [],
            'protocol_start': -1,
            'general_start': -1,
            'special_start': -1,
            'all_result_texts': [None] * length,
            'all_result_boxes': [None] * length,
            'all_result_scores': [None] * length,
            'cover_uie': None,
            'protocol_uie': None,
            'general_uie': None,
            'special_uie': None
        }
        
        # 指定文件路径
        json_path = save_path.replace('.pdf', '.json')
        json_str = json.dumps(data)
        # 创建并写入 JSON 文件
        with open(json_path, 'w', encoding="utf-8") as f:
            f.write(json_str)
        return jsonify(
            {
                "save_path": str(save_path),
                "length": str(length),
            }
        ), 200
    except Exception as e:
        current_app.logger.info('error:' + str(e))
        traceback.print_exc(file=sys.stdout)
        return jsonify({'error': str(e), "code": 500}), 500


@upload_api.route("/upload_common_pdf", methods=["POST"])
def upload_common_pdf():
    try:
        # 校验code
        v_flag, message = verify_data(request.form)
        if not v_flag:
            return jsonify({"error": message}), 500
        # 获取请求参数
        oss_path = request.form.get("filePath")
        if not oss_path:
            return jsonify({"error": "请传入文件地址!"}), 500
        save_path = save_oss_file(oss_path)
        # 获取pdf页数
        doc_contract = fitz.open(save_path)
        length = len(doc_contract)
        return jsonify(
            {
                "save_path": str(save_path),
                "length": str(length),
            }
        ), 200
    except Exception as e:
        current_app.logger.info('error:' + str(e))
        traceback.print_exc(file=sys.stdout)

        return jsonify({'error': str(e), "code": 500}), 500


@upload_api.route("/upload_common_pdf_download", methods=["POST"])
def upload_common_pdf_download():
    try:
        # 校验code
        v_flag, message = verify_data(request.form)
        if not v_flag:
            return jsonify({"error": message}), 500
        # 获取请求参数
        oss_path = request.form.get("downloadPath")
        if not oss_path:
            return jsonify({"error": "请传入文件地址!"}), 500
        save_path = save_download_file(oss_path)
        # 获取pdf页数
        doc_contract = fitz.open(save_path)
        length = len(doc_contract)
        return jsonify(
            {
                "save_path": str(save_path),
                "length": str(length),
            }
        ), 200
    except Exception as e:
        current_app.logger.info('error:' + str(e))
        traceback.print_exc(file=sys.stdout)

        return jsonify({'error': str(e), "code": 500}), 500
    

@upload_api.route('/save_common_file', methods=['POST'])
def save_common_file():
    try:
        # 储存接收文件
        file, save_path = save_api_receives()
        save_to_pdf(file, save_path)
        # 获取pdf页数
        doc_contract = fitz.open(save_path)
        length = len(doc_contract)
        return jsonify({"path": save_path, 'length': length}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@upload_api.route('/checkConnect', methods=['POST'])
def checkConnect():
    try:
        # 获取请求参数
        if request.content_type.startswith('application/json'):
            code = request.json.get('code')
        elif request.content_type.startswith('multipart/form-data'):
            code = request.form.get('code')
        else:
            code = request.values.get("code")
        if not code:
            return jsonify({'error': '请传入code！', 'code': 500}), 500
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        en_str = md5_encrypt_string(current_time)
        final_str = md5_encrypt_string(en_str + "o8ASzhDB89ZsjvsBxK8XDA==")
        if final_str == code:
            return jsonify({"success": True, 'code': 200}), 200
        else:
            return jsonify({"success": False, 'code': 200}), 200
    except Exception as e:
        return jsonify({'error': str(e), 'code': 500}), 500

