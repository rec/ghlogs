# ghlogs: Extract failing test commands from PyTorch CI runs

### What it does

PyTorch's continuous integration tests (CI)  generate a large number of big logs.
The program  `failed_test_commands.py` in this project extracts just the tests
that failed  so they can be run locally.

### How to use it

1. If not running in a PyTorch environment, install the requirements with
  `python -m pip install -r requirements.txt`

2. Find the GitHub run IDs for your CI (see below for details).

3. Run `python failed_test_commands.py <RUN_ID1> <RUN_ID2>`

### Example of use

```
$ python failed_test_commands.py 9349550765 9349550798
python test/functorch/test_ops.py -k TestOperatorsCPU.test_vmapjvpvjp_as_strided_copy_cpu_float32  # 25550837738
```

Note that the line is suffixed with the GitHub job ID as a comment, to help debugging.

### How to get the run IDs for your pull request

1. Open the PyTorch HUD web page for your pull request

2. As of this writing, the CI workflow spawns two separate runs, labeled "pull" and
   "inductor", which have separate sections near the bottom of the page.

3. For each section, look at the top link.

4. The first number in that URL is the run ID for that section.

For example, for the pull request 127232, the HUD page is
https://hud.pytorch.org/pr/127232  and the top link for the "pull" section is
https://github.com/pytorch/pytorch/actions/runs/9382374924/job/25834350556
so the run ID is 9382374924.

### Future improvements

Getting the run IDs is currently a manual process, which is an obvious defect.

It would be better if this were done automatically, but I have not figured out a
way to go from the pull request number to the run IDs: the HUD pages are
dynamically generated so you can't just use `requests.get()` to get the text of
that page and then parse it.

Since the CI knows these run IDs, it would be easier and more convenient
if this step were incorporated into the construction of the HUD page.

### Notes

1. To get partial errors for a job in process, edit the script and set the variable
  `WAIT_FOR_CONCLUSION = 0`.

2. The following bash function has proven useful.

```
errors() {
    error_file=~/git/pytorch/commands.sh \
        && echo -e "#/bin/bash\n\nset -x\n" > $error_file \
        && python ~/code/ghlogs/failed_test_commands.py $@ >> $error_file \
        && chmod +x $error_file
}
```
