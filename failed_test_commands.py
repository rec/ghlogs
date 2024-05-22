import os
import pathlib
import re
import requests

API_ROOT ='https://api.github.com/repos/pytorch/pytorch'
HEADERS = {
    'Accept': 'application/vnd.github+json',
    'Authorization': 'Bearer ' + os.getenv('GIT_TOKEN', ''),
    'X-GitHub-Api-Version': '2022-11-28',
}

match_command = re.compile(r'([A-Z_]+=.*)|python').match

FAILURE = 'failure'
CONCLUSION = 'conclusion'
COMMAND = 'To execute this test, run the following from the base repo dir'


def api_get(path, **ka):
    query = '&'.join(f'{k}={v}' for k, v in ka.items())
    if query:
    query = bool(query) * '?' + query
    url = f'{API_ROOT}/{path}{query}'
    return requests.get(url, headers=HEADERS)


def get_failures(run_id):
    print('Loading jobs...', end='', flush=True, file=sys.stderr)
    jobs = api_get(f'actions/runs/{run_id}/jobs', per_page=100).json()['jobs']

    def failures(it):
        return [i for i in it if i[CONCLUSION] == FAILURE]

    failed = failures(jobs)
    for job in failed:
        job['failed_steps'] = failures(job['steps'])

    print(f'done, jobs = {len(jobs)}, failed = {len(failed)}', file=sys.stderr)
    return failed


def get_command(job_id):
    lines = api_get(f'actions/jobs/{job_id}/logs').text.splitlines()
    cmd_index = next(i for i, li in enumerate(lines) if COMMAND in li)

    words = lines[cmd_index + 1].split()
    while words and not match_command(words[0]):
        words.pop(0)

    return ' '.join(words)


def write_commands(run_id):
    for job in get_failures(run_id):
        command = get_command(job['id'])
        print(f'{command}  # {job["id"]}')


if __name__ == '__main__':
    import sys

    try:
        _, run_id = sys.argv
    except ValueError:
        print('Usage: ghlogs.py RUN_ID', file=sys.stderr)
        sys.exit(0)

    write_commands(run_id)
