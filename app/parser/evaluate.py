import uuid
import cv2
import os
from parser.base import BaseParser
from utils.util import (
    get_download_save_path, calculate_iou, order_points, find_largest_rectangle,
    img_to_base64, rot_image,

)
from parser.cell_det import parse_pic_to_struct, get_config_json


class EvaluateParser(BaseParser):
    @staticmethod
    def ch_to_en(content):
        schema = {
            "单位工程名称": "zlpd_dwgcmc",
            "单元工程量": "zlpd_dygcl",
            "工序编号": "zlpd_gxbh",
            "工序名称": "zlpd_gxmc",
            "分部工程名称": "zlpd_fbgcmc",
            "施工单位": "zlpd_sgdw",
            "单元工程名称部位": "zlpd_dygcmcbw",
            "施工日期": "zlpd_sgrq",
            "监理单位复核意见": "zlpd_jldwfhyj",
            "质量评定结果": "zlpd_zlpdjg"
        }
        en_dict = {}
        for key, value in content.items():
            if key in schema.keys():
                en_dict[schema[key]] = value
        return en_dict
    
    @staticmethod
    def remove_words_from_string(input_string, words_list):
        for word in words_list:
            input_string = input_string.replace(word, "")
        return input_string

    def get_contract_word(self, cv_image):
        # 文字识别
        infer_ch_result = self.model_class.infer_ch.ocr(cv_image)
        ch_boxes, ch_txts, ch_scores = [], [], []
        if infer_ch_result is not None:
            if infer_ch_result[0] is not None:
                ch_boxes = [line[0] for line in infer_ch_result[0]]
                ch_txts = [line[1][0] for line in infer_ch_result[0]]
                ch_scores = [line[1][1] for line in infer_ch_result[0]]
        return ch_boxes, ch_txts, ch_scores

    def get_result(self, pdf_file, start_index, end_index, **kwargs):
        # 返回参数初始化定义
        result = {}
        ip_str = kwargs["ip"]

        # 获取文档对象 0ms
        doc_contract = self.load_pdf_file(pdf_file)
        # 获取当页图片
        cv_image =  self.get_pdf_page_image(doc_contract, start_index)
        # 矫正图片
        warped_image = rot_image(cv_image)

        radon_name = str(uuid.uuid1()) + '+' + ip_str + ".jpg"
        image = os.path.join(get_download_save_path(), radon_name)
        cv2.imwrite(image, warped_image)

        # 获取单元格列表 result_squares 单元格清单 result_img 调试信息
        res_squares, res_img = parse_pic_to_struct(warped_image, get_config_json('fj5'))
        # 未识别出轮廓
        if len(res_squares) == 0:
            return image, result
        
        res_txts = []
        res_boxes = []
        res_single_txt = []
        res_txt_count = 0
        for sq in res_squares:
            # [top-left, top-right, bottom-right, bottom-left]
            sq = order_points(sq).astype(int)
            cell = warped_image[int(sq[0][1]):int(sq[3][1]), int(sq[0][0]):int(sq[1][0])]
            ch_boxes, ch_texts, ch_scores = self.get_contract_word(cell)
            res_boxes.append(ch_boxes)
            res_single_txt.append(ch_texts)
            content_ocr = ''
            if ch_texts is not None and len(ch_texts) > 0:
                for text in ch_texts:
                    content_ocr = content_ocr + text
            # 组装单元格json内容
            res_txts.append(content_ocr)
            if content_ocr == '':
                res_txt_count = res_txt_count + 1
        if res_txt_count == len(res_txts):
            return image, result
        
        base64_img = img_to_base64(warped_image)
        results = self.model_class.infer_uie_quality_evaluate({"doc": base64_img})
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
                    for idx, res_square in enumerate(res_squares):
                        res_square = order_points(res_square).astype(int)
                        iou = calculate_iou(max_box, res_square)
                        if iou > max_iou:
                            max_iou = iou
                            max_iou_index = idx
                    if max_iou_index != -1:
                        bbox = order_points(res_squares[max_iou_index]).astype(int)
                        clear_dict[key].append({
                            'text': res_txts[max_iou_index],
                            'bbox': bbox.tolist(),
                            'single_box': res_boxes[max_iou_index],
                            'single_text': res_single_txt[max_iou_index]
                        })
                    else:
                        clear_dict[key].append({
                            'text': v['text'],
                            'bbox': max_box,
                            'single_box': max_box,
                            'single_text': v['text']
                        })

        pdf_res = self.ch_to_en(clear_dict)

        if 'zlpd_dygcmcbw' in pdf_res:
            result['zlpd_dygcmcbw'] = pdf_res['zlpd_dygcmcbw']

        find_box_obj = None
        if 'zlpd_zlpdjg' in pdf_res and 'zlpd_jldwfhyj' in pdf_res:
            find_box_obj = pdf_res['zlpd_zlpdjg'][0]
        if 'zlpd_zlpdjg' not in pdf_res and 'zlpd_jldwfhyj' in pdf_res:
            box_jldwfhyj = pdf_res['zlpd_jldwfhyj'][0]['bbox']
            box_y_arg = (box_jldwfhyj[1][1] + box_jldwfhyj[2][1]) / 2
            box_x_arg = (box_jldwfhyj[0][0] + box_jldwfhyj[1][0]) / 2
            box_idx = -1
            for idx, res_square in enumerate(res_squares):
                res_square = order_points(res_square).astype(int)
                box_sq_y_arg = (res_square[1][1] + res_square[2][1]) / 2
                box_sq_x_arg = (res_square[0][0] + res_square[1][0]) / 2
                if abs(box_y_arg - box_sq_y_arg) < 5 < abs(box_x_arg - box_sq_x_arg):
                    box_idx = idx
            if box_idx > -1:
                find_box_obj = {
                    'text': res_txts[box_idx],
                    'bbox': order_points(res_squares[box_idx]).astype(int),
                    'single_box': res_boxes[box_idx],
                    'single_text': res_single_txt[box_idx]
                }

        if find_box_obj:
            cut_image = warped_image[int(find_box_obj['bbox'][0][1]):int(find_box_obj['bbox'][3][1]),
                        int(find_box_obj['bbox'][0][0]):int(find_box_obj['bbox'][1][0])]
            score_index = -1
            date_index = -1
            for idx, item in enumerate(find_box_obj['single_text']):
                if '质量等级评定' in item:
                    score_index = idx
                if '加盖公章' in item:
                    date_index = idx

            if score_index >= 0:
                find_box = find_box_obj['single_box'][score_index]
                score_image = cut_image[int(find_box[1][1] - 30):int(find_box[2][1] + 20),
                            int(find_box[0][0]):int(find_box[1][0] + 120)]
                score_box = [
                    [int(find_box[0][0]), int(find_box[1][1] - 30)],
                    [int(find_box[1][0] + 120), int(find_box[1][1] - 30)],
                    [int(find_box[1][0] + 120), int(find_box[1][1] + 20)],
                    [int(find_box[0][0]), int(find_box[1][1] + 20)]
                ]
                res = self.model_class.infer_quality_evaluate_cls.predict(score_image)
                pic_cls_result = next(res)[0]['label_names'][0]

                radon_name = str(uuid.uuid1()) + '+' + ip_str + ".jpg"
                score_path = os.path.join(get_download_save_path(), radon_name)
                cv2.imwrite(score_path, score_image)

                result['score'] = [
                    {
                        'bbox': score_box,
                        'text': pic_cls_result,
                        'image': score_path
                    }
                ]

            if date_index > -1:
                find_box = find_box_obj['single_box'][date_index]
                date_image = cut_image[int(find_box[1][1] - 30):int(find_box[2][1] + 20),
                            int(find_box[0][0]):int(warped_image.shape[1])]
                date_box = [
                    [int(find_box[0][0]), int(find_box[1][1] - 30)],
                    [int(warped_image.shape[1]), int(find_box[1][1] - 30)],
                    [int(warped_image.shape[1]), int(find_box[1][1] + 20)],
                    [int(find_box[0][0]), int(find_box[1][1] + 20)]
                ]
                text = ''
                for i in range(date_index, len(find_box_obj['single_text'])):
                    text = text + find_box_obj['single_text'][i]

                words_list = ["（", "）", '签字', ',', '，', '加盖公章']
                text = self.remove_words_from_string(text, words_list)

                radon_name = str(uuid.uuid1()) + '+' + ip_str + ".jpg"
                date_path = os.path.join(get_download_save_path(), radon_name)
                cv2.imwrite(date_path, date_image)
                result['date'] = [
                    {
                        'bbox': date_box,
                        'text': text,
                        'image': date_path
                    }
                ]

        return image, result
