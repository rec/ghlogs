import os
import pathlib
import requests

API_ROOT ='https://api.github.com/repos/pytorch/pytorch'
FAILURE = 'failure'

HEADERS = {
    'Accept': 'application/vnd.github+json',
    'Authorization': 'Bearer ' + os.getenv('GIT_TOKEN', ''),
    'X-GitHub-Api-Version': '2022-11-28',
}


def api_get(path, **ka):
    query = '&'.join(f'{k}={v}' for k, v in ka.items())
    query = bool(query) * '?' + query
    url = f'{API_ROOT}/{path}{query}'
    return requests.get(url, headers=HEADERS)


def get_jobs(run_id):
    return api_get(f'actions/runs/{run_id}/jobs', per_page=100).json()['jobs']


def get_job_log(job_id):
    return api_get(f'actions/jobs/{job_id}/logs').text


def failed(it):
    return [i for i in it if i['conclusion'] == FAILURE]


def get_failures(run_id):
    jobs = get_jobs(run_id)
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


def get_execute(lines):
    index = next(i for i in range(index, len(lines)) if EXECUTE in lines[i])
    return lines[index + 1]


def filter_job_log(lines):
    result = []
    for name, start, stop in PATTERNS:
        between = list(lines_between(lines, start, stop))
        if between:
            result = (f'Pattern: {name}\n\n', *between)
            break

    return ''.join(result)


START = 20 * '!'
STOP = 'The above exception was the direct cause of the following exception'
EXECUTE = 'To execute this test, run the following from the base repo dir'

PATTERNS = [
    ['basic', START, STOP],
]


def write_logs(run_id, log_dir='log'):
    log_dir = pathlib.Path(log_dir) / run_id
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / 'commands.sh').open('w') as command_fp:
        for job, steps in get_failures(run_id):
            job_id = job['id']

            def write(name, s):
                fname = log_dir / name / f'{job_id}.txt'
                fname.parent.mkdir(parents=True, exist_ok=True)
                fname.write_text(s)
                print('written', fname)

            log = get_job_log(job_id)
            write('full', log)
            lines = log.splitlines(keepends=True)
            execute = get_execute(lines)
            result = filter_job_log(lines)

            write('summary', result)
            cmd = f'{execute}  # {job_id}\n'


if __name__ == '__main__':
    import sys

    write_logs(*sys.argv[1:])
