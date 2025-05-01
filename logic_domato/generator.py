#   Domato - main generator script
#   --------------------------------------
#
#   Written and maintained by Ivan Fratric <ifratric@google.com>
#
#   Copyright 2017 Google Inc. All Rights Reserved.
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


from __future__ import print_function
import os
import re
import random
import argparse
import sys

from grammar import Grammar
from svg_tags import _SVG_TYPES
from html_tags import _HTML_TYPES

_N_MAIN_LINES = 0
_N_EVENTHANDLER_LINES = 0

_N_ADDITIONAL_HTMLVARS = 0


def generate_html_elements(ctx, n):
    for i in range(n):
        tag = random.choice(list(_HTML_TYPES))
        tagtype = _HTML_TYPES[tag]
        ctx['htmlvarctr'] += 1
        varname = 'htmlvar%05d' % ctx['htmlvarctr']
        ctx['htmlvars'].append({'name': varname, 'type': tagtype})
        ctx[
            'htmlvargen'] += '/* newvar{' + varname + ':' + tagtype + '} */ var ' + varname + ' = document.createElement(\"' + tag + '\"); //' + tagtype + '\n'


def add_html_ids(matchobj, ctx):
    tagname = matchobj.group(0)[1:-1]
    if tagname in _HTML_TYPES:
        ctx['htmlvarctr'] += 1
        varname = 'htmlvar%05d' % ctx['htmlvarctr']
        ctx['htmlvars'].append({'name': varname, 'type': _HTML_TYPES[tagname]})
        ctx['htmlvargen'] += '/* newvar{' + varname + ':' + _HTML_TYPES[
            tagname] + '} */ var ' + varname + ' = document.getElementById(\"' + varname + '\"); //' + \
                             _HTML_TYPES[tagname] + '\n'
        return matchobj.group(0) + 'id=\"' + varname + '\" '
    elif tagname in _SVG_TYPES:
        ctx['svgvarctr'] += 1
        varname = 'svgvar%05d' % ctx['svgvarctr']
        ctx['htmlvars'].append({'name': varname, 'type': _SVG_TYPES[tagname]})
        ctx['htmlvargen'] += '/* newvar{' + varname + ':' + _SVG_TYPES[
            tagname] + '} */ var ' + varname + ' = document.getElementById(\"' + varname + '\"); //' + \
                             _SVG_TYPES[tagname] + '\n'
        return matchobj.group(0) + 'id=\"' + varname + '\" '
    else:
        return matchobj.group(0)


def generate_function_body(jsgrammar, htmlctx, num_lines):
    js = ''
    # js += 'var fuzzervars = {};\n\n'
    # js += "SetVariable(fuzzervars, window, 'Window');\nSetVariable(fuzzervars, document, 'Document');\nSetVariable(fuzzervars, document.body.firstChild, 'Element');\n\n"
    # js += '//beginjs\n'
    # js += htmlctx['htmlvargen']
    # js += jsgrammar._generate_code(num_lines, htmlctx['htmlvars'])
    # js += '\n//endjs\n'
    # js += 'var fuzzervars = {};\nfreememory()\n'
    return js


def check_grammar(grammar):
    """Checks if grammar has errors and if so outputs them.
    Args:
      grammar: The grammar to check.
    """

    for rule in grammar._all_rules:
        for part in rule['parts']:
            if part['type'] == 'text':
                continue
            tagname = part['tagname']
            # print tagname
            if tagname not in grammar._creators:
                print('No creators for type ' + tagname)


def generate_new_sample(template, htmlgrammar, cssgrammar, jsgrammar):
    """Parses grammar rules from string.
    Args:
      template: A template string.
      htmlgrammar: Grammar for generating HTML code.
      cssgrammar: Grammar for generating CSS code.
      jsgrammar: Grammar for generating JS code.
    Returns:
      A string containing sample data.
    """

    result = template

    css = cssgrammar.generate_symbol('rules')
    html = htmlgrammar.generate_symbol('bodyelements')

    htmlctx = {
        'htmlvars': [],
        'htmlvarctr': 0,
        'svgvarctr': 0,
        'htmlvargen': ''
    }
    html = re.sub(
        r'<[a-zA-Z0-9_-]+ ',
        lambda match: add_html_ids(match, htmlctx),
        html
    )
    generate_html_elements(htmlctx, _N_ADDITIONAL_HTMLVARS)

    result = result.replace('<cssfuzzer>', css)
    result = result.replace('<htmlfuzzer>', html)

    handlers = False
    while '<jsfuzzer>' in result:
        numlines = _N_MAIN_LINES
        if handlers:
            numlines = _N_EVENTHANDLER_LINES
        else:
            handlers = True
        result = result.replace(
            '<jsfuzzer>',
            generate_function_body(jsgrammar, htmlctx, numlines),
            1
        )

    return result


