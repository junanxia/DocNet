#!/usr/bin/env python3
# coding=utf8
"""
@author: 'junan'
@contact: junan007@163.com
@file:
@time:
@description:
"""
import os

class Config:
    SVR_NAME = "DocNet Web Server"
    VERSION = "1.0.0"
    SVR_PORT = 9990

    # 调试模式开关
    DEBUG = True

    # 文件上传目录
    UPLOAD_ROOT = "data\\upload"
    
    # 文件下载目录
    DOWNLOAD_ROOT = "data\\download"
    
    # 模型文件目录
    MODEL_ROOT = "inference_model"

    ROOT_PATH = os.sep.join(__file__.split(os.sep)[:-1])

