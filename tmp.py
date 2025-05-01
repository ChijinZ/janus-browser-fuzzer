from selenium.webdriver.webkitgtk import webdriver, options
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

import os
import signal
import psutil
import time

webkit_driver_path = None
binary_location = None
url = None
if "WEBKIT_WEBDRIVER_PATH" in os.environ:
    webkit_driver_path = os.environ["WEBKIT_WEBDRIVER_PATH"]
else:
    print("didn't set WEBKIT_WEBDRIVER_PATH env var")
    exit(1)
if "WEBKIT_BINARY_PATH" in os.environ:
    binary_location = os.environ["WEBKIT_BINARY_PATH"]
else:
    print("didn't set WEBKIT_BINARY_PATH env var")
    exit(1)
if "TMP_URL_PATH" in os.environ:
    url = f"file://{os.environ['TMP_URL_PATH']}"
else:
    print("didn't set TMP_URL_PATH env var")
    exit(1)

caps = DesiredCapabilities.WEBKITGTK.copy()
# caps["pageLoadStrategy"] = "eager"
caps["pageLoadStrategy"] = "normal"

option = options.Options()
option.binary_location = binary_location
option.add_argument("--automation")
print("start browser")
browser = webdriver.WebDriver(
    executable_path=webkit_driver_path,
    options=option,
    desired_capabilities=caps,
    service_log_path="/tmp/bb")
browser.set_page_load_timeout(5)
browser.command_executor.set_timeout(5)
print("successfully start")


def kill_browser(browser):
    webdriver_pid = browser.service.process.pid
    process = psutil.Process(webdriver_pid)
    child_procs = process.children(recursive=True)
    print(f"try to kill webdriver pid: {webdriver_pid}")
    try:
        os.kill(webdriver_pid, signal.SIGINT)
        print(f"successfully kill webdriver pid: {webdriver_pid}")
    except BaseException as e:
        print(f"cannot kill webdriver pid :{webdriver_pid}; cause: {e}")
    for pid in child_procs:
        print(f"try to kill pid: {pid.pid}")
        try:
            os.kill(pid.pid, signal.SIGINT)
            print(f"successfully kill pid {pid.pid}")
        except BaseException as e:
            print(f"cannot kill {pid.pid}; cause: {e}")


for _ in range(1):
    browser.switch_to.window(browser.window_handles[0])
    browser.execute_script("window.open('','_blank');")
    browser.switch_to.window(browser.window_handles[1])
    print(f"start! goto: {url}")
    try:
        # browser.get("https://www.baidu.com")
        browser.get(url)
        print("finish get")
        browser.close()
    except BaseException as e:
        try:
            print(f"not finish, because: {e}")
            print(browser.close())
            print("timeout!")
        except WebDriverException as e:
            print(f"crash! message: {e}")
            try:
                kill_browser(browser)

                print("killed")
            except BaseException as e:
                print(f"cannot kill: {e}")

            # browser = webdriver.WebDriver(
            #     executable_path="/home/jin/.cache/ms-playwright/webkit-1516/minibrowser-gtk/bin/WebKitWebDriver",
            #     options=option,
            #     desired_capabilities=caps)
