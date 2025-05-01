import sys
import json

input_path = sys.argv[1]

cnt = 0
accumulated_overhead_dict = {}

with open(input_path, "r") as f:
    for line in f.readlines():
        index = line.find("overhead info: ")
        if index == -1:
            continue

        overhead_info_str = line[index + len("overhead info: "):]
        overhead_info_str = overhead_info_str.replace("\'", "\"")
        overhead_info: dict = json.loads(overhead_info_str)
        for key, val in overhead_info.items():
            if key in accumulated_overhead_dict:
                accumulated_overhead_dict[key] += val
            else:
                accumulated_overhead_dict[key] = val
        cnt += 1

consistency_check_time = accumulated_overhead_dict["result_check"] + (
        accumulated_overhead_dict["browser1_execution_for_input1"] +
        accumulated_overhead_dict["browser1_execution_for_input2"] +
        accumulated_overhead_dict["browser2_execution_for_input1"] +
        accumulated_overhead_dict["browser2_execution_for_input2"] -
        accumulated_overhead_dict["actual_execution_time"])

avg_result = {
    "init_dom_generation": accumulated_overhead_dict["generate_input"] / cnt,
    "html_transformation": accumulated_overhead_dict["transformation"] / cnt,
    "browser_execution": accumulated_overhead_dict["actual_execution_time"] / cnt,
    "consistency_check": consistency_check_time / cnt,
}

print(avg_result)

avg_total_time = avg_result["init_dom_generation"] + avg_result["html_transformation"] + avg_result[
    "browser_execution"] + avg_result["consistency_check"]

for key, val in avg_result.items():
    print(f"{key}: {val / avg_total_time * 100:.2f}%")