def generate_samples(template, outfiles):
    """Generates a set of samples and writes them to the output files.
    Args:
      grammar_dir: directory to load grammar files from.
      outfiles: A list of output filenames.
    """

    grammar_dir = os.path.join(os.path.dirname(__file__), 'rules')
    htmlgrammar = Grammar()

    err = htmlgrammar.parse_from_file(os.path.join(grammar_dir, 'html.txt'))
    # CheckGrammar(htmlgrammar)
    if err > 0:
        print('There were errors parsing html grammar')
        return

    cssgrammar = Grammar()
    err = cssgrammar.parse_from_file(os.path.join(grammar_dir, 'css.txt'))
    # CheckGrammar(cssgrammar)
    if err > 0:
        print('There were errors parsing css grammar')
        return

    jsgrammar = Grammar()
    err = jsgrammar.parse_from_file(os.path.join(grammar_dir, 'js.txt'))
    # CheckGrammar(jsgrammar)
    if err > 0:
        print('There were errors parsing js grammar')
        return

    # JS and HTML grammar need access to CSS grammar.
    # Add it as import
    htmlgrammar.add_import('cssgrammar', cssgrammar)
    jsgrammar.add_import('cssgrammar', cssgrammar)

    for outfile in outfiles:
        result = generate_new_sample(template, htmlgrammar, cssgrammar, jsgrammar)
        if result is not None:
            print('Writing a sample to ' + outfile)
            try:
                with open(outfile, 'w') as f:
                    f.write(result)
            except IOError:
                print('Error writing to output')


def get_argument_parser():
    parser = argparse.ArgumentParser(description="DOMATO (A DOM FUZZER)")

    parser.add_argument("-f", "--file",
                        help="File name which is to be generated in the same directory")

    parser.add_argument('-o', '--output_dir', type=str,
                        help='The output directory to put the generated files in')

    parser.add_argument('-n', '--no_of_files', type=int,
                        help='number of files to be generated')

    return parser


class Generator:
    def __init__(self):
        self.grammar_dir = os.path.join(os.path.dirname(__file__), 'rules')
        f = open(os.path.join(os.path.dirname(__file__), 'template.html'))
        self.template = f.read()
        f.close()

        self.htmlgrammar = Grammar()
        err = self.htmlgrammar.parse_from_file(os.path.join(self.grammar_dir, 'html.txt'))
        # CheckGrammar(htmlgrammar)
        if err > 0:
            print('There were errors parsing grammar')
            return

        self.cssgrammar = Grammar()
        err = self.cssgrammar.parse_from_file(os.path.join(self.grammar_dir, 'css.txt'))
        # CheckGrammar(cssgrammar)
        if err > 0:
            print('There were errors parsing grammar')
            return
        use_mem_dep = False
        if os.getenv("MEM_DEP_JSON_PATH") is not None:
            print("use memory dependency analysis")
            use_mem_dep = True
        self.jsgrammar = Grammar()
        err = self.jsgrammar.parse_from_file(os.path.join(self.grammar_dir, 'js.txt'))
        if err > 0:
            print('There were errors parsing grammar')
            return

        # JS and HTML grammar need access to CSS grammar.
        # Add it as import
        self.htmlgrammar.add_import('cssgrammar', self.cssgrammar)
        self.jsgrammar.add_import('cssgrammar', self.cssgrammar)
        # lines = []
        # for rule in self.jsgrammar._creators['line']:
        #     lines.append(rule['original_line']+'\n')
        # with open('parsed_line', 'w') as f:
        #     f.writelines(lines)
        # return

    def generate_one(self) -> str:
        result = generate_new_sample(self.template, self.htmlgrammar, self.cssgrammar,
                                     self.jsgrammar)
        return result

    def _get_tag_name(self, string):
        return self.jsgrammar._parse_tag_and_attributes(string)["tagname"]

    def generate_sample_of_two_apis(self, original_line_1, original_line_2):
        pass


# def main():
#     fuzzer_dir = os.path.dirname(__file__)
#
#     multiple_samples = False
#
#     for a in sys.argv:
#         if a.startswith('--output_dir='):
#             multiple_samples = True
#
#     if '--output_dir' in sys.argv:
#         multiple_samples = True
#
#     if multiple_samples:
#         print('Running on ClusterFuzz')
#         out_dir = get_option('--output_dir')
#         nsamples = int(get_option('--no_of_files'))
#         print('Output directory: ' + out_dir)
#         print('Number of samples: ' + str(nsamples))
#
#         if not os.path.exists(out_dir):
#             os.mkdir(out_dir)
#
#         outfiles = []
#         for i in range(nsamples):
#             outfiles.append(os.path.join(out_dir, 'fuzz-' + str(i).zfill(5) + '.html'))
#
#         generate_samples(fuzzer_dir, outfiles)
#
#     elif len(sys.argv) > 1:
#         outfile = sys.argv[1]
#         generate_samples(fuzzer_dir, [outfile])
#
#     else:
#         print('Arguments missing')
#         print("Usage:")
#         print("\tpython generator.py <output file>")
#         print(
#             "\tpython generator.py --output_dir <output directory> --no_of_files <number of output files>")

def main():
    generator = Generator()
    target_file = ""
    while True:
        msg = sys.stdin.readline().strip()
        if msg == "generate":
            seed = generator.generate_one()
            try:
                f = open(target_file, 'w')
                f.write(seed)
                f.close()
                if os.getenv("ENABLE_RULE_MAP") is not None:
                    f = open(target_file + ".seq", 'w')
                    f.write(generator.jsgrammar.get_seq())
                    generator.jsgrammar.clear_seq()
                    f.close()
            except IOError as e:
                print(f'Error writing to output: {e}')
            print("done")
            sys.stdout.flush()
        elif msg == "exit":
            return
        elif msg.startswith("init"):
            target_file = msg.split(" ")[1]
            print(target_file)
            print("received")
            sys.stdout.flush()


if __name__ == '__main__':
    main()
