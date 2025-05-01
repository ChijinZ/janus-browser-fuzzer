import json
import random
import os
from collections import defaultdict
import threading
import sys
sys.path.append('/root/chijin_workspace/fuzzer')
from minimizer import HTMLMinimizer
import logging
from common import FuzzedBrowser
from config import get_minimizer_option
from browser_selenium import get_browser


def processCrashMessage(crashMessage: dict, index: int):
    target = os.sep.join(['minimized', str(index) + '.html'])
    crashMessage['minimizedHtmlPath'] = target
    crashMessage['minimizedLogPath'] = target + '.log'


def sample2file():
    classificationResultPath = '/root/chijin_workspace/fuzzer/crashAnalyze/classification.json'
    with open(classificationResultPath, 'r', encoding='utf-8') as fp:
        data = json.load(fp)

    record = defaultdict() # record the result of sampling
    errorType = ['AssertionFailed', 'AddressSanitizer', 'Other']
    for type in errorType:
        record[type] = defaultdict(lambda: defaultdict())

    index = 0 # for minimized files

    # Other
    case_Other = data['Other']
    for errorStatement in case_Other:
        # crash message list
        cmlst = case_Other[errorStatement]
        # randomly pick a sample
        cm = random.sample(cmlst, 1)[0]
        processCrashMessage(cm, index)
        index += 1
        record['Other'][errorStatement] = cm

    # AssertionFailed
    case_AssertionFailed = data['AssertionFailed']
    for errorMessage in case_AssertionFailed:
        record['AssertionFailed'][errorMessage] = defaultdict()
        for errorStatement in case_AssertionFailed[errorMessage]:
            # crash message list
            cmlst = case_AssertionFailed[errorMessage][errorStatement]
            # randomly pick a sample
            cm = random.sample(cmlst, 1)[0]
            processCrashMessage(cm, index)
            index += 1
            record['AssertionFailed'][errorMessage][errorStatement] = cm

    # AddressSanitizer
    case_AddressSanitizer = data['AddressSanitizer']
    for summary in case_AddressSanitizer:
        record['AddressSanitizer'][summary] = defaultdict()
        for errorStatement in case_AddressSanitizer[summary]:
            # crash message list
            cmlst = case_AddressSanitizer[summary][errorStatement]
            # randomly pick a sample
            cm = random.sample(cmlst, 1)[0]
            processCrashMessage(cm, index)
            index += 1
            record['AddressSanitizer'][summary][errorStatement] = cm

    with open('./sample2.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False, indent=2))


class minimizeThread(threading.Thread):
    def __init__(self, threadID, cm):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.cm = cm
    
    def run(self):
        options = get_minimizer_option()
        browser = get_browser(0, options["browser"], options["timeout"])
        htmlMinimizer = HTMLMinimizer(self.cm['htmlPath'], self.cm['minimizedHtmlPath'], self.cm['minimizedLogPath'], browser)
        htmlMinimizer.minimization()


def sampleFromFile():
    print('start sample from file')
    samplePath = '/root/chijin_workspace/fuzzer/crashAnalyze/sample.json'
    with open(samplePath, 'r', encoding='utf-8') as f:
        data = json.load(f)
  
    # crash messages
    cms = [] 

    # AssertionFailed
    case_AssertionFailed = data['AssertionFailed']
    for errorMessage in case_AssertionFailed:
        for errorStatement in case_AssertionFailed[errorMessage]:
            # crash sample
            cm = case_AssertionFailed[errorMessage][errorStatement]
            cms.append(cm)

    # AddressSanitizer
    case_AddressSanitizer = data['AddressSanitizer']
    for summary in case_AddressSanitizer:
        for errorStatement in case_AddressSanitizer[summary]:
            # crash sample
            cm = case_AddressSanitizer[summary][errorStatement]
            cms.append(cm)

    # Other
    case_Other = data['Other']
    for errorStatement in case_Other:
        # crash sample
        cm = case_Other[errorStatement]
        cms.append(cm)

    for i in range(len(cms)):
        output_name = cms[i]['minimizedHtmlPath'].split('/')[1]
        output_index = int(output_name.split('.')[0])
        not_finished = set([22])
        if output_index in not_finished:
            print(output_index, output_name)
            t = minimizeThread(i, cms[i])
            t.start()


if __name__ == '__main__':
    sample2file()
    sampleFromFile()
