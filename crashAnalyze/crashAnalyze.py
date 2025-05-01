from crashMessage import CrashMessage, CrashMessageEncoder, CrashType

from collections import defaultdict
import os
import json

if __name__ == '__main__':
    result = defaultdict(lambda: defaultdict())

    resultsPath = '/root/chijin_workspace/results'
    for _crashDirectory in os.listdir(resultsPath):
        print(_crashDirectory)
        if not _crashDirectory.startswith('crash'):
            continue
        for threadDirectory in os.listdir(os.sep.join([resultsPath, _crashDirectory])):
            print('  ', threadDirectory)
            crashDirectory = os.sep.join([resultsPath, _crashDirectory, threadDirectory, 'crash'])
            for file in os.listdir(crashDirectory):
                if not file.endswith('.log'):
                    continue
                fullPath = os.sep.join([crashDirectory, file])
                cm = CrashMessage()
                cm.analyze(fullPath)

                if cm.crashType == CrashType.AddressSanitizer:
                    if cm.summary not in result[CrashType.AddressSanitizer.value]:
                        result[CrashType.AddressSanitizer.value][cm.summary] = defaultdict(list)
                    result[CrashType.AddressSanitizer.value][cm.summary][cm.errorStatement].append(cm)
                elif cm.crashType == CrashType.AssertionFailed:
                    if cm.errorMessage not in result[cm.crashType.value]:
                        result[cm.crashType.value][cm.errorMessage] = defaultdict(list)
                    result[cm.crashType.value][cm.errorMessage][cm.errorStatement].append(cm)
                elif cm.crashType == CrashType.Other:
                    if cm.errorStatement not in result[cm.crashType.value]:
                        result[cm.crashType.value][cm.errorStatement] = []
                    result[cm.crashType.value][cm.errorStatement].append(cm)

    with open('classification.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(result, ensure_ascii=False, indent=2, cls=CrashMessageEncoder))