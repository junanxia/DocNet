#!/usr/bin/env python3
# coding=utf8
"""
@author: 'junan'
@contact: junan007@163.com
@file: server.py
@time:
@description:
"""
from gevent import monkey
from gevent import pywsgi
monkey.patch_all()

import signal
import logging
from flask import Flask, request
from flask_cors import CORS
from config import Config
from api.contract import contract_api
from api.upload import upload_api
from api.download import download_api
from api.blueprint import blueprint_api
from api.check import check_api
from api.evaluate import evaluate_api


class MainExitException(Exception):
    """
    主进程异常退出异常类，用于多进程处理时进程间的异常捕获
    """
    @staticmethod
    def sigterm_handler(signum, frame):
        raise MainExitException()
    pass

def create_logger(app):
    LOG_FORMAT = '%(asctime)s %(levelname)s %(pathname)s: %(message)s'
    app.logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler('log_file/app.log')
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)


def create_app():
    app = Flask(__name__)
    CORS(app, supports_credentials=True)

    app.config.from_object(Config)
    create_logger(app)

    # Router
    app.register_blueprint(contract_api)
    app.register_blueprint(upload_api)
    app.register_blueprint(download_api)
    app.register_blueprint(blueprint_api)
    app.register_blueprint(check_api)
    app.register_blueprint(evaluate_api)

    return app


def run():
    app = create_app()

    @app.before_request
    def log_request_info():
        app.logger.info('Request: %s', request.full_path)

    @app.after_request
    def log_response(response):
        app.logger.info('Response: %s', response.status)
        return response
    
    # Web Server
    app.logger.info('%s(%s) started on port %d.' % (Config.SVR_NAME,
                                                Config.VERSION,
                                                Config.SVR_PORT))
    signal.signal(signal.SIGTERM, MainExitException.sigterm_handler)
    server = pywsgi.WSGIServer(('0.0.0.0', Config.SVR_PORT), app)
    try:
        server.serve_forever()
    except MainExitException:
        pass

    app.logger.info('%s(%s) exit.' % (Config.SVR_NAME, Config.VERSION))


if __name__ == '__main__':
    run()
