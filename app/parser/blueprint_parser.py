import uuid
import cv2
import os
import numpy as np
from parser.base import BaseParser
from utils.util import get_download_save_path, calculate_iou, order_points, find_largest_rectangle
from flask import current_app


class BlueprintParser(BaseParser):
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

    # 获取表格样式配置
    def get_config_json(self, style_name):
        # 此处添加样式识别逻辑代码
        if style_name == "" or style_name not in self.style_config:
            return self.style_config['normal']
        else:
            return self.style_config[style_name]
    
    @staticmethod
    def angle_cos(p0, p1, p2):
        d1, d2 = (p0 - p1).astype('float'), (p2 - p1).astype('float')
        return abs(np.dot(d1, d2) / np.sqrt(np.dot(d1, d1) * np.dot(d2, d2)))

    # 寻找矩形单元格
    def find_squares(self, bin, img, config):
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
                max_cos = np.max([self.angle_cos(cnt[i], cnt[(i + 1) % 4], cnt[(i + 2) % 4]) for i in range(4)])
                # 只检测矩形（cos90° = 0）
                if max_cos < 0.1:
                    # 检测四边形（不限定角度范围）
                    # if True:
                    index = index + 1
                    cv2.putText(img, ("#%d" % index), (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
                    squares.append(cnt)
        return squares, img

    # 表格图片结构化
    def parse_pic_to_struct(self, src, config):
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
        squares, result_img = self.find_squares(merge.copy(), src.copy(), config)
        cv2.drawContours(result_img, squares, -1, (0, 0, 255), 2)
        return squares, result_img

    def get_result(self, pdf_file, start_index, end_index, **kwargs):
        ip_str = kwargs["ip"]
        doc_contract =  self.load_pdf_file(pdf_file)
        pdf_res = None
        pdf_image = None
        pdf_cut_image = None
        if start_index >= len(doc_contract):
            return None, None, None
        # 获取当页图片
        cv_image =  self.get_pdf_page_image(doc_contract, start_index)
        image_copy = cv_image[:]
        height, width = cv_image.shape[:2]
        # 横版蓝图
        if height < width:
            image_yx = image_copy[int(image_copy.shape[0] * 3 / 4):image_copy.shape[0],
                    int(image_copy.shape[1] * 5 / 8):image_copy.shape[1]]
            # 单元格检测
            # 获取单元格列表 result_squares 单元格清单 result_img 调试信息
            res_squares, res_image = self.parse_pic_to_struct(image_yx, self.get_config_json('fj2'))
            # 未识别出轮廓
            if len(res_squares) == 0:
                return pdf_res, pdf_image, pdf_cut_image
            # 文字识别并将内容填充进去
            res_txts = []
            res_txt_count = 0
            for sq in res_squares:
                # [top-left, top-right, bottom-right, bottom-left]
                sq = order_points(sq).astype(int)
                cell = image_yx[int(sq[0][1]):int(sq[3][1]), int(sq[0][0]):int(sq[1][0])]
                result_ocr = self.model_class.infer_ch.ocr(cell, cls=True)
                content_ocr = ''
                if result_ocr is not None:
                    for idx in range(len(result_ocr)):
                        res = result_ocr[idx]
                        if res is not None:
                            for line in res:
                                content_ocr = content_ocr + line[1][0]
                # 组装单元格json内容
                res_txts.append(content_ocr)
                if content_ocr == '':
                    res_txt_count = res_txt_count + 1
            if res_txt_count == len(res_txts):
                return pdf_res, pdf_image, pdf_cut_image

            # 保存图片
            radon_name = str(uuid.uuid1()) + '+' + ip_str + ".jpg"
            save_path = os.path.join(get_download_save_path(), radon_name)
            cv2.imwrite(save_path, cv_image)
            radon_cut_name = str(uuid.uuid1()) + '+' + ip_str + ".jpg"
            save_cut_path = os.path.join(get_download_save_path(), radon_cut_name)
            cv2.imwrite(save_cut_path, image_yx)

            pdf_image = save_path
            pdf_cut_image = save_cut_path

            # base64_img = cv2_to_base64(image_yx)
            results = self.model_class.infer_uie_blueprint({"doc": save_cut_path})
            
            clear_dict = {}
            for key, value in results[0].items():
                if len(value) > 0:
                    clear_dict[key] = []
                    for v in value:
                        # 找到面积最大的矩形框
                        max_box = find_largest_rectangle(v['bbox'])
                        max_box = [
                            [max_box[0], max_box[1]],
                            [max_box[2], max_box[1]],
                            [max_box[2], max_box[3]],
                            [max_box[0], max_box[3]]
                        ]
                        max_iou = 0
                        max_iou_index = -1
                        if key == '日期':
                            clear_dict[key].append({
                                'text': v['text'],
                                'bbox': max_box
                            })
                            continue
                        if key == '图号':
                            clear_dict[key].append({
                                'text': v['text'],
                                'bbox': max_box
                            })
                            continue
                        for idx, res_square in enumerate(res_squares):
                            res_square = order_points(res_square)
                            iou = calculate_iou(max_box, res_square)
                            if iou > max_iou:
                                max_iou = iou
                                max_iou_index = idx
                        if max_iou_index != -1:
                            clear_dict[key].append({
                                'text': res_txts[max_iou_index],
                                'bbox': res_squares[max_iou_index].tolist()
                            })
            pdf_res = self.ch_to_en(clear_dict)

        return pdf_res, pdf_image, pdf_cut_image
