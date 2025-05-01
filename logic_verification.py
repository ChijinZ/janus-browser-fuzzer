import logging
import os
import shutil
import config
import common
from browser_selenium import get_browser
from synthesis import verify_bug, logic_minimizer
import json
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED, ProcessPoolExecutor
from tqdm import tqdm


def re_verify(options):
    input_dir = options["input_dir"]
    number_of_head = int(options["head"])
    browser1 = get_browser(0, options["browser1"],
                           int(options["timeout"]))
    browser2 = get_browser(0, options["browser2"],
                           int(options["timeout"]))
    records = []
    for parent, dirnames, filenames in tqdm(os.walk(input_dir)):
        if len(filenames) == 0:
            continue
        for file in tqdm(filenames):
            if len(file) <= 5:
                continue
            if not file.endswith(".trans"):
                continue
            trans_path = os.path.join(parent, file)
            with open(trans_path, "r") as f:
                trans_content = json.load(f)

            file_id = file[:-6]
            h1 = os.path.join(parent, file_id + ".h1.html")
            h2 = os.path.join(parent, file_id + ".h2.html")
            diff, img_files = verify_bug(h1, h2, browser1, browser2)
            if diff is not None:
                records.append((trans_content, trans_path, diff))
    records.sort(key=lambda x: x[2], reverse=True)
    for i in range(min(number_of_head, len(records))):
        print(records[i])


def check_and_minimize(options):
    input_dir = options["input_dir"]
    number_of_head = int(options["head"])
    records = []
    for parent, dirnames, filenames in os.walk(input_dir):
        if len(filenames) == 0:
            continue
        for file in filenames:
            if len(file) <= 5:
                continue
            if not file.endswith(".trans"):
                continue
            trans_path = os.path.join(parent, file)
            try:
                with open(trans_path, "r") as f:
                    trans_content = json.load(f)
            except:
                continue
            diff = 0
            if "diff" in trans_content:
                diff = trans_content["diff"]
            else:
                try:
                    diff = max(trans_content["diff1"], trans_content["diff2"])
                except:
                    diff = 1
                    logging.info(f"did not contain diff in content: {file}")
            records.append((trans_content, trans_path, diff))
    records.sort(key=lambda x: x[2], reverse=True)

    logging.info("traversed all files")
    logging.info(f"need to process: {len(records)}")

    parallel_num = int(options["parallel"])
    with ProcessPoolExecutor(max_workers=parallel_num) as executor:
        tasks = []
        for i in range(len(records)):
            trans_path = records[i][1]
            path = trans_path[:-6]
            if os.path.exists(path + ".min.diff"):
                with open(path + ".min.diff", "r") as f:
                    diff_json = json.load(f)
                    if "diff3" in diff_json:
                        continue

            h2_file_path = path + ".h2.html"
            task = executor.submit(logic_minimizer,
                                   h2_file_path,
                                   options["browser1"],
                                   options["browser2"],
                                   options["browser3"],
                                   int(options["timeout"]), i, options["use_llm"])
            tasks.append(task)
        logging.info("wait for tasks")
        logging.info(f"task nums: {len(tasks)}; parallel nums: {parallel_num}")
        wait(tasks, return_when=ALL_COMPLETED)
    diffs = []
    for parent, dirnames, filenames in os.walk(input_dir):
        if len(filenames) == 0:
            continue
        for file in tqdm(filenames):
            if not file.endswith(".diff"):
                continue
            diff_path = os.path.join(parent, file)
            with open(diff_path, "r") as f:
                diff = json.load(f)
                diffs.append((diff_path, max(diff["diff1"], diff["diff2"])))
    diffs.sort(key=lambda x: x[1], reverse=True)
    for diff in diffs[:min(number_of_head, len(diffs))]:
        print(diff)


def logic_verification():
    logging.basicConfig(level=logging.INFO)
    options = config.get_verification_option()
    need_re_verify = options["re-verify"]
    if need_re_verify:
        re_verify(options)
    else:
        check_and_minimize(options)


if __name__ == '__main__':
    logic_verification()
