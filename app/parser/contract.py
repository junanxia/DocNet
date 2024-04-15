import json
import uuid
import cv2
import os
from parser.base import BaseParser
from utils.util import get_download_save_path
from schema import schema_sg_cover, schema_sg_special


class ContractParser(BaseParser):
    # uie结果中英对应dict
    @staticmethod
    def en_to_ch(content):
        schema = {
            "合同名称": "htmc",
            "合同价": "htj",
            "合同工期": "htgq",
            "开始时间": "kssj",
            "所属标段": "ssbd",
            "合同编号": "htbh",
            "签订时间": "qdsj",
            "支付周期": "zfzq",
            "对应概算": "dygs",
            "发包单位名称": "fbdwmc",
            "承建单位名称": "cjdwmc",
            "项目负责人": "xmfzr",
            "项目技术负责人": "xmjsfzr",
            "项目设计负责人": "xmsjfzr",
            "项目安全负责人": "xmaqfzr",
            "项目质量负责人": "xmzlfzr",
            "项目施工负责人": "xmsgfzr",
            "法定代表人": "fddbr",
            "考勤条款": "ht_kqtq",
            "人员变更条款": "ht_rybgtk",
            "分包约定": "ht_fbyd",
            "交付条款": "th_jftk",
            "质量检测条款": "ht_zljctk",
            "检查条款": "ht_jctk"
        }
        en_dict = {}
        for key, value in content.items():
            if key in schema.keys():
                en_dict[schema[key]] = value
        return en_dict

    def handle_uie_res(self, obj):
        res = self.en_to_ch(obj)
        # 增加合同类型和开始时间判断
        if "qdsj" in res and "kssj" not in res:
            res["kssj"] = res["qdsj"]
        if "htmc" in res:
            text = res["htmc"][0]["text"]
            if "epc" in text.lower():
                type = "EPC总承包合同"
            elif "施工" in text:
                type = "施工合同"
            elif "监理" in text:
                type = "监理合同"
            elif "设计" in text:
                type = "设计合同"
            elif "采购" in text:
                type = "采购合同"
            elif "咨询" in text:
                type = "咨询合同"
            elif "检测" in text:
                type = "检测合同"
            else:
                type = "其他合同"
            res["htlx"] = [{"text": type}]
        return res

    # 文本分类
    def get_contract_txt_clas(self, contract_text):
        result = self.model_class.infer_text_contract_cls(contract_text)
        label = result[0]['predictions'][0]['label']
        return label

    # UIE 提取关键字
    def get_contract_uie_cover(self, contract_text):
        res = self.model_class.infer_uie_contract(contract_text)[0]
        cover_res = {key:value for key, value in res.items() if key in schema_sg_cover}

        return cover_res

    # UIE 提取关键字
    def get_contract_uie_protocol(self, contract_text):
        res = self.model_class.infer_uie_contract(contract_text)[0]
        
        return res
    
    # UIE提取专用合同
    def get_contract_uie_special(self, contract_text):
        # old
        # return self.model_class.infer_uie_contract_special(contract_text)
        
        # new
        res = self.model_class.infer_uie_contract(contract_text)[0]
        special_res = {key:value for key, value in res.items() if key in schema_sg_special}
        return special_res

    def merge_contract_horizontal(self, res_boxes, res_txts, res_scores):
        # 合并纵向文本
        des_boxes, des_txts, des_scores = [], [], []
        for index_box in range(len(res_boxes)):
            # 已合并内容score为None
            if res_scores[index_box] is None:
                continue
            if index_box + 1 < len(res_boxes):
                # 下一个box的索引
                index_next = index_box + 1
                insert_box = res_boxes[index_box]
                insert_txt = res_txts[index_box]
                insert_score = res_scores[index_box]
                while self.check_if_sameline(res_boxes[index_box], res_boxes[index_next]):
                    insert_box = self.merge_contract_points(insert_box, res_boxes[index_next])
                    insert_txt = insert_txt + " " + res_txts[index_next]
                    res_scores[index_next] = None
                    if index_next + 1 < len(res_boxes):
                        index_next += 1
                    else:
                        break
                des_boxes.append(insert_box)
                des_txts.append(insert_txt)
                des_scores.append(insert_score)
                continue
            des_boxes.append(res_boxes[index_box])
            des_txts.append(res_txts[index_box])
            des_scores.append(res_scores[index_box])
        return des_boxes, des_txts, des_scores
    
    def get_contract_split(self, cv_image, res_boxes, res_txts, res_scores):
        '''
        切分左右两版面  
        '''
        xmin = 99999999
        xmax = -99999999
        for res_box in res_boxes:
            for point in res_box:
                if point[0] > xmax:
                    xmax = point[0]
                if point[0] < xmin:
                    xmin = point[0]
        cut_locatx = int((xmin + xmax) / 2)
        # 左页为空
        if xmin > cv_image.shape[1] / 3:
            cut_locatx = int(xmin) - 1
            return (
                None,
                {"res_boxes": res_boxes, "res_txts": res_txts, "res_scores": res_scores},
                cut_locatx,
            )
        # 右页为空
        if xmax < (cv_image.shape[1] * 2) / 3:
            cut_locatx = int(xmax) + 1
            return (
                {"res_boxes": res_boxes, "res_txts": res_txts, "res_scores": res_scores},
                None,
                cut_locatx,
            )
        # 左右分页
        obj_left = {"res_boxes": [], "res_txts": [], "res_scores": []}
        obj_right = {"res_boxes": [], "res_txts": [], "res_scores": []}
        for index_box in range(len(res_boxes)):
            res_box = res_boxes[index_box]
            pmax = -99999999
            for point in res_box:
                if point[0] > pmax:
                    pmax = point[0]
            if pmax < cut_locatx:
                obj_left["res_boxes"].append(res_box)
                obj_left["res_txts"].append(res_txts[index_box])
                obj_left["res_scores"].append(res_scores[index_box])
            else:
                obj_right["res_boxes"].append(res_box)
                obj_right["res_txts"].append(res_txts[index_box])
                obj_right["res_scores"].append(res_scores[index_box])

        return obj_left, obj_right, cut_locatx
    
    def get_contract_single_result(self, index_page, page_type, obj, protocol_start, general_start, special_start):
        '''
        解析单面结果
        '''
        if obj is not None:
            # 合并段落
            obj_boxes, obj_txts, obj_scores = self.merge_contract_horizontal(
                obj["res_boxes"], obj["res_txts"], obj["res_scores"]
            )
            merge_boxes, merge_txts, merge_scores = [], [], []
            merge_box, merge_txt, merge_score = None, None, None
            if page_type == 'text' or page_type == 'double':
                for txt_index, txt in enumerate(obj_txts):
                    # 文字分类
                    label = self.get_contract_txt_clas(txt)
                    if label != 'text':
                        if merge_box is not None:
                            merge_boxes.append(merge_box)
                            merge_txts.append(merge_txt)
                            merge_scores.append(merge_score)
                        merge_box = obj_boxes[txt_index]
                        merge_txt = obj_txts[txt_index]
                        merge_score = obj_scores[txt_index]
                    else:
                        if merge_box is None:
                            merge_box = obj_boxes[txt_index]
                            merge_txt = obj_txts[txt_index]
                            merge_score = obj_scores[txt_index]
                        else:
                            merge_box = self.merge_contract_points(merge_box, obj_boxes[txt_index])
                            merge_txt = merge_txt + obj_txts[txt_index]
                            merge_score = obj_scores[txt_index]
                    # 如果是最后一个直接加入
                    if txt_index == len(obj_txts) - 1 and merge_box is not None:
                        merge_boxes.append(merge_box)
                        merge_txts.append(merge_txt)
                        merge_scores.append(merge_score)
                    # 如果识别出标题进行赋值
                    if label == 'xys' and protocol_start == -1:
                        protocol_start = index_page
                    if label == 'ty' and general_start == -1:
                        general_start = index_page
                    if label == 'zy' and special_start == -1:
                        special_start = index_page
                return merge_boxes, merge_txts, merge_scores, protocol_start, general_start, special_start
            if page_type == 'cover' or page_type == 'directory':
                return obj_boxes, obj_txts, obj_scores, protocol_start, general_start, special_start

        else:
            return None, None, None, protocol_start, general_start, special_start
    
    @staticmethod
    def add_sub_results(sort_boxes, sort_txts, sort_scores, sub_boxes, sub_txts, sub_scores):
        sort_boxes.extend(sub_boxes)
        sort_txts.extend(sub_txts)
        sort_scores.extend(sub_scores)
        return sort_boxes, sort_txts, sort_scores

    def get_result(self, pdf_file, start_index, end_index, **kwargs):
        doc_contract = self.load_pdf_file(pdf_file)
        ip_str = kwargs['ip']

        # 读取json文件内容
        json_path = pdf_file.replace('.pdf', '.json')
        with open(json_path, 'r', encoding="utf-8") as f:
            json_str = f.read()
            all_data_obj = json.loads(json_str, strict=False)

        # 读取json参数
        cover_index_list = all_data_obj.get("cover_index_list", [])
        directory_index_list = all_data_obj.get("directory_index_list", [])

        protocol_start = all_data_obj.get('protocol_start', -1)
        general_start = all_data_obj.get('general_start', -1)
        special_start = all_data_obj.get('special_start', -1)

        cover_uie = all_data_obj.get('cover_uie', None)
        protocol_uie = all_data_obj.get('protocol_uie', None)
        general_uie = all_data_obj.get('general_uie', None)
        special_uie = all_data_obj.get('special_uie', None)

        all_result_texts = all_data_obj.get('all_result_texts', [None] * len(doc_contract))
        all_result_boxes = all_data_obj.get('all_result_boxes', [None] * len(doc_contract))
        all_result_scores = all_data_obj.get('all_result_scores', [None] * len(doc_contract))

        image_path_list = []

        # 是否更新cover_uie
        refresh_cover_uie = False
        for index_page in range(start_index, end_index + 1):
            # 索引越界
            if index_page >= len(doc_contract):
                break
            # 获取当页图片
            cv_image = self.get_pdf_page_image(doc_contract, index_page)
            # 保存图片
            radon_name = str(uuid.uuid1()) + '+' + ip_str + ".jpg"
            save_path = os.path.join(get_download_save_path(), radon_name)
            cv2.imwrite(save_path, cv_image)
            image_path_list.append(save_path)

            # 左右两版面切割初始化参数
            obj_left, obj_right, cut_locatx = None, None, -1
            sorted_boxes, sorted_txtes, sorted_scores = [], [], []
            pic_left_result, pic_right_result = None, None

            # 文字识别 cls+det+rec <0.5ms/字
            res_boxes, res_txts, res_scores = self.get_text_struct(cv_image)
            # print(res_txts)

            # 当页图片进行图像分类
            result = self.model_class.infer_pic_contract_cls.predict(cv_image)
            pic_left_result = next(result)[0]['label_names'][0]

            # 封面和目录存取页码
            if pic_left_result == 'cover' and index_page not in cover_index_list:
                refresh_cover_uie = True
                cover_index_list.append(index_page)
            elif pic_left_result == 'directory' and index_page not in directory_index_list:
                directory_index_list.append(index_page)

            # 双页需要区分
            if pic_left_result == 'double':
                obj_left, obj_right, cut_locatx = self.get_contract_split(cv_image, res_boxes, res_txts, res_scores)
                # 根据cut_locatx切分图片重新图片分类
                left_image = cv_image[:, :cut_locatx, :]
                right_image = cv_image[:, cut_locatx:, :]
                pic_left_result = self.model_class.infer_pic_contract_cls.predict(left_image)
                pic_left_result = next(pic_left_result)[0]['label_names'][0]
                pic_right_result = self.model_class.infer_pic_contract_cls.predict(right_image)
                pic_right_result = next(pic_right_result)[0]['label_names'][0]
            else:
                obj_left = {
                    "res_boxes": res_boxes,
                    "res_txts": res_txts,
                    "res_scores": res_scores,
                }

            # 横纵向合并
            left_boxes, left_txts, left_scores, protocol_start, general_start, special_start = self.get_contract_single_result(
                index_page, pic_left_result, obj_left, protocol_start, general_start, special_start)
            right_boxes, right_txts, right_scores, protocol_start, general_start, special_start = (
                self.get_contract_single_result(index_page, pic_right_result, obj_right, protocol_start, general_start, special_start))

            if left_boxes:
                sorted_boxes, sorted_txtes, sorted_scores = self.add_sub_results(
                    sorted_boxes, sorted_txtes, sorted_scores, left_boxes, left_txts, left_scores)
            if right_boxes:
                sorted_boxes, sorted_txtes, sorted_scores = self.add_sub_results(
                    sorted_boxes, sorted_txtes, sorted_scores, right_boxes, right_txts, right_scores)

            h, w, _ = cv_image.shape
            for box in sorted_boxes:
                for box_index in range(len(box)):
                    box[box_index][0] = box[box_index][0] / w
                    box[box_index][1] = box[box_index][1] / h
            all_result_texts[index_page] = sorted_txtes
            all_result_boxes[index_page] = sorted_boxes
            all_result_scores[index_page] = sorted_scores

        # 封面UIE
        if refresh_cover_uie and len(cover_index_list) > 0:
            content_cover = ""
            for page_idx in cover_index_list:
                for t in all_result_texts[page_idx]:
                    content_cover = content_cover + t + " \n"
            cover_uie = self.handle_uie_res(self.get_contract_uie_cover(content_cover))

        # 协议书UIE
        if protocol_uie is None or not protocol_uie:
            contract_text = ""
            if protocol_start >= 0:
                if general_start > protocol_start or special_start > protocol_start:
                    protocol_end_index = general_start if general_start >= protocol_start else special_start
                    for box_txtes_index in range(protocol_start, protocol_end_index):
                        if all_result_texts[box_txtes_index] is not None:
                            contract_text += " \n".join(all_result_texts[box_txtes_index]) + " \n"
                    protocol_uie = self.handle_uie_res(self.get_contract_uie_protocol(contract_text))

        if protocol_uie is None or not protocol_uie:
            contract_text = ""
            if end_index == len(doc_contract) - 1:
                protocol_start_index = protocol_start if general_start > protocol_start or special_start > protocol_start else 0
                protocol_end_index = len(doc_contract)
                for box_txtes_index in range(protocol_start_index, protocol_end_index):
                    if all_result_texts[box_txtes_index] is not None:
                        contract_text += " \n".join(all_result_texts[box_txtes_index]) + " \n"
                protocol_uie = self.handle_uie_res(self.get_contract_uie_protocol(contract_text)[0])

        # 专用合同UIE
        if end_index == len(doc_contract) - 1 and special_start > 0:
            special_text = ""
            end_index = min(special_start + 21, len(doc_contract))
            for box_txtes_index in range(special_start, end_index):
                if all_result_texts[box_txtes_index] is not None:
                    special_text += " \n".join(all_result_texts[box_txtes_index]) + " \n"
            special_uie = self.handle_uie_res(self.get_contract_uie_special(special_text)[0])

        # 赋值
        all_data_obj["all_result_texts"] = all_result_texts
        all_data_obj["all_result_boxes"] = all_result_boxes
        all_data_obj["all_result_scores"] = all_result_scores

        all_data_obj["cover_uie"] = cover_uie
        all_data_obj["protocol_uie"] = protocol_uie
        all_data_obj["general_uie"] = general_uie
        all_data_obj["special_uie"] = special_uie

        all_data_obj["protocol_start"] = protocol_start
        all_data_obj["general_start"] = general_start
        all_data_obj["special_start"] = special_start

        all_data_obj["cover_index_list"] = cover_index_list
        all_data_obj["directory_index_list"] = directory_index_list

        with open(json_path, 'w', encoding="utf-8") as f:
            json.dump(all_data_obj, f)
        return all_result_boxes, all_result_texts, all_result_scores, image_path_list, cover_uie, protocol_uie, special_uie
