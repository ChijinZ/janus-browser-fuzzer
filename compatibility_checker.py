import json
import traceback
from typing import List
from enum import Enum
import os

BROWSER_NAME_DICT = {"chrome": "chrome", "chromium": "chrome", "firefox": "firefox", "webkitgtk": "safari",
                     "webkitwpe": "safari", "safari": "safari"}


class CompatibilityResult(str, Enum):
    NoRecord = "NoRecord"
    Compatible = "Compatible"
    InCompatible = "InCompatible"
    InternalError = "InternalError"


def is_special_prop(prop: str) -> bool:
    for var in ["font", "border", "blend", "column", "background-image"]:
        if var in prop:
            return True

    return False


def is_special_value(value: str) -> bool:
    for var in ["-webkit-", "-moz-"]:
        if var in value:
            return True
    return False


class CompatibilityChecker:
    def __init__(self):
        self.bcd = None
        parent_dir = os.path.abspath(os.path.dirname(__file__))

        with open(parent_dir + "/llm_helper/mdn_bcd.json", "r") as f:
            bcd = json.load(f)
            self.bcd = bcd["css"]["properties"]

    def check_css_for_browsers(self, prop: str, value_list: List[str],
                               browser_list: List[str]) -> CompatibilityResult:
        if self.bcd is None:
            return CompatibilityResult.InternalError

        if prop not in self.bcd:
            return CompatibilityResult.NoRecord

        if is_special_prop(prop):
            return CompatibilityResult.InCompatible

        for value in value_list:
            if is_special_value(value):
                return CompatibilityResult.InCompatible

        prop_dict = self.bcd[prop]

        for name in browser_list:
            browser_name = BROWSER_NAME_DICT[name.lower()]
            comp_info = prop_dict["__compat"]["support"][browser_name]
            assert isinstance(comp_info, dict) or isinstance(comp_info, list)
            if isinstance(comp_info, dict) and comp_info["version_added"] is False:
                return CompatibilityResult.InCompatible
            if isinstance(comp_info, list) and comp_info[0]["version_added"] is False:
                return CompatibilityResult.InCompatible

        for value in value_list:
            if any(char.isdigit() for char in value):
                continue
            if value not in prop_dict:
                continue
            try:
                support_dict = prop_dict[value]["__compat"]["support"]
                for name in browser_list:
                    browser_name = BROWSER_NAME_DICT[name.lower()]
                    assert browser_name in support_dict

                    version_res = None
                    if isinstance(support_dict[browser_name], dict):
                        assert "version_added" in support_dict[browser_name]
                        version_res = support_dict[browser_name]["version_added"]
                    elif isinstance(support_dict[browser_name], list):
                        assert "version_added" in support_dict[browser_name][0]
                        version_res = support_dict[browser_name][0]["version_added"]
                    else:
                        raise AssertionError

                    if version_res is False:
                        return CompatibilityResult.InCompatible
            except AssertionError as e:
                raise e
            except BaseException as e:
                traceback.print_exception(e)
                return CompatibilityResult.InternalError

        return CompatibilityResult.Compatible
