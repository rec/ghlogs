import os
import re
import time

import requests

API_ROOT = "https://api.github.com/repos/pytorch/pytorch"

GIT_TOKEN = os.getenv("GIT_TOKEN", "")
assert GIT_TOKEN, "Please set env GIT_TOKEN to be a read access token"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {GIT_TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28",
}

COMMAND_RE = re.compile(r"([A-Z_]+=.*)|python")

FAILURE = "failure"
CONCLUSION = "conclusion"
COMMAND = "To execute this test, run the following from the base repo dir"
WAIT_FOR_CONCLUSION = 60
PRINT_SCRIPT_HEADER = False


def failed_test_commands(*run_ids):
    if PRINT_SCRIPT_HEADER:
        print("#/bin/bash\n\nset -x\n")

    for run_id in run_ids:
        for job in get_failures(run_id):
            command = get_command(job["id"])
            if command:
                print(f"{command}  # {job['id']}")


def get_failures(run_id):
    while True:
        print(f"Loading jobs for {run_id}...", file=sys.stderr)
        json = api_get(f"actions/runs/{run_id}/jobs?per_page=100").json()
        try:
            jobs = json["jobs"]
        except KeyError:
            print(json, file=sys.stderr)
            sys.exit(1)

        not_finished = sum(not j["conclusion"] for j in jobs)
        if not_finished:
            msg = f"{not_finished} job{'s' * (not_finished != 1)} not finished"
            print(msg, file=sys.stderr)

        if not (WAIT_FOR_CONCLUSION and not_finished):
            break
        print("Waiting for", WAIT_FOR_CONCLUSION, "seconds", file=sys.stderr)
        time.sleep(WAIT_FOR_CONCLUSION)

    failed = [i for i in jobs if i[CONCLUSION] == FAILURE]
    print(f"run_id={run_id}, jobs={len(jobs)}, failed={len(failed)}", file=sys.stderr)
    return failed


def get_command(job_id):
    lines = api_get(f"actions/jobs/{job_id}/logs").text.splitlines()
    command_lines = (i for i, li in enumerate(lines) if COMMAND in li)
    cmd_index = next(command_lines, -1)
    if cmd_index == -1:
        return ""

    words = lines[cmd_index + 1].split()
    while words and not COMMAND_RE.match(words[0]):
        words.pop(0)

    return " ".join(words)


def api_get(path):
    return requests.get(f"{API_ROOT}/{path}", headers=HEADERS)


if __name__ == "__main__":
    import sys

    _, *run_ids = sys.argv
    if not run_ids:
        print("Usage: ghlogs.py RUN_ID [RUN_ID]", file=sys.stderr)
        sys.exit(0)

    failed_test_commands(*run_ids)
