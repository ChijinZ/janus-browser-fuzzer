import re
from enum import Enum
import json


class CrashType(Enum):
    AddressSanitizer = 'AddressSanitizer'
    AssertionFailed = 'AssertionFailed'
    Other = 'Other'


class CrashMessage:
    def __init__(self):
        self.crashType = None
        self.errorTitle = ''
        self.errorMessage = ''
        self.summary = ''
        self.stacktrace = []
        self.errorStatement = ''
        self.logPath = ''
        self.htmlPath = ''
        self.logContent = ''
        self.hasCrash = True

    def analyze(self, logPath: str):
        """
        analyze the crash message from crash log
        """
        self.logPath = logPath
        self.htmlPath = logPath.replace('.log', '')
        with open(logPath, 'r') as f:
            self.logContent = f.read()
        lines = self.logContent.split('\n')
        length = len(lines)
        i = 0
        while i < length:
            if lines[i].startswith('ASSERTION FAILED:'):
                self.errorTitle = lines[i]
                self.crashType = CrashType.AssertionFailed
                self.errorMessage = lines[i + 1]
                i += 2
                # stacktrace
                st = []
                while re.match('[0-9]+\\s*0x[0-9a-zA-Z]*', lines[i]):
                    st.append(lines[i])
                    i += 1
                self.stacktrace = st
            elif lines[i].startswith('AddressSanitizer:'):
                self.errorTitle = lines[i]
                self.crashType = CrashType.AddressSanitizer
                i += 2
                # error message
                while re.match('==[0-9]*==', lines[i]):
                    self.errorMessage += lines[i] + '\n'
                    i += 1
                # stacktrace
                st = []
                while re.match('\\s*#[0-9]*', lines[i]):
                    s = lines[i].strip()
                    st.append(s)
                    i += 1
                self.stacktrace = st
                # summary
                while not re.match('SUMMARY:', lines[i]):
                    i += 1
                if re.match('SUMMARY:', lines[i]):
                    self.summary = lines[i]
            i += 1
        if self.crashType is None:
            self.crashType = CrashType.Other
            # record stacktrace
            i = 0
            while i < len(lines):
                if re.match('[0-9]+\\s*0x[0-9a-zA-Z]+', lines[i]):
                    st = []
                    while i < length and re.match('[0-9]+\\s*0x[0-9a-zA-Z]+', lines[i]):
                        st.append(lines[i])
                        i += 1
                    self.stacktrace = st
                i += 1
        self.findErrorStatement()
        # print("%-30s %s" % (self.crashType, self.logPath))

    def findErrorStatement(self):
        """
        find the first function call in the stacktrace
        """
        pat = '\\b[a-zA-Z_][a-zA-Z0-9_]*(::\\b[a-zA-Z_][a-zA-Z0-9_]*)*\\([^)]*\\)'
        for line in self.stacktrace:
            if re.search(pat, line):
                self.errorStatement = re.search(pat, line).group()
                break
        return self.errorStatement


class CrashMessageEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, CrashMessage):
            return {
                'logPath': obj.logPath,
                'htmlPath': obj.htmlPath,
                'crashType': obj.crashType.value,
                'errorTitle': obj.errorTitle,
                'errorMessage': obj.errorMessage,
                'summary': obj.summary,
                'stacktrace': obj.stacktrace,
                'errorStatement': obj.errorStatement,
            }
        return json.JSONEncoder.default(self, obj)