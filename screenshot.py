from synthesis import visit_and_get_img_and_phash
from config import get_screenshot_option
from browser_selenium import get_browser
import logging


def main():
    logging.basicConfig(level=logging.DEBUG)
    options = get_screenshot_option()
    browser = get_browser(0, options["browser"], 5000)
    width = int(options["width"])
    height = int(options["height"])
    input_path = options["input_html_path"]
    output_path = options["output_png_path"]
    png_buf, _phash = visit_and_get_img_and_phash(file_path=input_path, browser=browser, width=width, height=height)
    with open(output_path, "wb+") as f:
        f.write(png_buf)


if __name__ == '__main__':
    main()
