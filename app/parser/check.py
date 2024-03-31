import uuid
import cv2
import os
from parser.base import BaseParser
from utils.util import (
    get_download_save_path, calculate_iou, order_points, find_largest_rectangle,
    get_rect_center, get_closest_rect, img_to_base64, 
)
from parser.cell_det import parse_pic_to_struct, get_config_json



class CheckParser(BaseParser):
    
    @staticmethod
    def ch_to_en(content):
        schema = {
            "报告编号": "zljc_bgbh",
            "样品编号": "zljc_ypbh",
            "委托日期": "zljc_wtrq",
            "委托单位": "zljc_wtdw",
            "工程结构部位": "zljc_gcjgbw",
            "强度等级": "zljc_qddj",
            "抗压强度平均值": "zljc_kyqdpjz",
            "达到设计强度": "zljc_sjddqd",
            "制作日期": "zljc_zzrq",
            "委托人": "zljc_wtr",
            "取证人": "zljc_qzr"
        }
        en_dict = {}
        for key, value in content.items():
            if key in schema.keys():
                en_dict[schema[key]] = value
        return en_dict


    def get_result(self, pdf_file, start_index, end_index, **kwargs):
        # 获取文档对象 0ms
        doc_contract = self.load_pdf_file(pdf_file)
        ip_str = kwargs["ip"]

        # 报告编号
        report_number = []
        # 委托日期
        date_of_commission = []
        # 委托单位
        unit_of_commission = []
        # 取证人
        qz_people = []
        # 委托人
        wt_people = []
        all_res = []
        images_path = []
        # 逐页获取内容
        for index_page in range(0, len(doc_contract)):
            # 获取当页图片
            cv_image = self.get_pdf_page_image(doc_contract, index_page)
            # 单元格检测
            # 获取单元格列表 result_squares 单元格清单 result_img 调试信息
            res_squares, res_img = parse_pic_to_struct(cv_image, get_config_json('fj4'))
            # 未识别出轮廓
            if len(res_squares) == 0:
                continue
            # 文字识别并将内容填充进去
            res_txts = []
            res_txt_count = 0
            for sq in res_squares:
                # [top-left, top-right, bottom-right, bottom-left]
                sq = order_points(sq).astype(int)
                cell = cv_image[int(sq[0][1]):int(sq[3][1]), int(sq[0][0]):int(sq[1][0])]
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
                continue
            base64_img = img_to_base64(cv_image)
            results = self.model_class.infer_uie_quality_check({"doc": base64_img})

            radon_name = str(uuid.uuid1()) + '+' + ip_str + ".jpg"
            save_path = os.path.join(get_download_save_path(), radon_name)
            cv2.imwrite(save_path, cv_image)
            images_path.append(save_path)

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

                        if max_iou_index == -1 and key == '报告编号':
                            clear_dict[key].append({
                                'text': v['text'],
                                'bbox': max_box
                            })
                        if key == '委托单位':
                            clear_dict[key].append({
                                'text': v['text'],
                                'bbox': max_box
                            })
                        for idx, res_square in enumerate(res_squares):
                            iou = calculate_iou(max_box, res_square)
                            if iou > max_iou:
                                max_iou = iou
                                max_iou_index = idx
                        if max_iou_index != -1:
                            clear_dict[key].append({
                                'text': res_txts[max_iou_index],
                                'bbox': res_squares[max_iou_index].tolist()
                            })
            clear_dict = self.ch_to_en(clear_dict)

            if 'zljc_ypbh' in clear_dict:
                for item in clear_dict['zljc_ypbh']:
                    res = {'zljc_ypbh': item}
                    _, box_center_y = get_rect_center(item['bbox'])
                    # 强度等级
                    if 'zljc_qddj' in clear_dict:
                        res['zljc_qddj'] = get_closest_rect(clear_dict['zljc_qddj'], box_center_y)
                    # 工程结构部位
                    if 'zljc_gcjgbw' in clear_dict:
                        res['zljc_gcjgbw'] = get_closest_rect(clear_dict['zljc_gcjgbw'], box_center_y)
                    # 抗压强度平均值
                    if 'zljc_kyqdpjz' in clear_dict:
                        res['zljc_kyqdpjz'] = get_closest_rect(clear_dict['zljc_kyqdpjz'], box_center_y)
                    # 达到设计强度
                    if 'zljc_sjddqd' in clear_dict:
                        res['zljc_sjddqd'] = get_closest_rect(clear_dict['zljc_sjddqd'], box_center_y)
                    # 制作日期
                    if 'zljc_zzrq' in clear_dict:
                        res['zljc_zzrq'] = get_closest_rect(clear_dict['zljc_zzrq'], box_center_y)

                    all_res.append(res)
            if "zljc_bgbh" in clear_dict:
                for v in clear_dict['zljc_bgbh']:
                    v['index_page'] = index_page
                    report_number.append(v)
            if "zljc_wtrq" in clear_dict:
                for v in clear_dict['zljc_wtrq']:
                    v['index_page'] = index_page
                    date_of_commission.append(v)
            if "zljc_wtdw" in clear_dict:
                for v in clear_dict['zljc_wtdw']:
                    v['index_page'] = index_page
                    unit_of_commission.append(v)
            if "zljc_qzr" in clear_dict:
                for v in clear_dict['zljc_qzr']:
                    v['zljc_qzr'] = index_page
                    qz_people.append(v)
            if "zljc_wtr" in clear_dict:
                for v in clear_dict['zljc_wtr']:
                    v['index_page'] = index_page
                    wt_people.append(v)
        return all_res, report_number, date_of_commission, unit_of_commission, qz_people, wt_people, images_path
