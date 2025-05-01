import os
from optparse import OptionParser
import logging
import shutil
import hashlib

if __name__ == '__main__':
    usage = "TODO: show how to use it"
    parser = OptionParser(usage)
    parser.add_option("-d", "--result-dir", dest="result_dir", help="result directory")
    parser.add_option("-o", "--output-dir", dest="output_dir", help="output directory")
    parser.add_option("-m", "--mode", dest="mode", help="crash | interesting", default="crash")

    (options, args) = parser.parse_args()
    if len(args) != 0:
        logging.warning(f"unused arguments: {args}")
    opt = vars(options)
    r = opt["result_dir"]
    o = opt["output_dir"]
    m = opt["mode"]
    os.makedirs(o, exist_ok=True)
    for thread_path in os.listdir(r):
        path = os.path.join(r, thread_path, m)
        for file in os.listdir(path):
            if file.split(".")[-1] == "log":
                continue
            file_path = os.path.join(path, file)
            with open(file_path, "r") as f:
                h = hashlib.md5(f.read().encode("utf-8")).hexdigest()
                shutil.move(file_path, os.path.join(o, h))
                shutil.move(file_path + ".log", os.path.join(o, h + ".log"))
