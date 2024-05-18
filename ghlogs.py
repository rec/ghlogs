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
STOP = 'The above exception was the direct cause of the following exception'
COMMAND = 'To execute this test, run the following from the base repo dir'

PATTERNS = [
    ['basic', START, STOP],
]


def api_get(path, **ka):
    query = '&'.join(f'{k}={v}' for k, v in ka.items())
    query = bool(query) * '?' + query
    url = f'{API_ROOT}/{path}{query}'
    return requests.get(url, headers=HEADERS)


def get_failures(run_id):
    def failed(it):
        return [i for i in it if i[CONCLUSION] == FAILURE]

    print('Loading jobs...', end='', flush=True)
    jobs = api_get(f'actions/runs/{run_id}/jobs', per_page=100).json()['jobs']
    print(f'done, fai;ure count = {len(jobs)}')
    return [[j, failed(j['steps'])] for j in failed(jobs)]


def lines_between(lines, start, stop):
    for i, line in enumerate(lines):
        if start in line:
            for j in range(i + 1, len(lines)):
                line = lines[j]
                if stop in line:
                    return
                else:
                    yield line


def filter_job_log(lines):
    result = []
    for name, start, stop in PATTERNS:
        between = list(lines_between(lines, start, stop))
        if between:
            result = (f'Pattern: {name}\n\n', *between)
            break

    return ''.join(result)


def write_logs(run_id, log_dir='log'):
    log_dir = pathlib.Path(log_dir) / run_id
    log_dir.mkdir(parents=True, exist_ok=True)
    commands = []

    for job, steps in get_failures(run_id):
        job_id = job['id']
        print(job_id)

        def write(name, s):
            fname = log_dir / name / f'{job_id}.txt'
            fname.parent.mkdir(parents=True, exist_ok=True)
            fname.write_text(s)

        log = api_get(f'actions/jobs/{job_id}/logs').text
        lines = log.splitlines(keepends=True)

        write('full', log)
        write('summary', filter_job_log(lines))

        cmd_index = next(i for i, li in enumerate(lines) if COMMAND in li)
        cmd = lines[cmd_index + 1]
        commands.append('{cmd}  # {job_id}\n')

    (log_dir / 'commands.sh').write_text(''.join(commands))


if __name__ == '__main__':
    import sys

    write_logs(*sys.argv[1:])
