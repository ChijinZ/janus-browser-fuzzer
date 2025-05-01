import copy
import os
import logging
import subprocess
import random
import sys
import shutil
import time
from tqdm import tqdm
from browser_selenium import FuzzedBrowser, get_browser
from browser_adapters.firefox import FirefoxSeleniumBrowser
from browser_adapters.webkit import WebKitSeleniumBrowser
import imagehash
from imagehash import ImageHash
from PIL import Image
from io import BytesIO
import json
from logic_domato.grammar import Grammar
from typing import Union
import logging
import re
from typing import List
from common import Transform, CounterExample, set_default
from llm_verifier import LLMVerifier
from compatibility_checker import CompatibilityResult, CompatibilityChecker
import traceback

from selenium.common.exceptions import JavascriptException

SLEEP_TIME_BETWEEN_EXEC_AND_SCREENSHOT = 0.4
HASH_SIMILAR_THRESHOLD = 0
HASH_DIFF_THRESHOLD = 20

VERIFY_NUMBER = 10
CRASH_TOLERANCE = 5
RANDOM_GRAMMAR = {"type": "grammar",
                  "creates": {"type": "tag", "tagname": "tmp"},
                  "parts": [{"type": "tag", "tagname": "cssproperty_value"}], "recursive": False}

GRAMMAR_CONTEXT = {
    'lastvar': 0,
    'lines': [],
    'variables': {},
    'force_var_reuse': False
}

CSS_PATTERN = re.compile("<style>(.*?)</style>", flags=re.DOTALL)
JS_PATTERN = re.compile("<script>(.*?)</script>", flags=re.DOTALL)
HTML_PATTERN = re.compile("<body .*?>(.*?)</body>", flags=re.DOTALL)


# if the execution successes, return png buffer and hash value (ImageHash for now);
# otherwise, return None
def visit_and_get_img_and_phash(file_path: str, browser: FuzzedBrowser, width=None, height=None,
                                overhead_record_dict=None):
    if overhead_record_dict is not None:
        start_time = time.time()
    browser.ready()
    execution_res = browser.fuzz(file_path)

    if overhead_record_dict is not None:
        if "actual_execution_time" not in overhead_record_dict:
            overhead_record_dict["actual_execution_time"] = 0.0
        overhead_record_dict["actual_execution_time"] += time.time() - start_time

    if not execution_res:
        return None, None
    try:
        time.sleep(SLEEP_TIME_BETWEEN_EXEC_AND_SCREENSHOT)
        driver = browser.get_webdriver()
        if width is not None and height is not None:
            if isinstance(browser, FirefoxSeleniumBrowser):
                # firefox is very special...
                height += 85
                # height += 179
            if isinstance(browser, WebKitSeleniumBrowser):
                # well, webkit is also special
                height += 38
            driver.set_window_size(width, height)
            time.sleep(0.5)
        png = driver.get_screenshot_as_png()
        img = Image.open(BytesIO(png))
        phash = imagehash.phash(img, hash_size=32, highfreq_factor=10)
        # if phash.__str__() == "8000000000000000" or phash.__str__() == "0000000000000000":
        #     return None, None
        return png, phash
    except BaseException as e:
        logging.info(f"get screenshot error: {e}")
        return None, None


# return true if it is a bug
def simple_check_result(r11, r12, r21, r22) -> bool:
    # logging.debug(f"result hash: {r11}, {r12}, {r21}, {r22})")
    if (is_similar_hash(r11, r21) and is_largely_different_hash(r12, r22)) or (
            is_largely_different_hash(r11, r21) and is_similar_hash(r12, r22)):
        return True
    else:
        return False


#           browser1    browser2
# html1         r11         r12
# html2         r21         r22
#
# return diff and img buffers if it is a bug
def verify_bug(h1_path: str, h2_path: str,
               browser1: FuzzedBrowser, browser2: FuzzedBrowser,
               verify_number=VERIFY_NUMBER,
               crash_tolerance=CRASH_TOLERANCE) -> (Union[dict, None], Union[dict, None]):
    crash_cnt = 0
    diff = None
    img_files = None
    for _ in range(verify_number):
        img11, r11 = visit_and_get_img_and_phash(h1_path, browser1)
        img12, r12 = visit_and_get_img_and_phash(h1_path, browser2)
        img21, r21 = visit_and_get_img_and_phash(h2_path, browser1)
        img22, r22 = visit_and_get_img_and_phash(h2_path, browser2)
        if None in [r11, r12, r21, r22]:
            crash_cnt += 1
            continue
        if crash_cnt > crash_tolerance:
            return None, None
        if not simple_check_result(r11, r12, r21, r22):
            return None, None
        else:
            img_files = {"img11": img11, "img12": img12, "img21": img21, "img22": img22}
            diff = {"diff1": abs(r11 - r21), "diff2": abs(r12 - r22)}
    return diff, img_files


