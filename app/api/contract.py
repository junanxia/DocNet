#!/usr/bin/env python3
# coding=utf8
"""
@author: 'junan'
@contact: junan007@163.com
@file: contract.py
@time:
@description: 合同识别接口定义
"""
import os
import sys
import traceback
import numpy as np
from flask import Blueprint, request, jsonify, current_app
from utils.util import verify_data
from parser.parser_wrapper import parser_wrapper


contract_api = Blueprint('contract', __name__, url_prefix='/struct')


@contract_api.route('/contract_in_pdf_v14_ocr', methods=['POST'])
def contract_in_pdf_v14_ocr():
    try:
        # 校验code
        v_flag, message = verify_data(request.form)
        if not v_flag:
            return jsonify({"error": message}), 500
        
        # 获取请求参数
        start_index = request.form.get("startIndex")
        end_index = request.form.get("endIndex")
        file_path = request.form.get("savePath")

        # 请求参数校验
        if not start_index:
            return jsonify({"error": "请传入起始索引!"}), 500
        if not end_index:
            return jsonify({"error": "请传入结束索引!"}), 500
        if not file_path:
            return jsonify({"error": "请传入文件地址!"}), 500
        if isinstance(start_index, str) and not start_index.isdigit():
            return jsonify({"error": "起始索引入参错误!"}), 500
        if isinstance(end_index, str) and not end_index.isdigit():
            return jsonify({"error": "结束索引入参错误!"}), 500
        if not os.path.exists(file_path):
            return jsonify({"error": "不存在该文件！"}), 500
        if int(start_index) > int(end_index):
            return jsonify({"error": "起始索引不应该大于结束索引！"}), 500
        
        # 获取请求的ip地址
        ip = request.remote_addr
        ip_str = str(ip).replace('.', '-')
        all_result_boxes, all_result_texts, all_result_scores, image_path_list, cover_uie, protocol_uie, special_uie = parser_wrapper.contract_parser.get_result(file_path, int(start_index), int(end_index), ip=ip_str)

        return jsonify(
            {
                "res_boxes": all_result_boxes, # np.array(list(all_result_boxes)).tolist(),
                "res_txts": all_result_texts, #np.array(list(all_result_texts)).tolist(),
                "res_scores": all_result_scores, #np.array(list(all_result_scores)).tolist(),
                "image_list": np.array(list(image_path_list)).tolist(),
                "cover_uie": cover_uie,
                "protocol_uie": protocol_uie,
                "special_uie": special_uie
            }
        ), 200
    except Exception as e:
        current_app.logger.info('error:' + str(e))
        traceback.print_exc(file=sys.stdout)
        
        return jsonify({'error': str(e), "code": 500}), 500
