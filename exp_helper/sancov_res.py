import os
import sys
import json
import pandas as pd

if len(sys.argv) != 2:
    exit()

log_dir = sys.argv[1]

REPEAT_TIME = 5

browser_names = ["webkit", "firefox", "chromium"]
cov_res = {var: {} for var in browser_names}
crash_res = {var: {} for var in browser_names}


def process_log(browser_name: str, log: str) -> [str]:
    res = set()
    splited = log.splitlines()
    for i, line in enumerate(splited):
        if browser_name == "webkit":
            if "SUMMARY" in line:
                res.add(line)
            elif "WTFCrash" in line:
                root = splited[i + 1].split(" ")[-2]
                res.add(f"{line}\n{root}")
            elif "ASSERTION" in line:
                res.add(line)
        elif browser_name == "chromium":
            if "FATAL" in line:
                index = line.find("FATAL")
                l2 = line[index:]
                index = l2.find("]")
                res.add(l2[:index])
    # if len(res) == 0:
    #     print(log)
    #     return ["normal_crash"]
    # else:
    #     return res
    return res


for path in os.listdir(log_dir):
    index = path.find("sancov")
    if index == -1:
        continue
    names = path.split("-")[:-1]
    name = names[1]
    browser_name = names[2]
    cov_path = "-".join(names) + "-cov"
    file = os.path.join(log_dir, path, cov_path)
    print(file)
    if name not in cov_res[browser_name]:
        cov_res[browser_name][name] = []
    if name not in crash_res[browser_name]:
        crash_res[browser_name][name] = []

    with open(file) as f:
        r = f.readlines()[-1]
        data = json.loads(r)
        cov_res[browser_name][name].append(data["covered_num"])

    crash_path = file + "-output/thread-0/crash/"
    unique_crash_set = set()
    for file_name in os.listdir(crash_path):
        if not file_name.endswith("log"):
            continue
        log = None
        with open(crash_path + file_name, "r") as f:
            # print(crash_path + file_name)
            log = f.read()
            # print(len(log))
        splited = log.splitlines()
        log2 = ""
        with open(crash_path + file_name, "w") as f:
            for line in splited:
                if line.__contains__("AT-SPI: Could not obtain desktop path or name"):
                    # print(line)
                    continue
                if len(line) == 0 or line.startswith('\x00'):
                    continue
                f.write(line)
                f.write("\n")
                log2 += line + "\n"
            keys = process_log(browser_name, log2)
            for key in keys:
                unique_crash_set.add(key)

    crash_res[browser_name][name].append(list(unique_crash_set))

with open("crash.json", "w+") as f:
    json.dump(crash_res, f)

data = []
for browser_name, val in cov_res.items():
    for fuzzer_name, vec in val.items():
        assert len(vec) == REPEAT_TIME
        dic = {"browser": browser_name, "fuzzer": fuzzer_name}
        for i, cov in enumerate(vec):
            dic[str(i + 1)] = cov
        data.append(dic)

df = pd.DataFrame(data)
df.to_csv("cov.csv", index=False)
