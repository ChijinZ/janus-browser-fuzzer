# Janus Artifacts

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


