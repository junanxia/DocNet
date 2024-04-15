import sys
import json


def usage():
    print('Usage: python compare.py [file1.json] [file2.json]\n')

def main(first_file, second_file):
    # if len(sys.argv) < 3:
    #     usage()

    # first_file = sys.argv[1]
    # second_file = sys.argv[2]

    first_object = []
    second_object = []

    with open(first_file, encoding='utf8') as reader:
        tmp = reader.readlines()
        for _, line in enumerate(tmp):
            t = json.loads(s=line)
            first_object.append(t)

    with open(second_file, encoding='utf8') as reader:
        tmp = reader.readlines()
        for _, line in enumerate(tmp):
            t = json.loads(s=line)
            second_object.append(t)

    for idx, f_obj in enumerate(first_object):
        obj_text_1 = f_obj["text"]
        print('%d %d' % (idx, f_obj["id"]))

        for s_obj in second_object:
            obj_text_2 = s_obj["text"]

            if obj_text_1 == obj_text_2:
                print('第二个文件中存在相同的text, id1: %d, id2: %d' % (f_obj["id"], s_obj["id"]))
                break
    
    print('Done!')

if __name__ == '__main__':
    first_file = "./datasets/HT-UIE/data_he_202403201516_80/doccano.json"
    second_file = "./datasets/HT-UIE/tiaokuan_test/202402191419缩短考勤条款/e47fb657-4138-4143-a907-32fd34c0077b/admin.jsonl"
    main(first_file, second_file)
    