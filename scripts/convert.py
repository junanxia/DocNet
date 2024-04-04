import sys
import json


def usage():
    print('Usage: python convert.py [doccano_with_relation.json] [target.json]\n')

def main():
    if len(sys.argv) < 3:
        usage()

    src_file = sys.argv[1]
    dsc_file = sys.argv[2]

    file = open(dsc_file, "w+")
    with open(src_file, encoding='utf8') as reader:
        tmp = reader.readlines()
        for idx, line in enumerate(tmp):
            t = json.loads(s=line)

            labels = []
            for entity in t["entities"]:
                print(entity)
                label = [entity['start_offset'], entity['end_offset'], entity['label']]
                labels.append(label)

            new_data = {"id": t["id"], "text": t['text'], "Comments": t["Comments"], "label": labels}
            d = json.dumps(new_data)
            file.write(d + "\n")
            
            print(new_data)

    file.close()

if __name__ == '__main__':
    main()
    