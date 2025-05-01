from config import get_dry_run_option
from browser_selenium import get_browser
import os
import time
from tqdm import tqdm

if __name__ == '__main__':
    options = get_dry_run_option()
    browser = get_browser(0, options["browser"], int(options["timeout"]))
    input_dir = options["input_dir"]
    total_time_record = []
    fuzz_time_record = []
    for file in tqdm(os.listdir(input_dir)):
        if not file.endswith("html"):
            continue
        t1 = time.perf_counter()
        browser.ready()
        t2 = time.perf_counter()
        res = browser.fuzz(os.path.realpath(input_dir + "/" + file))
        t3 = time.perf_counter()
        if not res:
            print(file)
            print(browser.message())
            continue
        total_time_record.append(t3 - t1)
        fuzz_time_record.append(t3 - t2)
    print(f"avg total time: {sum(total_time_record) / len(total_time_record)} s")
    print(f"avg fuzz time: {sum(fuzz_time_record) / len(fuzz_time_record)} s")
