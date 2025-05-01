import os
import sys
import json

input_dir = sys.argv[1]

key_words = {"-webkit-appearance", "-webkit-mask-box-image-source", "-webkit-mask-image",
             "https://www.w3schools.com/images/picture.jpg", "document.all[0].style[\"filter\"]",
             "document.all", "-webkit-user-modify", "keygen", "basefont", "marquee", "noembed",
             "dialog", "style[\"scale\"]", "mix-blend-mode", "box-direction", "embed"}

useful_files = {}

for parent, dirnames, filenames in os.walk(input_dir):
    if len(filenames) == 0:
        continue
    for file in filenames:
        if file.endswith(".min.diff"):
            trans_file = file[:-8] + "trans"
            trans_str = ""
            with open(os.path.join(parent, trans_file), "r") as f:
                trans = json.load(f)
                t = json.loads(trans["trans"])
                prop = t["prop"]
                new_val = t["new_value"]
                trans_str = f"prop:{prop}; val:{new_val}"

            h2_file = os.path.join(parent, file[:-4] + "h2.html")
            has_keyword = False
            with open(h2_file, "r") as f:
                content = f.read()
                for key_word in key_words:
                    if key_word in content:
                        has_keyword = True
                        break
            if not has_keyword:
                with open(os.path.join(parent, file), "r") as f:
                    diff = json.load(f)
                    if diff["diff1"] != 0 and diff["diff2"] != 0:
                        continue
                    if "diff3" not in diff:
                        continue
                    if trans_str not in useful_files:
                        useful_files[trans_str] = []
                    useful_files[trans_str].append((h2_file, diff["diff1"], diff["diff2"], diff["diff3"]))

presentation_dic = {}
for key, val in useful_files.items():
    val.sort(key=lambda x: x[1], reverse=True)
    presentation_dic[key] = val

print(f"number of keys: {len(presentation_dic.keys())}")

for key, val in presentation_dic.items():
    print("=======")
    print(key)
    for info in val:
        print(f"\t{info}")
