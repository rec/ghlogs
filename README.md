# ghlogs: Extract failing test commands from PyTorch CI runs

### What it does

PyTorch's continuous integration tests (CI)  generate a large number of big logs.
The program  `failed_test_commands.py` in this project extracts just the tests
that failed  so they can be run locally.

### How to use it

1. If not running in a PyTorch environment, install the requirements with
  `python -m pip install -r requirements.txt`

2. Get the URL of your pull request: just the pull ID number will do.

3. Run `python failed_test_commands.py PULL_URL [SECONDS_TO_WAIT]`

`SECONDS_TO_WAIT` defaults to 0.


### Note

The following bash function has proven useful.

```
errors() {
    error_file=~/git/pytorch/commands.sh \
        && echo -e "#/bin/bash\n\nset -x\n" > $error_file \
        && python ~/code/ghlogs/failed_test_commands.py $@ >> $error_file \
        && chmod +x $error_file
}
```
