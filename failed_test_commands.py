import os
import pathlib
import re
import requests

API_ROOT ='https://api.github.com/repos/pytorch/pytorch'

GIT_TOKEN = os.getenv('GIT_TOKEN', '')
assert GIT_TOKEN, 'Please set env GIT_TOKEN to be a read access token'

HEADERS = {
    'Accept': 'application/vnd.github+json',
    'Authorization': f'Bearer {GIT_TOKEN}',
    'X-GitHub-Api-Version': '2022-11-28',
}

COMMAND_RE = re.compile(r'([A-Z_]+=.*)|python')

FAILURE = 'failure'
CONCLUSION = 'conclusion'
COMMAND = 'To execute this test, run the following from the base repo dir'


def failed_test_commands(run_id):
    for job in get_failures(run_id):
        command = get_command(job['id'])
        print(f'{command}  # {job["id"]}')


def get_failures(run_id):
    print('Loading jobs...', file=sys.stderr)
    json = api_get(f'actions/runs/{run_id}/jobs?per_page=100').json()
    try:
        jobs = json['jobs']
    except KeyError:
        print(json, file=sys.stderr)
        sys.exit(1)

    failed = [i for i in jobs if i[CONCLUSION] == FAILURE]
    print(f'run_id={run_id}, jobs={len(jobs)}, failed={len(failed)}', file=sys.stderr)
    return failed


def get_command(job_id):
    lines = api_get(f'actions/jobs/{job_id}/logs').text.splitlines()
    cmd_index = next(i for i, li in enumerate(lines) if COMMAND in li)

    words = lines[cmd_index + 1].split()
    while words and not COMMAND_RE.match(words[0]):
        words.pop(0)

    return ' '.join(words)


def api_get(path):
    return requests.get(f'{API_ROOT}/{path}', headers=HEADERS)


if __name__ == '__main__':
    import sys

    try:
        _, run_id = sys.argv
    except ValueError:
        print('Usage: ghlogs.py RUN_ID', file=sys.stderr)
        sys.exit(0)

    failed_test_commands(run_id)
