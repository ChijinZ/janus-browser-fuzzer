import os
import sys
import json

input_dir = sys.argv[1]

prop_count = {}

for parent, dirnames, filenames in os.walk(input_dir):
    if len(filenames) == 0:
        continue
    for file in filenames:
        if not file.endswith("h2.html") or "min" in file:
            continue
        trans_file = file[:-7] + "trans"
        with open(os.path.join(parent, trans_file), "r") as f:
            trans = json.load(f)
            t = json.loads(trans["trans"])
            prop = t["prop"]
            _new_val = t["new_value"]
            if prop not in prop_count:
                prop_count[prop] = 0
            prop_count[prop] += 1

print_pro_count_list = []

for key, val in prop_count.items():
    print_pro_count_list.append((key, val))

print_pro_count_list.sort(key=lambda x: x[1], reverse=True)
print(print_pro_count_list)
