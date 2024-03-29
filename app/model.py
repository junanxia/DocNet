
import os
from paddleocr import PaddleOCR
from paddlenlp import Taskflow
from paddleclas import PaddleClas
from config import Config
from schema import schema_sg_protocol, schema_sg_special, schema_qc, schema_bp, schema_qe


class ModelClass(object):
    def __init__(self):
        print("-------------------- OCR 模型初始化 -----------------------")
        model_root_path = os.path.join(Config.ROOT_PATH, Config.MODEL_ROOT)
        
        self.infer_ch = PaddleOCR(
            use_angle_cls=True,
            cls_model_dir=os.path.join(model_root_path, "ch_cls"),
            rec_model_dir=os.path.join(model_root_path, "ch_rec"),
            det_model_dir=os.path.join(model_root_path, "ch_det"),
        )

        print("-------------------- 合同UIE 模型初始化 -----------------------")
        self.infer_uie_contract = Taskflow(
            "information_extraction",
            schema=schema_sg_protocol,
            task_path=os.path.join(model_root_path, "ch_uie"),
        )
        
        self.infer_uie_contract_special = Taskflow(
            "information_extraction",
            schema=schema_sg_special,
            task_path=os.path.join(model_root_path, "ch_uie_special")
        )

        self.infer_uie_quality_check = Taskflow("information_extraction", model="uie-x-base", schema=schema_qc,
                                                task_path=os.path.join(model_root_path, "ch_uie_quality_check"),
                                                precision='fp32')
        self.infer_uie_blueprint = Taskflow("information_extraction", model="uie-x-base", schema=schema_bp,
                                            task_path=os.path.join(model_root_path, "ch_uie_blue"),
                                            precision='fp32')
        self.infer_uie_quality_evaluate = Taskflow("information_extraction", model="uie-x-base", schema=schema_qe,
                                                   task_path=os.path.join(model_root_path, "ch_uie_quality_evaluate"),
                                                   precision='fp32')
        
        print("-------------------- 合同文本分类 模型初始化 -----------------------")
        self.infer_text_contract_cls = Taskflow("text_classification",
                                                task_path=os.path.join(model_root_path, "ch_text"),
                                                is_static_model=True)
        
        print("-------------------- 合同图片分类 模型初始化 -----------------------")
        model_path = os.path.join(model_root_path, "ch_pic")
        self.infer_pic_contract_cls = PaddleClas(use_gpu=True, use_tensorrt=False,
                                                 class_id_map_file=os.path.join(model_path, "label.txt"),
                                                 inference_model_dir=model_path)
        
        qe_model_path = os.path.join(model_root_path, "ch_cls_qe_score")
        self.infer_quality_evaluate_cls = PaddleClas(use_gpu=True, use_tensorrt=False,
                                                     class_id_map_file=os.path.join(qe_model_path, "label.txt"),
                                                     inference_model_dir=qe_model_path)
