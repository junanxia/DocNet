# ------------------------ 头文件 ------------------------ #
import cv2
import numpy as np

# ----------- 配置文件 ----------- #
# 表格样式调参
# hmin_dis 值越大，检测到的横线越多
# vmin_dis 值越大，检测到的竖线越多
# cell_x_dis 最小单元格表格的长度x
# cell_y_dis 最小单元格表格的高度y
style_config = {
    'normal': {
        'hmin_dis': 10,
        'vmin_dis': 10,
        'cellx_dis': 10,
        'celly_dis': 10,
        'min_area': 2000,
        'eroded_kernel': (0, 0),
        'dilate_kernel': (1, 1)
    },
    'fj2': {
        'hmin_dis': 15,
        'vmin_dis': 11,
        'cellx_dis': 5,
        'celly_dis': 10,
        'min_area': 100,
        'eroded_kernel': (0, 0),
        'dilate_kernel': (1, 1)
    },
    'fj4': {
        'hmin_dis': 20,
        'vmin_dis': 40,
        'cellx_dis': 1,
        'celly_dis': 1,
        'min_area': 10,
        'eroded_kernel': (0, 0),
        'dilate_kernel': (1, 1)
    },
    'fj5': {
        'hmin_dis': 20,
        'vmin_dis': 40,
        'cellx_dis': 10,
        'celly_dis': 10,
        'min_area': 100,
        'eroded_kernel': (0, 0),
        'dilate_kernel': (1, 1)
    }
}


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


# 获取表格样式配置
def get_config_json(style_name):
    # 此处添加样式识别逻辑代码
    if style_name == "" or style_name not in style_config:
        return style_config['normal']
    else:
        return style_config[style_name]


def angle_cos(p0, p1, p2):
    d1, d2 = (p0 - p1).astype('float'), (p2 - p1).astype('float')
    return abs(np.dot(d1, d2) / np.sqrt(np.dot(d1, d1) * np.dot(d2, d2)))


# 寻找矩形单元格
def find_squares(bin, img, config):
    # 设置putText函数字体
    squares = []
    contours, _hierarchy = cv2.findContours(bin, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # print("轮廓数量：%d" % len(contours))
    index = 0
    # 轮廓遍历
    for index_obj in range(len(contours)):
        cnt = contours[index_obj]
        cnt_len = cv2.arcLength(cnt, True)  # 计算轮廓周长
        cnt = cv2.approxPolyDP(cnt, 0.02 * cnt_len, True)  # 多边形逼近
        # 条件判断逼近边的数量是否为4，轮廓面积是否大于1000，检测轮廓是否为凸的
        # if len(cnt) == 4 and cv2.contourArea(cnt) > 1000 and cv2.isContourConvex(cnt):
        if len(cnt) == 4 and cv2.contourArea(cnt) > config['min_area'] and cv2.isContourConvex(cnt) and \
                _hierarchy[0][index_obj][
                    3] != -1:
            # if len(cnt) == 4 and cv2.isContourConvex(cnt):
            # print("检测到轮廓", cnt)
            M = cv2.moments(cnt)  # 计算轮廓的矩
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])  # 轮廓重心

            cnt = cnt.reshape(-1, 2)
            max_cos = np.max([angle_cos(cnt[i], cnt[(i + 1) % 4], cnt[(i + 2) % 4]) for i in range(4)])
            # 只检测矩形（cos90° = 0）
            if max_cos < 0.1:
                # 检测四边形（不限定角度范围）
                # if True:
                index = index + 1
                cv2.putText(img, ("#%d" % index), (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
                squares.append(cnt)
    return squares, img


# 表格图片结构化
def parse_pic_to_struct(src, config):
    # # 要计算一下，然后每个文档版面设置不一样的参数
    hmin_dis = config['hmin_dis']
    vmin_dis = config['vmin_dis']
    cellx_dis = config['cellx_dis']
    celly_dis = config['celly_dis']

    # 灰度图片
    gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
    # 二值化 ADAPTIVE_THRESH_MEAN_C ADAPTIVE_THRESH_GAUSSIAN_C/THRESH_BINARY  THRESH_BINARY_INV
    binary = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, -2)
    # 模糊处理 腐蚀（减少）和膨胀（变粗）
    kernel = np.ones(config['dilate_kernel'], np.uint8)
    binary = cv2.dilate(binary, kernel, iterations=1)

    # 获取所有横竖线网格
    rows, cols = binary.shape

    # 获取横线 先腐蚀再膨胀
    scale = hmin_dis
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (cols // scale, 1))
    eroded = cv2.erode(binary, kernel, iterations=1)
    dilated_col = cv2.dilate(eroded, kernel, iterations=1)

    # 识别竖线 先腐蚀再膨胀
    scale = vmin_dis
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, rows // scale))
    eroded = cv2.erode(binary, kernel, iterations=1)
    dilated_row = cv2.dilate(eroded, kernel, iterations=1)

    # 标识交点
    bitwise_and = cv2.bitwise_and(dilated_col, dilated_row)

    # 标识表格
    merge = cv2.add(dilated_col, dilated_row)
    # 模糊处理 腐蚀和膨胀
    kernel_rec = np.ones((3, 3), np.uint8)
    merge = cv2.dilate(merge, kernel_rec, iterations=1)

    # 识别黑白图中的白色交叉点，将横纵坐标取出
    ys, xs = np.where(bitwise_and > 0)
    if len(ys) == 0 and len(xs) == 0:
        return [], None

    # 纵坐标
    y_point_arr = []
    # 横坐标
    x_point_arr = []
    # 通过排序，获取跳变的x和y的值，说明是交点，否则交点会有好多像素值值相近，我只取相近值的最后一点
    # 这个10的跳变不是固定的，根据不同的图片会有微调，基本上为单元格表格的高度（y坐标跳变）和长度（x坐标跳变）
    i = 0
    sort_x_point = np.sort(xs)
    for i in range(len(sort_x_point) - 1):
        if sort_x_point[i + 1] - sort_x_point[i] > cellx_dis:
            x_point_arr.append(sort_x_point[i])
        i = i + 1
    x_point_arr.append(sort_x_point[i])  # 要将最后一个点加入

    i = 0
    sort_y_point = np.sort(ys)
    for i in range(len(sort_y_point) - 1):
        if (sort_y_point[i + 1] - sort_y_point[i] > celly_dis):
            y_point_arr.append(sort_y_point[i])
        i = i + 1
    # 要将最后一个点加入
    y_point_arr.append(sort_y_point[i])

    # 按照轮廓识别坐标
    squares, result_img = find_squares(merge.copy(), src.copy(), config)
    cv2.drawContours(result_img, squares, -1, (0, 0, 255), 2)
    return squares, result_img
