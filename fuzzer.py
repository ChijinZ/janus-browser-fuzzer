from config import get_generation_only_option
import copy
import os
import logging
import subprocess
import random
import sys
import shutil
import time
from tqdm import tqdm


# from domato.generator import Generator


class Fuzzer(object):
    def generate_input(self) -> str:
        pass

    def is_interesting(self) -> bool:
        pass

    def clone(self):
        pass

    def close(self):
        pass


def get_fuzzer(fuzzer_name, id) -> Fuzzer:
    fuzzer = None
    if fuzzer_name == "domato":
        fuzzer = FileBasedDomatoFuzzer(id)
    elif fuzzer_name == "freedom":
        fuzzer = FileBasedFreeDomFuzzer(id)
    elif fuzzer_name == "favocado":
        fuzzer = FileBasedFavocadoFuzzer(id)
    elif fuzzer_name == "dummy":
        fuzzer = Fuzzer()
    else:
        logging.error(f"invalid fuzzer: {fuzzer_name}")
        exit()
    assert fuzzer is not None
    return fuzzer


# class DomatoFuzzer(Fuzzer):
#     def __init__(self, id):
#         self.id = id
#         self.generator = Generator()
#         self.tmp_path = "/tmp/domato-fuzzer/tmpoutput-" + str(self.id)
#         os.makedirs(self.tmp_path, exist_ok=True)
#
#     def generate_input(self) -> str:
#         seed = self.generator.generate_one()
#         target_file = os.path.join(self.tmp_path, "tmp")
#         try:
#             f = open(target_file, 'w')
#             f.write(seed)
#             f.close()
#         except IOError:
#             print('Error writing to output')
#         return target_file
#
#     def is_interesting(self) -> bool:
#         return False
#
#     def clone(self):
#         return copy.deepcopy(self)


class FileBasedDomatoFuzzer(Fuzzer):
    def __init__(self, id):
        self.id = id
        # path = os.getenv("DOMATO_PATH")
        # if path is None:
        #     logging.error(f"doesn't have DOMATO_PATH env var")
        #     exit()
        path = os.path.dirname(__file__)
        path = os.path.join(path, "domato/generator.py")
        if not os.path.exists(path):
            logging.error(f"doesn't have {path} doens't exist")
            exit()
        self.domato_path = path
        self.tmp_path = "/tmp/domato-fuzzer/tmpoutput-" + str(self.id) + "pid" + str(
            os.getpid()) + "rand" + str(random.random())

        self.target_file = os.path.join(self.tmp_path, "tmp")
        if os.getenv("ENABLE_RULE_MAP") is not None:
            os.environ["RULE_SEQ_PATH"] = self.target_file + ".seq"
        self.p = None
        self.new_child()

    def new_child(self):
        try:
            self.p = subprocess.Popen(["python3", self.domato_path],
                                      stdout=subprocess.PIPE,
                                      stdin=subprocess.PIPE)
            self.p.stdin.write(f"init: {self.target_file}\n".encode('utf-8'))
            self.p.stdin.flush()
            while True:
                msg = self.p.stdout.readline().decode("utf-8").strip()
                if msg == "received":
                    break
                elif msg != "":
                    print(f"[{self.id}]: msg from domato process: {msg}")
            os.makedirs(self.tmp_path, exist_ok=True)
        except BaseException as e:
            logging.info(f"[{self.id}]: fuzzer error: {e}")
            self.p.terminate()
            self.new_child()

    def __del__(self):
        self.p.terminate()

    def generate_input(self) -> str:
        try:
            # logging.debug(f"domato output: {p.stdout.read()}")
            self.p.stdin.write("generate\n".encode("utf-8"))
            self.p.stdin.flush()
            while True:
                if self.p.poll is not None:
                    raise Exception("fuzzer process has been terminated")
                msg = self.p.stdout.readline().decode("utf-8").strip()
                if msg == "done":
                    break
                elif msg != "":
                    print(f"[{self.id}]: msg from domato process: {msg}")
            return self.target_file
        except BaseException as e:
            logging.info(f"[{self.id}]: fuzzer error: {e}")
            self.p.terminate()
            self.new_child()
            return self.generate_input()

    def is_interesting(self) -> bool:
        return False

    def clone(self):
        return copy.deepcopy(self)

    def close(self):
        self.p.terminate()


class FileBasedFreeDomFuzzer(Fuzzer):
    def __init__(self, id):
        self.id = id
        if "FREEDOM_PATH" in os.environ:
            self.freedom_path = os.environ["FREEDOM_PATH"]
        else:
            logging.error("FREEDOM_PATH is not in env var")
            exit()

        self.tmp_path = "/tmp/freedom-fuzzer/tmpoutput-" + str(self.id) + "pid" + str(
            os.getpid()) + "rand" + str(random.random())
        os.makedirs(self.tmp_path, exist_ok=True)

    def generate_input(self) -> str:
        for file in os.listdir(self.tmp_path):
            path = os.path.join(self.tmp_path, file)
            os.remove(path)
        p = subprocess.run(
            ["python3", self.freedom_path, "-i", "1", "-m", "generate", "-n", "1", "-o",
             self.tmp_path], stdout=subprocess.PIPE)
        for file in os.listdir(self.tmp_path):
            path = os.path.join(self.tmp_path, file)
            return path
        # did not generate input successfully
        return self.generate_input()

    def is_interesting(self) -> bool:
        return False

    def clone(self):
        return copy.deepcopy(self)


class FileBasedFavocadoFuzzer(Fuzzer):
    def __init__(self, id):
        self.id = id
        if "FAVOCADO_PATH" in os.environ:
            self.favocado_path = os.environ["FAVOCADO_PATH"]
        else:
            logging.error("FAVOCADO_PATH is not in env var")
            exit()

        self.tmp_path = "/tmp/favocado-fuzzer/tmpoutput-" + str(self.id) + "pid" + str(
            os.getpid()) + "rand" + str(random.random())
        os.makedirs(self.tmp_path, exist_ok=True)

    def generate_input(self) -> str:
        for file in os.listdir(self.tmp_path):
            path = os.path.join(self.tmp_path, file)
            os.remove(path)
        p = subprocess.run(
            ["node", self.favocado_path, "-r", "-n", "1", "-o", self.tmp_path],
            stdout=subprocess.PIPE)
        for file in os.listdir(self.tmp_path):
            path = os.path.join(self.tmp_path, file)
            return path
        # did not generate input successfully
        return self.generate_input()

    def is_interesting(self) -> bool:
        return False

    def clone(self):
        return copy.deepcopy(self)


if __name__ == '__main__':
    options = get_generation_only_option()
    fuzzer = get_fuzzer(options["fuzzer"], 0)
    n = int(options["number"])
    output_dir = options["output_dir"]
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    time_record = []
    for i in tqdm(range(n)):
        start_time = time.perf_counter()
        path = fuzzer.generate_input()
        end_time = time.perf_counter()
        time_record.append(end_time - start_time)
        shutil.move(path, output_dir + "/" + str(i) + ".html")
    print(f"avg generation time: {sum(time_record) / len(time_record)} s")
