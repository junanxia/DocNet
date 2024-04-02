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
import fitz
import json
import traceback
import numpy as np
from flask import Blueprint, request, jsonify, current_app
from utils.util import verify_data, save_api_receives, save_to_pdf
from parser.wrapper import parser_wrapper


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


@contract_api.route('/save_contract_file', methods=['POST'])
def save_contract_file():
    try:
        # 储存接收文件
        file, save_path = save_api_receives()
        save_to_pdf(file, save_path)
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
        return jsonify({"path": save_path, 'length': length}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500