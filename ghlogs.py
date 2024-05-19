import os
import pathlib
import requests

API_ROOT ='https://api.github.com/repos/pytorch/pytorch'
HEADERS = {
    'Accept': 'application/vnd.github+json',
    'Authorization': 'Bearer ' + os.getenv('GIT_TOKEN', ''),
    'X-GitHub-Api-Version': '2022-11-28',
}

FAILURE = 'failure'
CONCLUSION = 'conclusion'

START = 20 * '!'
SPLIT = 80 * '-'
ABOVE_EXCEPTION = 'The above exception was the direct cause of the following exception'
COMMAND = 'To execute this test, run the following from the base repo dir'

PATTERNS = [
    ['basic', START, ABOVE_EXCEPTION],
]

MIN_LINES = 250
MAX_LINES = 500


def api_get(path, **ka):
    query = '&'.join(f'{k}={v}' for k, v in ka.items())
    query = bool(query) * '?' + query
    url = f'{API_ROOT}/{path}{query}'
    return requests.get(url, headers=HEADERS)


def get_failures(run_id):
    print('Loading jobs...', end='', flush=True)
    jobs = api_get(f'actions/runs/{run_id}/jobs', per_page=100).json()['jobs']
    print(f'done, failures = {len(jobs)}')

    def failures(it):
        return [i for i in it if i[CONCLUSION] == FAILURE]

    for job in failures(jobs):
        job['failed_steps'] = failures(job['steps'])
        yield job


def lines_between(lines, start, stop, min_lines):
    for i, line in enumerate(lines):
        if start in line:
            stopped = False

            for j in range(i + 1, len(lines)):
                line = lines[j]
                stopped = stopped or stop in line
                if stopped and (i - j >= min_lines):
                    return
                else:
                    yield line


def filter_job_log(lines):
    result = []
    for name, start, stop in PATTERNS:
        between = list(lines_between(lines, start, stop, MIN_LINES))
        if between:
            result = between[:MAX_LINES]
            if len(PATTERNS) > 1:
                result = f'Pattern: {name}\n\n', *result
            break

    return ''.join(result)


def write_log(job, log_dir):
    job_id = job['id']
    print(job_id)

    def write(name, s):
        fname = log_dir / name / f'{job_id}.txt'
        fname.parent.mkdir(parents=True, exist_ok=True)
        fname.write_text(s)

    log = api_get(f'actions/jobs/{job_id}/logs').text
    lines = log.splitlines(keepends=True)

    write('full', log)
    summary = filter_job_log(lines)
    write('summary', summary)

    cmd_index = next(i for i, li in enumerate(lines) if COMMAND in li)
    _, cmd = lines[cmd_index + 1].split(maxsplit=1)
    return summary, f'{cmd.strip()}  # {job_id}\n'


def write_logs(run_id, log_dir='log'):
    log_dir = pathlib.Path(log_dir) / run_id
    log_dir.mkdir(parents=True, exist_ok=True)
    failures = get_failures(run_id)
    summaries_cmds = [write_log(job, log_dir) for job in failures]

    with (log_dir / f'{run_id}-summary.txt').open('w') as fp:
        for i, (summary, cmd) in enumerate(summaries_cmds):
            if i:
                fp.write('\n')

            fp.write(f'BEGIN {cmd}\n\n')
            fp.writelines(summary)
            fp.write(f'\nEND {cmd}\n{SPLIT}\n')

    cmd_file = log_dir / 'commands.sh'
    with cmd_file.open('w') as fp:
        fp.write('#!/bin/bash\n\nset -e\n\n')
        fp.writelines(cmd for _, cmd in summaries_cmds)

    cmd_file.chmod(cmd_file.stat().st_mode | 0o111)


if __name__ == '__main__':
    import sys

    write_logs(*sys.argv[1:])