def is_largely_different_hash(r1, r2) -> bool:
    return abs(r1 - r2) >= HASH_DIFF_THRESHOLD


def is_similar_hash(r1, r2) -> bool:
    return abs(r1 - r2) <= HASH_SIMILAR_THRESHOLD


class EquivalenceSynthesizer(object):
    def __init__(self, id):
        self.id = id
        path = os.path.dirname(__file__)
        path = os.path.join(path, "logic_domato/generator.py")
        if not os.path.exists(path):
            logging.error(f"doesn't have {path} doens't exist")
            exit()
        self.domato_path = path
        self.tmp_path = "/tmp/logic_domato-fuzzer/tmpoutput-" + str(self.id) + "pid" + str(
            os.getpid()) + "rand" + str(random.randbytes(16).hex())

        self.target_file = os.path.join(self.tmp_path, "tmp.html")
        self.target_file2 = os.path.join(self.tmp_path, "tmp2.html")
        # if os.getenv("ENABLE_RULE_MAP") is not None:
        #     os.environ["RULE_SEQ_PATH"] = self.target_file + ".seq"
        self.p = None
        self.new_child()

        # transform_functions[Element Type][CSS Property] = [v1->v2, ...]
        # e.g.
        # tran_funcs["HTMLUListElement"]["-webkit-border-vertical-spacing"] = [('0px', '1px'), ...]
        self.transform_functions = {}
        self.transform_blacklist = {}
        # current_trans = (Element Type, CSS Property, v1, v2)
        self.current_trans = Transform(None, None, None, None)
        self.style_dic = {}
        self.grammar = Grammar()
        self.grammar.parse_from_file(
            os.path.join(os.path.dirname(__file__), 'logic_domato/rules/css.txt'))
        self.comp_checker = CompatibilityChecker()

        self.print_overhead_for_exp = False
        if os.getenv("PRINT_OVERHEAD_FOR_EXP") is not None:
            if os.getenv("PRINT_OVERHEAD_FOR_EXP") in ["True", "true", "1"]:
                self.print_overhead_for_exp = True

        if os.getenv("PROPERTY_DIC_PATH") is not None:
            p = os.environ["PROPERTY_DIC_PATH"]
            with open(p, "r") as f:
                self.style_dic = json.load(f)
        else:
            logging.info(f"[{self.id}]:there is no PROPERTY_DIC_PATH in env var, exit")
            exit()

    # return counter example if the result is worth to save
    def transform(self, browser1: FuzzedBrowser, browser2: FuzzedBrowser) \
            -> Union[CounterExample, None]:
        overhead_info = None

        if self.print_overhead_for_exp:
            overhead_info = {}
            start_time = time.time()

        original_path = self.generate_input()

        if self.print_overhead_for_exp:
            overhead_info["generate_input"] = time.time() - start_time

        transformed_path = self.target_file2

        if self.print_overhead_for_exp:
            start_time = time.time()

        img11, r11 = visit_and_get_img_and_phash(original_path, browser1, overhead_record_dict=overhead_info)

        if self.print_overhead_for_exp:
            overhead_info["browser1_execution_for_input1"] = time.time() - start_time
            start_time = time.time()

        img12, r12 = visit_and_get_img_and_phash(original_path, browser2, overhead_record_dict=overhead_info)

        if self.print_overhead_for_exp:
            overhead_info["browser2_execution_for_input1"] = time.time() - start_time

        if None in [r11, r12]:
            # error occurs when visiting and screenshotting
            return None

        if self.print_overhead_for_exp:
            start_time = time.time()

        driver = browser1.get_webdriver()
        try:
            document_length = driver.execute_script("return document.all.length")
        except BaseException as e:
            logging.error(f"cannot execute script for document_length: {e}")
            return None
        if document_length == 0:
            return None
        chosen_element = random.randint(0, document_length - 1)
        try:
            type_of_chosen_element = driver.execute_script(
                f"return document.all[{chosen_element}].constructor.name")
            element_id = driver.execute_script(
                f"return document.all[{chosen_element}].id")
            style_of_chosen_element = {}
            for i in range(document_length):
                style_of_chosen_element = driver.execute_script(
                    f"style = window.getComputedStyle(document.all[{chosen_element}]);"
                    "dic = {};"
                    "for(var i = 0; i < style.length; i++)"
                    "{var prop = style[i];"
                    "if(typeof style[prop] !== 'function')"
                    "{ dic[prop] = style[prop] }};"
                    "return dic")
                if len(style_of_chosen_element.keys()) != 0:
                    break
                if i >= document_length - 1:
                    return None
        except BaseException as e:
            logging.error(f"cannot execute script for chosen_element: {e}")
            # except JavascriptException:
            return None
        for _ in range(1000):
            chosen_prop = random.choice(list(style_of_chosen_element))
            chosen_original_value = style_of_chosen_element[chosen_prop]
            if self.comp_checker.check_css_for_browsers(
                    chosen_prop, [chosen_original_value],
                    ["chrome", "firefox", "webkitgtk"]) == CompatibilityResult.Compatible:
                break
        if chosen_prop in self.style_dic:
            rule = random.choice(self.style_dic[chosen_prop])
            # print(rule)
            new_value = self.grammar._expand_rule("", rule, copy.deepcopy(GRAMMAR_CONTEXT), 0,
                                                  False)
        else:
            new_value = self.grammar._expand_rule("", RANDOM_GRAMMAR,
                                                  copy.deepcopy(GRAMMAR_CONTEXT), 0, False)

        # construct a js statement that renew the property
        if element_id and element_id != "":
            append_line = \
                f"document.getElementById(\"{element_id}\").style[\"{chosen_prop}\"] = \"{new_value}\""
        else:
            append_line = f"document.all[{chosen_element}].style[\"{chosen_prop}\"] = \"{new_value}\""
        lines = []
        with open(original_path, "r") as f:
            lines = f.readlines()
        with open(transformed_path, "w+") as f:
            for line in lines:
                f.write(line)
                if line.__contains__("/* appending new logic for equivalence synthesis */"):
                    f.write(append_line)

        self.current_trans = Transform(type_of_chosen_element, chosen_prop, chosen_original_value,
                                       new_value)

        if self.print_overhead_for_exp:
            overhead_info["transformation"] = time.time() - start_time
            start_time = time.time()

        img21, r21 = visit_and_get_img_and_phash(transformed_path, browser1, overhead_record_dict=overhead_info)

        if self.print_overhead_for_exp:
            overhead_info["browser1_execution_for_input2"] = time.time() - start_time
            start_time = time.time()

        img22, r22 = visit_and_get_img_and_phash(transformed_path, browser2, overhead_record_dict=overhead_info)

        if self.print_overhead_for_exp:
            overhead_info["browser2_execution_for_input2"] = time.time() - start_time
            start_time = time.time()

        if None in [r21, r22]:
            # error occurs when visiting and screenshotting
            return None

        is_bug = self.result_check(r11, r12, r21, r22)

        if self.print_overhead_for_exp:
            overhead_info["result_check"] = time.time() - start_time
            logging.info(f"[{self.id}]: overhead info: {overhead_info}")

        if is_bug:
            diff, img_files = verify_bug(original_path, transformed_path, browser1, browser2)
            if diff is not None:
                counterexample = CounterExample(self.current_trans, original_path, transformed_path,
                                                r11, r12, r21, r22, img_files)
                return counterexample
            else:
                logging.info(f"[{self.id}]: verification failed")
                return None
        else:
            return None

    #           browser1    browser2
    # html1         r11         r12
    # html2         r21         r22
    #
    # if there is a contradiction bug, return true
    def result_check(self, r11, r12, r21, r22):
        # logging.info(f"[{self.id}]: result hash: {r11}, {r12}, {r21}, {r22})")
        el, prop, v1, v2 = self.current_trans.get_tuple()
        if is_similar_hash(r11, r21) and is_similar_hash(r12, r22):
            # it seems like a legal trans, add it to our trans_funcs
            if el not in self.transform_functions:
                self.transform_functions[el] = {}
            if prop not in self.transform_functions[el]:
                self.transform_functions[el][prop] = set()
            if not (el in self.transform_blacklist and prop in self.transform_blacklist[el]
                    and (v1, v2) in self.transform_blacklist[el][prop]):
                self.transform_functions[el][prop].add((v1, v2))
        elif not is_similar_hash(r11, r21) and not is_similar_hash(r12, r22):
            # it seems like an illegal trans, add it to our trans_blacklist
            if el not in self.transform_blacklist:
                self.transform_blacklist[el] = {}
            if prop not in self.transform_blacklist[el]:
                self.transform_blacklist[el][prop] = set()
            self.transform_blacklist[el][prop].add((v1, v2))

            if el in self.transform_functions and prop in self.transform_functions[el] \
                    and (v1, v2) in self.transform_functions[el][prop]:
                self.transform_functions[el][prop].remove((v1, v2))
        elif (is_similar_hash(r11, r21) and r12 != r22) or \
                (r11 != r21 and is_similar_hash(r12, r22)):
            # contradiction, we found a bug!
            # note that we restrict the constraint for less false positives
            return True

        return False

    def new_child(self):
        self.p = subprocess.Popen(["python3", self.domato_path],
                                  stdout=subprocess.PIPE,
                                  stdin=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)
        self.p.stdin.write(f"init: {self.target_file}\n".encode('utf-8'))
        self.p.stdin.flush()
        while True:
            msg = self.p.stdout.readline().decode("utf-8").strip()
            if msg == "received":
                break
            elif msg != "":
                print(f"[{self.id}]: msg from domato process: {msg}")
        os.makedirs(self.tmp_path, exist_ok=True)

    def __del__(self):
        self.p.terminate()

    def generate_input(self) -> str:
        try:
            # logging.debug(f"domato output: {p.stdout.read()}")
            self.p.stdin.write("generate\n".encode("utf-8"))
            self.p.stdin.flush()
            while True:
                if self.p.poll() is not None:
                    raise Exception("fuzzer process has been terminated")
                msg = self.p.stdout.readline().decode("utf-8").strip()
                if msg == "done":
                    break
                elif msg != "":
                    logging.info(f"[{self.id}]: msg from domato process: {msg}")
            return self.target_file
        except BaseException as e:
            logging.info(f"[{self.id}]: fuzzer error: {e}")
            self.p.terminate()
            self.new_child()
            return self.generate_input()

    def dump_trans(self, output_file_path):
        # print(self.transform_functions)
        with open(output_file_path, "w+") as f:
            json.dump({"func": self.transform_functions, "blacklist": self.transform_blacklist}, f,
                      default=set_default)


