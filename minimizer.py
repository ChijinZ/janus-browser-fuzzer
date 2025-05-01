from common import FuzzedBrowser
from config import get_minimizer_option
from browser_selenium import get_browser
import logging
from enum import Enum
import queue
import time
import os
from datetime import datetime, timedelta


class HtmlType(Enum):
    body = 0
    css = 1
    script = 2


def is_error(message):
    return message.find('ASSERTION FAILED') != -1 or message.find('AddressSanitizer') != -1


class HTMLMinimizer():
    def __init__(self, input_path: str, output_path: str, error_path: str, browser: FuzzedBrowser) -> None:
        self.input_path = input_path
        self.output_path = output_path
        self.error_path = error_path
        logFilename = os.path.basename(output_path).replace('.html', '.log')
        self.log_path = f'/root/chijin_workspace/fuzzer/log/{logFilename}'
        tmpHtmlFilename = os.path.basename(output_path)
        self.tmp_path = f'/root/chijin_workspace/fuzzer/tmp/{tmpHtmlFilename}'
        self.browser = browser
        self.body_lst, self.css_lst, self.script_lst = self.__parse_html()
    
    def log(self, s):
        now_time = datetime.now()
        utc_time = now_time - timedelta(hours=8)  # UTC只是比北京时间提前了8个小时
        utc_time = utc_time.strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_path, 'a') as f:
            f.write('%s: ' % utc_time)
            f.write('%s\n' % s)

    def __parse_html(self):
        '''
        提取出html中的不同部分，因为html不是特别规范，beautifulsoup提取有问题，暂时做人工提取，但是要考虑html的格式
        '''
        css_lst = []
        body_lst = []
        script = []
        with open(self.input_path, 'r') as f:
            lines = [l.strip() for l in f.readlines()]
            i = 0
            while i < len(lines):
                if lines[i].startswith('<style'):
                    i += 1
                    while not lines[i].startswith('</style'):
                        css_lst.append(lines[i])
                        i += 1
                if lines[i].startswith('<script'):
                    i += 1
                    while not lines[i].startswith('</script'):
                        script.append(lines[i])
                        i += 1
                if lines[i].startswith('<body'):
                    i += 1
                    while not lines[i].startswith('</html'):
                        body_lst.append(lines[i])
                        i += 1
                    body_lst.pop()
                i += 1

        # function需要划分成每个函数，然后每个函数里面的语句
        script_lst = []
        i = 0
        while i < len(script):
            if script[i].startswith('function'):
                cnt = script[i].count('{') - script[i].count('}')
                fun = [script[i]]
                while not cnt == 0:
                    i += 1
                    cnt = cnt + script[i].count('{') - script[i].count('}')
                    fun.append(script[i])
                script_lst.append(fun)
            i += 1
        return body_lst, css_lst, script_lst

    def __generate_html(self, body_lst, css_lst, script_lst) -> str:
        b_lst = body_lst
        c_lst = css_lst
        s_lst = script_lst
        body_str = '\n'.join(b_lst)
        css_str = '\n'.join(c_lst)
        script_str = '\n'.join([s for function in s_lst for s in function]) # 包含多个函数
        runcount_def = r"var runcount = {'jsfuzzer':0, 'eventhandler1':0, 'eventhandler2':0, 'eventhandler3':0, 'eventhandler4':0, 'eventhandler5':0}"
        ret = '<html>\n<head>\n<style>\n{}\n</style>\n<script>\n' \
            '{}\n{}\n</script>\n</head>\n<body onload=jsfuzzer()>' \
            '\n{}\n</body>\n</html>'.format(css_str, runcount_def, script_str, body_str)
        ret = '\n'.join([l for l in ret.split('\n') if len(l) != 0])
        return ret

    def __judge_html(self, body_lst, css_lst, script_lst) -> bool:
        self.log('judge_html')
        file = self.__generate_html(body_lst, css_lst, script_lst)

        with open(self.tmp_path, 'w') as f:
            f.write(file)
        self.browser.ready()
        is_normal_execution = self.browser.fuzz(self.tmp_path)
        # add judge through message
        if (is_error(self.browser.message())):
            is_normal_execution = False
        self.log('judge_html ' + str(is_normal_execution))
        if not is_normal_execution:
            self.log(self.browser.message())
        return not is_normal_execution

    def __binary(self, target_lst, type: HtmlType):
        '''
        二分缩减
        '''
        # deep copy script_lst
        s = []
        for i in range(len(self.script_lst)):
            s.append(self.script_lst[i].copy())
        # current config of html(body, css, script)
        total = [self.body_lst.copy(), self.css_lst.copy(), s]

        if type == HtmlType.body or type == HtmlType.css:
            l = 0
            r = len(target_lst)
            q = queue.Queue()
            q.put((l,r))
            while not q.empty():
                l, r = q.get()
                m = int((l+r)/2)
                self.log(f'binary {l} - {r}')
                # 1. 前半段置为空
                for j in range(l, m):
                    total[type.value][j] = ''
                flag1 = self.__judge_html(total[0], total[1], total[2]) # flag=True表示出现crash
                for j in range(l, m):
                    total[type.value][j] = target_lst[j]

                # 2. 后半段置为空
                for j in range(m, r):
                    total[type.value][j] = ''
                flag2 = self.__judge_html(total[0], total[1], total[2])
                for j in range(m, r):
                    total[type.value][j] = target_lst[j]

                if type == HtmlType.body:
                    self.log(f'body-{l}-{m}-{flag1}-{m}-{r}-{flag2}')
                elif type == HtmlType.css:
                    self.log(f'css-{l}-{m}-{flag1}-{m}-{r}-{flag2}')
                
                # 两个都为True，证明前半段和后半段单独都可能触发bug，这样选择保留前半段即可，然后继续对前半段做递归
                if flag1 and flag2:
                    for j in range(m, r):
                        target_lst[j] = ''
                        total[type.value][j] = ''
                    if l < m - 1:
                        q.put((l, m))
                    continue

                if flag1:
                    for j in range(l, m):
                        target_lst[j] = ''
                        total[type.value][j] = ''
                else:
                    if l < m - 1:
                        q.put((l,m))
                if flag2:
                    for j in range(m, r):
                        target_lst[j] = ''
                        total[type.value][j] = ''
                else:
                    if m < r - 1:
                        q.put((m,r))
        # 多个函数逐一处理
        elif type == HtmlType.script:
            for i in range(len(target_lst)):
                func = target_lst[i]
                # 如果函数小于一行
                if len(func) <= 1:
                    total[type.value][i] = ['']
                    flag = self.__judge_html(total[0], total[1], total[2])
                    total[type.value][i] = func
                    if flag:
                        target_lst[i] = ['']
                        total[type.value][i] = ['']
                    continue
                # 如果有多行
                head = func[0]
                l = 1
                r = len(func) - 1
                q = queue.Queue()
                q.put((l,r))
                while not q.empty():
                    l, r = q.get()
                    m = int((l + r) / 2)
                    self.log(f'{head} {l} - {r}')
                    # 1. 前半段置为空
                    for j in range(l,m):
                        total[type.value][i][j] = ''
                    flag1 = self.__judge_html(total[0], total[1], total[2])
                    for j in range(l,m):
                        total[type.value][i][j] = func[j]

                    # 2. 后半段置为空
                    for j in range(m, r):
                        total[type.value][i][j] = ''
                    flag2 = self.__judge_html(total[0], total[1], total[2])
                    for j in range(m, r):
                        total[type.value][i][j] = func[j]

                    self.log(f'{head}-{l}-{m}-{flag1}-{m}-{r}-{flag2}')

                    # 两个都为True，证明前半段和后半段单独都可能触发bug，这样选择保留前半段即可，然后继续对前半段做递归
                    if flag1 and flag2:
                        for j in range(m, r):
                            target_lst[i][j] = ''
                            total[type.value][i][j] = ''
                        if l < m - 1:
                            q.put((l, m))
                        continue
                    
                    if flag1:
                        for j in range(l, m):
                            target_lst[i][j] = ''
                            total[type.value][i][j] = ''
                    else:
                        if l < m - 1:
                            q.put((l,m))
                    if flag2:
                        for j in range(m, r):
                            target_lst[i][j] = ''
                            total[type.value][i][j] = ''
                    else:
                        if m <  r - 1:
                            q.put((m,r))

    def minimization(self) -> bool:
        """
        Note:
        Usage of FuzzedBrowser ( perhaps you can also see the main.py :) ): 
        - ``FuzzedBrowser.ready()`` need to be called before fuzz()
        - ``FuzzedBrowser.fuzz(path: Path) -> bool`` takes a path for fuzzing and return true if is normal execution
        - ``FuzzedBrowser.message() -> -> str`` return the message of this execution 
        """
        self.log(f'minimize {self.input_path} starts!')

        # see if the original html can trigger crash, if not: return False
        self.log('see if the original html can trigger crash')
        for i in range(10):
            self.browser.ready()
            is_normal_execution = self.browser.fuzz(self.input_path)
            if is_error(self.browser.message()):
                is_normal_execution = False
            if not is_normal_execution:
                break
            else:
                if i == 9:
                    print(f'{self.input_path} doesn\'t trigger crash')
                    return False

        # reduce css
        self.log('reduce css')
        # self.__binary(self.css_lst, HtmlType.css)
        # reduce script
        self.log('reduce script')
        self.__binary(self.script_lst, HtmlType.script)
        # reduce body
        self.log('reduce body')
        self.__binary(self.body_lst, HtmlType.body)

        file = self.__generate_html(self.body_lst, self.css_lst, self.script_lst)
        # store html
        with open(self.output_path, 'w') as f:
            f.write(file)
        # store crash message
        if self.error_path != '':
            self.browser.ready()
            self.browser.fuzz(self.output_path)
            with open(self.error_path, 'w') as f:
                f.write(self.browser.message())
        self.log('finish!')
        return True

    
def main():
    logging.basicConfig(level=logging.INFO)
    options = get_minimizer_option()
    browser = get_browser(0, options["browser"], options["timeout"])
    htmlMinimizer = HTMLMinimizer(options['input_path'], options['output_path'], '', browser)
    htmlMinimizer.minimization()


if __name__ == '__main__':
    main()
