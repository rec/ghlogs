import os
import pathlib
import re
import requests
import time

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
COMPLETED = 'completed'

CONCLUSION = 'conclusion'
COMMAND = 'To execute this test, run the following from the base repo dir'
WAIT_FOR_CONCLUSION = 60
DEBUG = True

def failed_test_commands(run_id, wait_for_conclusion):
    print('#/bin/bash\n\nset -x\n')

    for job in get_failures(run_id, wait_for_conclusion):
        command = get_command(job['id'])
        file = sys.stderr if command.startswith('#') else sys.stdout
        print(f'{command}  # {job["id"]}', file=file)


def get_failures(run_id, wait_for_conclusion):
    while True:
        print('Loading jobs...', file=sys.stderr)
        json = api_get(f'actions/runs/{run_id}/jobs?per_page=100').json()
        jobs = json['jobs']

        not_finished = sum(not j['conclusion'] for j in jobs)
        if not_finished:
            print(f'{not_finished} job{"s" * (not_finished != 1)} not finished', file=sys.stderr)

        if not (wait_for_conclusion and not_finished):
            break
        print('Waiting for', wait_for_conclusion, 'seconds', file=sys.stderr)
        time.sleep(wait_for_conclusion)

    failed = [i for i in jobs if i[CONCLUSION] != COMPLETED]
    print(f'run_id={run_id}, jobs={len(jobs)}, failed or incomplete={len(failed)}', file=sys.stderr)
    return failed


def get_command(job_id):
    try:
        lines = api_get(f'actions/jobs/{job_id}/logs').text.splitlines()
    except requests.ConnectionError as e:
        return f'# couldn\'t get logs {e}'

    command_lines = (i for i, li in enumerate(lines) if COMMAND in li)
    cmd_index = next(command_lines, -1)
    if cmd_index == -1:
        if DEBUG:
            for i in lines:
                print(i)
            sys.exit()
        return '# No command found'

    words = lines[cmd_index + 1].split()
    while words and not COMMAND_RE.match(words[0]):
        words.pop(0)

    return ' '.join(words)


def api_get(path):
    return requests.get(f'{API_ROOT}/{path}', headers=HEADERS)


if __name__ == '__main__':
    import sys

    exe, *rest = sys.argv
    try:
        run_id, *rest = rest
        wait_for_conclusion, = rest or [WAIT_FOR_CONCLUSION]
        wait_for_conclusion = int(wait_for_conclusion)
    except ValueError:
        print(f'Usage: {exe} RUN_ID [WAIT_FOR_CONCLUSION]', file=sys.stderr)
        sys.exit(0)

    failed_test_commands(run_id, wait_for_conclusion)
