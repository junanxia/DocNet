import os
import sys
import traceback
import numpy as np
from flask import Blueprint, request, jsonify, current_app
from utils.util import verify_data
from parser.wrapper import parser_wrapper


check_api = Blueprint('quality_check', __name__, url_prefix='/struct')

@check_api.route("/quality_check_pdf", methods=["POST"])
def quality_check_pdf():
    try:
        # 校验code
        v_flag, message = verify_data(request.form)
        if not v_flag:
            return jsonify({"error": message}), 500
        
        # 获取请求参数
        file_path = request.form.get("savePath")
        if not file_path:
            return jsonify({"error": "请传入文件地址!"}), 500
        if not os.path.exists(file_path):
            return jsonify({"error": "不存在该文件！"}), 500
        # 获取请求的ip地址
        ip = request.remote_addr
        ip_str = str(ip).replace('.', '-')
        result, report_number, date_of_commission, unit_of_commission, qz_people, wt_people, images_path = infer_quality_check(
            file_path, INFER_CLASS, ip_str)
        return jsonify(
            {
                "result": np.array(list(result)).tolist(),
                "reportNumber": np.array(list(report_number)).tolist(),
                "dateCommission": np.array(list(date_of_commission)).tolist(),
                "qz_people": np.array(list(qz_people)).tolist(),
                "wt_people": np.array(list(wt_people)).tolist(),
                "images": np.array(list(images_path)).tolist()
            }
        ), 200
    except Exception as e:
        return jsonify({'error': str(e), "code": 500}), 500
