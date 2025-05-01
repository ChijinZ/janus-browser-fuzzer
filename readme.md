# Janus

Janus is a fuzzer for detecting rendering bugs in web browsers. Its technical details can be found in the [Janus Paper (ICSE'25)](https://www.computer.org/csdl/proceedings-article/icse/2025/056900a153/215aWz8c6nm). Basically, it crafts two HTML files that t differ only by minor modification, and observes if the reaction of two browsers to the modification is consistent. The test oracle here is that either two browsers render the HTML files identically or the browsers render them differently. The reason is detailed in the paper.

# Usage

```shell
Usage: python main [-options] -o output_dir

Options:
  -h, --help            show this help message and exit
  --browser1=BROWSER1   choose a browser (default: webkitgtk)
  --browser2=BROWSER2   choose a browser (default: webkitgtk)
  -t TIMEOUT, --timeout=TIMEOUT
                        timeout of each test (ms) (default: 5000ms)
  -p PARALLEL, --parallel=PARALLEL
                        how many instances in parallel (default: 1)
  -o OUTPUT_DIR, --output_dir=OUTPUT_DIR
                        where the result should output
  -e TIME_TO_EXIT, --time_to_exit=TIME_TO_EXIT
                        time to exit the fuzzing (hour)
  -x EXECUTION_ITERATION, --execution_iteration=EXECUTION_ITERATION
                        exit after this iteratio
```

example: ``python3 main.py --browser1=chromium --browser2=firefox -p 4 -o output``

# Key Component

The main workflow presents in the ``synthesis.py``.

# Publication

Related paper was published in ICSE'25. ``.bib`` info:

```bibtex
@inproceedings{zhou2024janus,
  title={Janus: Detecting Rendering Bugs in Web Browsers via Visual Delta Consistency},
  author={Zhou, Chijin and Zhang, Quan and Qian, Bingzhou and Jiang, Yu},
  booktitle={2025 IEEE/ACM 47th International Conference on Software Engineering (ICSE)},
  pages={153--164},
  year={2024},
  organization={IEEE Computer Society}
}
```
