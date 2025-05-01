# from playwright.sync_api import sync_playwright
import logging
import signal
import threading
import os
import shutil
import time

import config
import common
from synthesis import EquivalenceSynthesizer
from browser_selenium import get_browser
import time


class FuzzingLoop(threading.Thread):
    # class FuzzingLoop:
    def __init__(self, threadId, options):
        threading.Thread.__init__(self)
        self.threadId = threadId
        self.options = options
        self.exit_time = None
        if self.options["time_to_exit"]:
            self.exit_time = int(self.options["time_to_exit"]) * 3600
        self.execution_iteration = None
        if self.options["execution_iteration"]:
            self.execution_iteration = int(self.options["execution_iteration"])
        self.dir = os.path.join(self.options["output_dir"], f"thread-{threadId}")
        self.crash = os.path.join(self.dir, "crash")
        self.interesting = os.path.join(self.dir, "interesting")
        self.trans_path = os.path.join(self.dir, "trans")
        os.makedirs(self.dir, exist_ok=True)
        os.makedirs(self.crash, exist_ok=True)
        os.makedirs(self.interesting, exist_ok=True)

    def move_to_crash(self, source_path, message, dest_path):
        shutil.move(source_path, os.path.join(self.crash, dest_path))
        with open(os.path.join(self.crash, dest_path + ".log"), "w") as f:
            f.write(message)

    def move_to_interesting(self, source_path, dest_path):
        shutil.move(source_path, os.path.join(self.interesting, dest_path))

    def run(self):
        # with sync_playwright() as playwright:
        synthesizer = EquivalenceSynthesizer(self.threadId)
        browser1 = get_browser(self.threadId, self.options["browser1"],
                               int(self.options["timeout"]))
        browser2 = get_browser(self.threadId, self.options["browser2"],
                               int(self.options["timeout"]))
        start_time = time.time()
        try:
            i = 0
            while True:
                if self.exit_time is not None:
                    if (time.time() - start_time) > self.exit_time:
                        return
                if self.execution_iteration is not None:
                    if i >= self.execution_iteration:
                        return
                if i % 10 == 0:
                    logging.info(f"[{self.threadId}]: {i} iteration")
                    synthesizer.dump_trans(self.trans_path)
                counter_example = synthesizer.transform(browser1, browser2)
                if counter_example is not None:
                    logging.info(f"f[{self.threadId}]: found a counter example!")
                    counter_example.save_to_path(self.crash, str(i))
                i += 1
        except KeyboardInterrupt as e:
            logging.info(f"exit the loop: thread id: {self.threadId}, event: {e}")
            # browser.close()
            return


def main():
    logging.basicConfig(level=logging.INFO)
    options = config.get_main_option()
    common.create_output_directory(options["output_dir"])

    threads = []
    for i in range(int(options["parallel"])):
        thread = FuzzingLoop(i, options)
        thread.start()
        threads.append(thread)
        # time.sleep(20)
    for t in threads:
        t.join()
    logging.info("normal exit the fuzzing")


if __name__ == '__main__':
    main()
