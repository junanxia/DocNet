import cv2
import fitz
import numpy as np
from PIL import Image


class BaseParser(object):
    def __init__(self, model_class) -> None:
        self.model_class = model_class

    @staticmethod
    def load_pdf_file(pdf_file):
        return fitz.open(pdf_file)
    
    @staticmethod
    def get_pdf_page_image(pdf_doc, page_index):
        # 默认分辨率1倍 1->2倍->4倍 40页合同 42.1216-> 45.9046 -> 52.6322 ocr小模型 42.1216->37.5072
        multiple = 2
        # 转化成图片
        page = pdf_doc.load_page(page_index)
        zoom_x, zoom_y = multiple, multiple
        trans = fitz.Matrix(zoom_x, zoom_y)
        pix = page.get_pixmap(matrix=trans, alpha=False)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        # 将 PIL.Image 转换为 numpy 数组
        arr = np.array(image)
        # 将 numpy 数组转换为 OpenCV 格式
        opencv_image = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        return opencv_image
    
    def get_text_struct(self, cv_image):
        # 文字识别
        if self.model_class.infer_ch is None:
            raise Exception("OCR model is not initialized.") 

        infer_ch_result = self.model_class.infer_ch.ocr(cv_image)
        ch_boxes, ch_txts, ch_scores = [], [], []
        if infer_ch_result is not None:
            if infer_ch_result[0] is not None:
                ch_boxes = [line[0] for line in infer_ch_result[0]]
                ch_txts = [line[1][0] for line in infer_ch_result[0]]
                ch_scores = [line[1][1] for line in infer_ch_result[0]]
        return ch_boxes, ch_txts, ch_scores
    
    @staticmethod
    def get_points_min_max(res_box):
        xmin = 99999999
        xmax = -99999999
        ymin = 99999999
        ymax = -99999999
        for point in res_box:
            if point[0] > xmax:
                xmax = point[0]
            if point[0] < xmin:
                xmin = point[0]
            if point[1] > ymax:
                ymax = point[1]
            if point[1] < ymin:
                ymin = point[1]
        return xmin, xmax, ymin, ymax

    # 合并两个box
    def merge_contract_points(self, boxescur, boxnext):
        cur_xmin, cur_xmax, cur_ymin, cur_ymax = self.get_points_min_max(boxescur)
        next_xmin, next_xmax, next_ymin, next_ymax = self.get_points_min_max(boxnext)
        if next_xmin < cur_xmin:
            cur_xmin = next_xmin
        if next_xmax > cur_xmax:
            cur_xmax = next_xmax
        if next_ymin < cur_ymin:
            cur_ymin = next_ymin
        if next_ymax > cur_ymax:
            cur_ymax = next_ymax
        return [
            [cur_xmin, cur_ymin],
            [cur_xmax, cur_ymin],
            [cur_xmax, cur_ymax],
            [cur_xmin, cur_ymax],
        ]

    def check_if_sameline(self, boxcur, boxnext):
        boxcur_xmin, boxcur_xmax, boxcur_ymin, boxcur_ymax = self.get_points_min_max(boxcur)
        boxnext_xmin, boxnext_xmax, boxnext_ymin, boxnext_ymax = self.get_points_min_max(boxnext)
        if (
                boxcur_xmax < (boxnext_xmin + boxnext_xmax) / 2
                and boxcur_ymax > (boxnext_ymin + boxnext_ymax) / 2
        ):
            return True
        else:
            return False

    
    def get_result(self, pdf_file, start_index, end_index, **kwargs):
        raise NotImplemented
    