# -*- coding: utf-8 -*-
from paddlenlp import Taskflow
from pprint import pprint
import time


def DEBUG_SHOW_TIME(f):
    def inner(*arg, **kwarg):
        s_time = time.time()
        res = f(*arg, **kwarg)
        e_time = time.time()
        print('MainTool Output', f, '耗时：', str('%.4f' % float(e_time - s_time)), "秒")
        return res

    return inner


@DEBUG_SHOW_TIME
def tiaokuan_txt_line(file_path,my_uie):
    with open(file_path, 'r', encoding='gbk') as f:
        lines = f.readlines()
    for line in lines:
        print("===============================================================")
        pprint(my_uie(line))


if __name__ == "__main__":
    schema_sg_protocol = ["合同名称", "合同价", "合同工期", "开始时间", "所属标段", "合同编号", "签订时间",
                      "支付周期", "对应概算", "发包单位名称", "承建单位名称", "项目负责人", "项目技术负责人", 
                      "项目设计负责人", "项目安全负责人", "项目质量负责人", "项目施工负责人", "法定代表人"]

    # my_uie2 = Taskflow("information_extraction", schema=schema_sg_content, task_path='inference_model/infer-mini-100-new', max_length=163840, padding='max_length')
    my_uie2 = Taskflow("information_extraction", 
    	schema=schema_sg_protocol, 
    	model="uie-mini",
    	task_path='inference_model/test', 
    	position_prob=0.1) #,
    	# max_length=163840, 
    	# padding='max_length')
    
    text = "扩大杭嘉湖南排后续西部通道（南北线）工程九溪出水口枢纽段设计采购施工（EPC)总承包合同发包人：	杭州市南排水利发展有限公司承包人： 浙江省水利水电勘测设计院有限责任公司（牵头人）中国电建集团华东勘测设计研究院有限公司（成员方 1）浙江省第一水电建设集团股份有限公司（成员方 2）\n2023 年 3 月"

    pprint(my_uie2(text))