def fill_html(content: str, css_: List[str], js_: List[str], html_: List[str]) -> str:
    css = []
    js = []
    html = []
    for c in css_:
        if c.strip() != "":
            css.append(c)
    for j in js_:
        if j.strip() != "":
            js.append(j)
    for h in html_:
        if h.strip() != "":
            html.append(h)

    c1 = CSS_PATTERN.sub(lambda x: "<style>\n" + "\n".join(css) + "</style>", content)
    c2 = JS_PATTERN.sub(lambda x: "<script>\n" + "\n".join(js) + "</script>", c1)
    c3 = HTML_PATTERN.sub(lambda x: "<body onload=jsfuzzer()>\n" + "\n".join(html) + "</body>", c2)
    return c3


def save_content_to_fs(h1, h2, h1_path, h2_path):
    with open(h1_path, "w+") as f:
        f.write(h1)
    with open(h2_path, "w+") as f:
        f.write(h2)


def logic_minimizer(h2_file_path: str, browser1_name: str,
                    browser2_name: str, browser3_name, timeout: int, id: int, use_llm=False) -> Union[dict, None]:
    browser1 = get_browser(threadId=id, browser_name=browser1_name, timeout=timeout)
    browser2 = get_browser(threadId=id, browser_name=browser2_name, timeout=timeout)

    tmp_dir = "/tmp/minimizer/" + str(id)
    os.makedirs(tmp_dir, exist_ok=True)
    h1_path = os.path.join(tmp_dir, "h1.html")
    h2_path = os.path.join(tmp_dir, "h2.html")
    if not h2_file_path.endswith(".h2.html"):
        logging.error(f"[{id}]: the h2 file does not end with \".h2.html\"")
    res_path = h2_file_path[:-8] + ".min"
    res_h1_path = res_path + ".h1.html"
    res_h2_path = res_path + ".h2.html"
    trans_path = h2_file_path[:-8] + ".trans"
    res_llm_path = res_path + ".llm.json"

    with open(h2_file_path, "r") as f:
        content = f.read()
        css = re.search(CSS_PATTERN, content).group(1).split("\n")
        js = re.search(JS_PATTERN, content).group(1).split("\n")
        html = re.search(HTML_PATTERN, content).group(1).split("\n")
    js_original = []
    for i, val in enumerate(js):
        if val == "/* appending new logic for equivalence synthesis */":
            js_original += js[:i + 1]
            js_original += js[i + 2:]
            break
    if len(js_original) != len(js) - 1:
        logging.error(f"[{id}]: there is no trans statement")
        return None
    new_html = copy.deepcopy(html)
    new_css = copy.deepcopy(css)

    logging.debug(f"[{id}]: process html")
    cnt = 0
    for i in tqdm(range(len(html)), disable=True):
        statement = new_html[i]
        new_html[i] = ""
        h1 = fill_html(content, css, js_original, new_html)
        h2 = fill_html(content, css, js, new_html)
        save_content_to_fs(h1, h2, h1_path, h2_path)
        diff, img_files = verify_bug(h1_path, h2_path, browser1, browser2,
                                     verify_number=3, crash_tolerance=1)
        if diff is None:
            new_html[i] = statement
        else:
            # successfully minimize
            cnt += 1
    logging.info(f"[{id}]: html remove rate: {cnt}/{len(html)}")

    logging.debug(f"[{id}]: process css")
    cnt = 0
    for i in tqdm(range(len(css)), disable=True):
        statement = new_css[i]
        new_css[i] = ""
        h1 = fill_html(content, new_css, js_original, new_html)
        h2 = fill_html(content, new_css, js, new_html)
        save_content_to_fs(h1, h2, h1_path, h2_path)
        diff, img_files = verify_bug(h1_path, h2_path, browser1, browser2,
                                     verify_number=3, crash_tolerance=1)
        if diff is None:
            new_css[i] = statement
        else:
            # successfully minimize
            cnt += 1
    logging.info(f"[{id}]: css remove rate: {cnt}/{len(css)}")

    h1 = fill_html(content, new_css, js_original, new_html)
    h2 = fill_html(content, new_css, js, new_html)
    save_content_to_fs(h1, h2, h1_path, h2_path)
    diff, img_files = verify_bug(h1_path, h2_path, browser1, browser2,
                                 verify_number=3, crash_tolerance=1)

    if diff is None or img_files is None:
        logging.error(f"[{id}]: fail to minimize! file: {h2_file_path}")
        return None

    for key, val in img_files.items():
        with open(res_path + f".{key}.png", "wb+") as f:
            f.write(val)

    # ok, we got a verified buggy behavior
    # let's check out the behavior of browser3
    browser3 = get_browser(threadId=id, browser_name=browser3_name, timeout=timeout)
    img13, r13 = visit_and_get_img_and_phash(h1_path, browser3)
    img23, r23 = visit_and_get_img_and_phash(h2_path, browser3)
    if None in [r13, r23]:
        logging.info("firefox return None")
        return None

    diff["diff3"] = abs(r13 - r23)
    with open(res_path + ".img13.png", "wb+") as f:
        f.write(img13)
    with open(res_path + ".img23.png", "wb+") as f:
        f.write(img23)

    shutil.move(h1_path, res_h1_path)
    shutil.move(h2_path, res_h2_path)

    if use_llm:
        llm = LLMVerifier()
        try:
            with open(trans_path, "r") as f:
                json_obj = json.load(f)
                trans = Transform.fromJSON(json.loads(json_obj["trans"]))
            llm_res = llm.llm_verify(res_h1_path, res_h2_path, trans)
            with open(res_llm_path, "w+") as f:
                json.dump(llm_res.to_dict(), f, sort_keys=True)
        except BaseException as e:
            logging.error(f"[{id}]: error during llm verification: {e}. traceback: {traceback.format_exc()}")

    with open(res_path + f".diff", "w+") as f:
        json.dump(diff, f)

    logging.info(f"[{id}]: done: {res_path}")
    return diff
