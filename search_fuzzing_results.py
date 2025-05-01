import os
import sys
import json
from compatibility_checker import CompatibilityChecker, CompatibilityResult

input_dir = sys.argv[1]

HTML_NAME = "HTMLTableElement"
PROP_NAME = "padding-right"
ORG_VALUE = ""
NEW_VALUE = ""

BROWSER1_NAME = "chrome"
BROWSER2_NAME = "firefox"


def check_if_interesting(trans_json) -> bool:
    res1 = HTML_NAME == "" or trans_json["el_type"] == HTML_NAME

    res2 = PROP_NAME == "" or trans_json["prop"] == PROP_NAME

    res3 = ORG_VALUE == "" or trans_json["original_value"] == ORG_VALUE

    res4 = NEW_VALUE == "" or trans_json["new_value"] == NEW_VALUE

    return res1 and res2 and res3 and res4


def main():
    useful_files = []
    type_count = {}
    property_count = {}

    comp_checker = CompatibilityChecker()

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
                    is_interesting_case = check_if_interesting(t)
                    compatibility_res = comp_checker.check_css_for_browsers(t["prop"],
                                                                            [t["original_value"], t["new_value"]],
                                                                            [BROWSER1_NAME, BROWSER2_NAME])
                    if is_interesting_case and compatibility_res == CompatibilityResult.Compatible:
                        with open(os.path.join(parent, file), "r") as f2:
                            diff = json.load(f2)
                            if diff["diff1"] == 0 or diff["diff2"] == 0:
                                useful_files.append(
                                    (os.path.join(parent, file), t["el_type"], max(diff["diff1"], diff["diff2"]),
                                     "diff1" if diff["diff1"] > diff["diff2"] else "diff2",
                                     t["original_value"], t["new_value"]))

                                if t["el_type"] not in type_count:
                                    type_count[t["el_type"]] = 0
                                type_count[t["el_type"]] += 1

                                if t["prop"] not in property_count:
                                    property_count[t["prop"]] = 0
                                property_count[t["prop"]] += 1

    useful_files.sort(key=lambda x: (x[1], x[2]), reverse=True)

    for path in useful_files:
        print("=======")
        print(path)

    print("===========================")

    type_count_list = [(key, val) for key, val in type_count.items()]
    type_count_list.sort(key=lambda x: x[1], reverse=True)

    for t in type_count_list:
        print(t)

    print("===========================")

    property_count_list = [(key, val) for key, val in property_count.items()]
    property_count_list.sort(key=lambda x: x[1], reverse=True)

    for p in property_count_list:
        print(p)

    print("===========================")


if __name__ == '__main__':
    main()
