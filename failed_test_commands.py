import os
import re
import time

import bs4
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
SECONDS_TO_WAIT = 0
HREF_PREFIX = "/pytorch/pytorch/actions/runs/"


def get_run_ids(pull_id):
    try:
        pull_id = next(i for i in pull_id.split("/") if i.isnumeric())
    except Exception:
        sys.exit(f"Cannot get run id from {pull_id}")
    text = requests.get(f"https://github.com/pytorch/pytorch/pull/{pull_id}/checks").text
    soup = bs4.BeautifulSoup(text, "html.parser")
    links = (i for i in soup.find_all("a", href=True) if i.text)
    for a in links:
        prefix, _, href = a["href"].partition(HREF_PREFIX)
        if not prefix and href.isnumeric():
            for span in a.find_all("span"):
                if span.text.strip() in ('inductor', 'pull'):
                    yield href
                    break


def failed_test_commands(run_ids, seconds):
    for run_id in run_ids:
        for job in get_failures(run_id, seconds):
            command = get_command(job["id"])
            if command:
                print(f"{command}  # {job['id']}")


def get_failures(run_id, seconds):
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

        if not (seconds and not_finished):
            break
        print("Waiting for", seconds, "seconds", file=sys.stderr)
        time.sleep(seconds)

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

    try:
        _, pull_id, *seconds = sys.argv
        seconds, = seconds or [SECONDS_TO_WAIT]
        seconds = int(seconds)
    except Exception:
        sys.exit("Usage: ghlogs.py PULL_ID [SECONDS_TO_WAIT]")

    run_ids = get_run_ids(sys.argv[1])
    failed_test_commands(run_ids, seconds)
