
import os
import uuid
import datetime
import urllib.request
from urllib.parse import urlparse
from config import Config
import requests
import io
import hashlib
import cv2
import base64
import numpy as np


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


def get_uuid_path(root_path):
    uuid_str = str(uuid.uuid1())
    day_str = datetime.datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S-")
    save_path = os.path.join(root_path, os.path.join(day_str, time_str + uuid_str))
    
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    return save_path


# 上传文件获取储存位置
def get_upload_save_path():
    root_path = os.path.join(Config.ROOT_PATH, Config.UPLOAD_ROOT)
    return get_uuid_path(root_path)


# 下载文件获取储存位置
def get_download_save_path():
    root_path = os.path.join(Config.ROOT_PATH, Config.DOWNLOAD_ROOT)
    return get_uuid_path(root_path)


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


def img_to_base64(img):
    img = cv2.imencode('.jpg', img)[1]
    image_code = str(base64.b64encode(img))[2:-1]

    return image_code


def calculate_iou(box1, box2):
    """
    计算两个矩形框的 Intersection over Union (IoU)

    参数：
    - box1: 第一个矩形框的坐标，格式为 [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
    - box2: 第二个矩形框的坐标，格式为 [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]

    返回值：
    - iou: 两个矩形框的 IoU 值
    """

    # 获取矩形框的坐标
    x1, y1 = box1[0]
    x3, y3 = box1[2]

    x5, y5 = box2[0]
    x7, y7 = box2[2]

    # 计算两个矩形框的相交部分的面积
    left = max(x1, x5)
    top = max(y1, y5)
    right = min(x3, x7)
    bottom = min(y3, y7)

    if left > right or top > bottom:
        intersection_area = 0
    else:
        intersection_area = (right - left) * (bottom - top)

    # 计算两个矩形框的并集面积
    box1_area = (x3 - x1) * (y3 - y1)
    box2_area = (x7 - x5) * (y7 - y5)
    union_area = box1_area + box2_area - intersection_area

    # 计算 IoU 值
    iou = intersection_area / union_area

    return iou


# ----------- 函数区 ----------- #
# 四边形顶点排序
# [top-left, top-right, bottom-right, bottom-left]
def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def calculate_area(rectangle):
    """
    计算矩形的面积

    参数：
    - rectangle: 矩形的坐标，格式为 [x_min, y_min, x_max, y_max]

    返回值：
    - area: 矩形的面积
    """

    x1, y1, x2, y2 = rectangle
    width = x2 - x1
    height = y2 - y1
    area = width * height

    return area

def find_largest_rectangle(rectangles):
    """
    找到面积最大的矩形框

    参数：
    - rectangles: 矩形列表，每个矩形的坐标为 [x1, y1, x2, y2]

    返回值：
    - largest_rectangle: 面积最大的矩形框的坐标 [x1, y1, x2, y2]
    """

    largest_area = 0
    largest_rectangle = None

    for rectangle in rectangles:
        area = calculate_area(rectangle)
        if area > largest_area:
            largest_area = area
            largest_rectangle = rectangle

    return largest_rectangle
