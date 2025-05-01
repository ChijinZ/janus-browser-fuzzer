import config
import os
import logging
import signal
from selenium.webdriver.chrome.webdriver import WebDriver
import json
import shutil
from imagehash import ImageHash
import re

try:
    from typing import Self  # after python3.11
except:
    from typing_extensions import Self  # before Python3.11


def create_output_directory(path):
    # path = os.environ.get("OUTPUT_PATH")
    # if path is None:
    #     logging.error(f"doesn't have OUTPUT_PATH env var")
    #     exit()
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


class Timeout:
    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message

    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, type, value, traceback):
        signal.alarm(0)


class FuzzedBrowser(object):
    def ready(self):
        pass

    def clone(self):
        pass

    def fuzz(self, path: str) -> bool:
        pass

    def message(self) -> str:
        pass

    def get_webdriver(self) -> WebDriver:
        pass


def set_default(obj):
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, Transform):
        return obj.toJSON()
    if isinstance(obj, ImageHash):
        return obj.__str__()
    raise TypeError


class Transform(object):
    def __init__(self, el_type, prop, original_value, new_value):
        self.el_type = el_type
        self.prop = prop
        self.original_value = original_value
        self.new_value = new_value

    def get_tuple(self):
        return self.el_type, self.prop, self.original_value, self.new_value

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True)

    @staticmethod
    def fromJSON(json_obj) -> Self:
        trans = Transform(el_type=json_obj["el_type"], prop=json_obj["prop"],
                          original_value=json_obj["original_value"], new_value=json_obj["new_value"])
        return trans


class CounterExample(object):
    def __init__(self, trans: Transform, h1: str, h2: str, r11, r12, r21, r22, img_files):
        self.trans = trans
        self.h1 = h1
        self.h2 = h2
        self.r11 = r11
        self.r12 = r12
        self.r21 = r21
        self.r22 = r22
        self.img_files = img_files

    def save_to_path(self, output_dir: str, file_id: str):
        output_path = os.path.join(output_dir, file_id)
        h1_path = output_path + ".h1.html"
        h2_path = output_path + ".h2.html"
        trans_path = output_path + ".trans"
        shutil.move(self.h1, h1_path)
        shutil.move(self.h2, h2_path)
        with open(trans_path, "w+") as f:
            json.dump({"trans": self.trans, "r11": self.r11, "r12": self.r12, "r21": self.r21,
                       "r22": self.r22,
                       "diff1": abs(self.r11 - self.r21), "diff2": abs(self.r12 - self.r22)}, f,
                      default=set_default)
        for key, val in self.img_files.items():
            with open(output_path + f".{key}.png", "wb+") as f:
                f.write(val)

    @staticmethod
    def load_from_path(output_dir: str, file_id: str) -> Self:
        output_path = os.path.join(output_dir, file_id)
        h1_path = output_path + ".h1.html"
        h2_path = output_path + ".h2.html"
        trans_path = output_path + ".trans"
        with open(trans_path, "r") as f:
            loaded_json = json.load(f)
            trans = loaded_json["trans"]
            r11 = loaded_json["r11"]
            r12 = loaded_json["r12"]
            r21 = loaded_json["r21"]
            r22 = loaded_json["r22"]

        img_files = {}
        pattern = re.compile(rf"{file_id}\.(.*?)\.png")
        for file_name in os.listdir(output_dir):
            matched = pattern.match(file_name)
            if matched is not None:
                key = matched.groups()[1]
                img_path = os.path.join(output_path, file_name)
                with open(img_path, "rb") as f:
                    img_file = f.read()
                    img_files[key] = img_file

        assert len(img_files.keys()) != 0

        return CounterExample(trans=trans, h1=h1_path, h2=h2_path,
                              r11=r11, r12=r12, r21=r21, r22=r22,
                              img_files=img_files)
