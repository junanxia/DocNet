import os
import sys
import traceback
import numpy as np
from flask import Blueprint, request, jsonify, current_app
from utils.util import verify_data
from parser.wrapper import parser_wrapper


blueprint_api = Blueprint('blueprint', __name__, url_prefix='/struct')

@blueprint_api.route("/blue_print_pdf", methods=["POST"])
def blue_print_pdf():
    try:
        # 校验code
        v_flag, message = verify_data(request.form)
        if not v_flag:
            return jsonify({"error": message}), 500
        
        # 获取请求参数
        file_path = request.form.get("savePath")
        index = request.form.get("index")
        if not file_path:
            return jsonify({"error": "请传入文件地址!"}), 500
        if not index:
            return jsonify({"error": "请传入索引!"}), 500
        if isinstance(index, str) and not index.isdigit():
            return jsonify({"error": "结束索引入参错误!"}), 500
        if not os.path.exists(file_path):
            return jsonify({"error": "不存在该文件！"}), 500
        # 获取请求的ip地址
        ip = request.remote_addr
        ip_str = str(ip).replace('.', '-')
        all_res, all_images, all_cut_images = parser_wrapper.blueprint_parser.get_result(file_path, int(index), -1, ip=ip_str)
        return jsonify(
            {
                "all_res": all_res,
                "all_images": all_images,
                "all_cut_images": all_cut_images,
            }
        ), 200
    except Exception as e:
        return jsonify({'error': str(e), "code": 500}), 500
