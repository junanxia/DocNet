import uuid
import cv2
import os
import numpy as np
from parser.base import BaseParser
from utils.util import get_download_save_path, calculate_iou, order_points, find_largest_rectangle
from parser.cell_det import parse_pic_to_struct, get_config_json, angle_cos


class BlueprintParser(BaseParser):
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
                max_cos = np.max([angle_cos(cnt[i], cnt[(i + 1) % 4], cnt[(i + 2) % 4]) for i in range(4)])
                # 只检测矩形（cos90° = 0）
                if max_cos < 0.1:
                    # 检测四边形（不限定角度范围）
                    # if True:
                    index = index + 1
                    cv2.putText(img, ("#%d" % index), (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
                    squares.append(cnt)
        return squares, img

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
            res_squares, res_image = parse_pic_to_struct(image_yx, get_config_json('fj2'))
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
