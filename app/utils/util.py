
import os
import uuid
import datetime
import urllib.request
from urllib.parse import urlparse
from config import Config
import requests
import io
import hashlib


def md5_encrypt_string(string):
    hash_object = hashlib.md5(string.encode())
    return hash_object.hexdigest()


# 核验数据
def verify_data(form):
    if Config.DEBUG:
        return True, ""
    
    sorted_data = sorted(form.items(), key=lambda x: x[0])
    sorted_dict = dict(sorted_data)
    if "code" not in sorted_dict:
        return False, "入参缺少code"
    org_list = []
    for key, value in sorted_dict.items():
        if key != "code":
            value_copy = value
            if key == 'filePath' and len(value_copy.split('?')) > 1:
                value_copy = value_copy.split('?')[1]
            org_list.append(f"{key}={value_copy}")
    org_str = "&".join(org_list)
    en_str = md5_encrypt_string(org_str)
    final_str = md5_encrypt_string(en_str + "o8ASzhDB89ZsjvsBxK8XDA==")
    if final_str == sorted_dict["code"]:
        return True, ""
    else:
        return False, "数据校验不通过"

# 上传文件获取储存位置
def get_upload_save_path():
    uuid_str = str(uuid.uuid1())
    day_str = datetime.datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S-")
    save_path = os.path.join(
        Config.ROOT_PATH, Config.UPLOAD_ROOT, os.path.join(day_str, time_str + uuid_str)
    )
    
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    return save_path


def save_oss_file(oss_path):
    parsed_url = urlparse(oss_path)
    filename = os.path.basename(parsed_url.path)
    save_path = os.path.join(get_upload_save_path(), filename)
    
    # 解码路径
    decoded_path = urllib.parse.unquote(save_path)  # 解码路径
    urllib.request.urlretrieve(oss_path, decoded_path)
    return decoded_path


def save_download_file(oss_path):
    filename = os.path.basename(oss_path)
    save_path = os.path.join(get_upload_save_path(), filename)
    send_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
        "Connection": "keep-alive",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.8"}
    response = requests.get(oss_path, headers=send_headers)
    bytes_io = io.BytesIO(response.content)
    with open(save_path, mode='wb') as f:
        f.write(bytes_io.getvalue())
    return save_path
