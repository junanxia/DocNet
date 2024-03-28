#!/usr/bin/env python3
# coding=utf8
"""
@author: 'junan'
@contact: junan007@163.com
@file: download.py
@time:
@description: 
"""
import os
from flask import Blueprint, request, jsonify, make_response, send_file
from config import Config


download_api = Blueprint('download', __name__, url_prefix='/')


@download_api.route('/struct/download/<string:datename>/<string:postname>/<string:filename>', methods=['GET'])
def look_download(datename, postname, filename):
    # 获取请求地址的 IP
    ip = request.remote_addr
    start_index = filename.find('+') + 1
    end_index = filename.find('.jpg', start_index)
    # 提取子字符串
    input_ip = filename[start_index:end_index]
    if str(ip).replace('.', '-') != input_ip:
        return jsonify({"error": "图片鉴权失败!"}), 500

    file_dir = os.path.join(Config.ROOT_PATH, Config.DOWNLOAD_ROOT, datename)
    file_dir = os.path.join(file_dir, postname)
    if request.method == 'GET':
        if filename is None:
            return jsonify({"error": "图片名称不存在!"}), 500
        else:
            image_data = open(os.path.join(file_dir, '%s' % filename), "rb").read()
            response = make_response(image_data)
            response.headers['Content-Type'] = 'image/png'
            return response
    else:
        return jsonify({"error": "请求方式错误!"}), 500
    

@download_api.route('/logFile/look_file', methods=['GET'])
def look_log_file():
    if request.method == 'GET':
        log_path = os.path.join(Config.ROOT_PATH, 'log_file/app.log')
        if not os.path.exists(log_path):
            return jsonify({"error": "图片名称不存在!"}), 500
        return send_file(log_path, as_attachment=True)
    else:
        return jsonify({"error": "请求方式错误!"}), 500
