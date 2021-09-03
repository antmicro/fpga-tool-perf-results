# Fetch test results from Google Storage

import os
import json
import requests
import gzip
from argparse import ArgumentParser
from datetime import datetime
from collections import defaultdict

parser = ArgumentParser()
parser.add_argument('builds', type=str)
parser.add_argument('from_tr', type=int)
parser.add_argument('to_tr', type=str)
parser.add_argument('output_dir', type=str)

args = parser.parse_args()

STORAGE_API_AT='https://www.googleapis.com/storage/v1/b/fpga-tool-perf/o'
TESTRES_PREFIX='artifacts/prod/foss-fpga-tools/fpga-tool-perf/' + args.builds
OLD_TESTRES_DELIMITER='meta.json'
NEW_TESTRES_DELIMITER='results-generic-all.json.gz'
DOWNLOAD_BASE_URL='https://storage.googleapis.com/fpga-tool-perf'

# Iterage over all result pages in GCS JSON API.
def resp_pages(url: str):
    next_page_token = None
    while True:
        req_url = \
            url + f'&pageToken={next_page_token}' if next_page_token else url
        resp = requests.get(url=req_url,
                            headers={'Content-Type': 'application/json'})
        data = resp.json()

        yield data

        next_page_token = data.get('nextPageToken')
        if not next_page_token:
            break

def get_compound_result_file_path(test_run: int):
    url = f'{STORAGE_API_AT}?delimiter={NEW_TESTRES_DELIMITER}' \
          f'&prefix={TESTRES_PREFIX}/{test_run}/'

    for data in resp_pages(url):
        prefixes = data.get('prefixes')
        if prefixes:
            return prefixes[0]

def get_result_file_paths(test_run: int):
    url = f'{STORAGE_API_AT}?delimiter={OLD_TESTRES_DELIMITER}' \
          f'&prefix={TESTRES_PREFIX}/{test_run}/'

    for data in resp_pages(url):
        for prefix in data['prefixes']:
            yield prefix

def download_meta(path: str, binary: bool = False):
    print(f'Downloading `{path}`')

    req_url = f'{DOWNLOAD_BASE_URL}/{path}'
    resp = requests.get(url=req_url,
                        headers={"Content-Type": "application/json"})

    if not binary:
        return resp.text
    return resp.content

def are_results_compound(prefixes: 'list[str]'):
    return len(prefixes) == 1

def datetime_from_str(s: str):
    return datetime.strptime(s, '%Y-%m-%dT%H:%M:%S')

def merge_results(metas, filter=None):
    earliest_dt = datetime.now()
    projects = defaultdict(lambda: {
        'results': defaultdict(lambda: [])
    })

    for meta in metas:
        try:
            dt = datetime_from_str(meta['date'])
            if dt < earliest_dt:
                earliest_dt = dt

            results = projects[meta['project']]['results']

            if filter is not None:
                if not filter(meta):
                    continue

            # This is a rather incomplete list, but it should do the job
            results['board'].append(meta['board'])
            results['toolchain'].append(meta['toolchain'])
            results['runtime'].append(meta['runtime'])
            results['resources'].append(meta['resources'])
            results['maximum_memory_use'].append(meta['maximum_memory_use'])
            results['max_freq'].append(meta['max_freq'])
            results['device'].append(meta['device'])

        except KeyError as e:
            print(f'Skipping a meta file because of {e}')

    for project in projects.values():
        project['date'] = \
            f'{earliest_dt.year}-{earliest_dt.month}-{earliest_dt.day}T' \
            f'{earliest_dt.hour}:{earliest_dt.minute}:{earliest_dt.second}'

    return projects

def get_legacy_metas(gcs_paths: str):
    for path in gcs_paths:
        meta_json = download_meta(path)
        meta: dict
        try:
            meta = json.loads(meta_json)
        except json.decoder.JSONDecodeError:
            # Yes this has actually happened once for some reason
            print('ERROR: CAN\'T DECODE THE JSON FROM GCS')
            with open(f'faulty_json-{test_run_no}.json', 'w') as f:
                f.write(meta_json)
            continue
        yield meta
    print('Download complete!')

def download_and_merge_legacy(gcs_paths: str):
    def accept_generic_all_build_only(meta):
        return meta['build_type'] == 'generic-all' and meta['build'] == '000'

    metas = get_legacy_metas(gcs_paths)
    merged =  merge_results(metas, filter=accept_generic_all_build_only)
    print('Merge complete!')
    return merged

def download_and_split_compound(gcs_compound_path: str):
    meta_json_gz = download_meta(gcs_compound_path, binary=True)
    meta_json = gzip.decompress(meta_json_gz).decode()
    meta = json.loads(meta_json)

    projects = defaultdict(lambda: {
        'results': defaultdict(lambda: [])
    })

    meta_results = meta['results']
    zipped = zip(
        meta_results['board'],
        meta_results['project'],
        meta_results['toolchain'],
        meta_results['runtime'],
        meta_results['resources'],
        meta_results['maximum_memory_use'],
        meta_results['max_freq'],
        meta_results['device'],
        meta_results['wirelength']
    )

    for board, project, toolchain, runtime, resources, maximum_mem_use, \
            max_freq, device, wirelength in zipped:

        project_res = projects[project]['results']
        project_res['board'].append(board)
        project_res['toolchain'].append(toolchain)
        project_res['runtime'].append(runtime)
        project_res['resources'].append(resources)
        project_res['maximum_memory_use'].append(maximum_mem_use)
        project_res['max_freq'].append(max_freq)
        project_res['device'].append(device)
        project_res['wirelength'].append(wirelength)

    for project in projects.values():
        project['date'] = meta['date']

    return projects

def get_test_run_numbers(start: int, end: 'str'):
    url = f'{STORAGE_API_AT}?delimiter=/&prefix={TESTRES_PREFIX}/'

    for data in resp_pages(url):
        for prefix in data['prefixes']:
            no = int(prefix.split('/')[-2])
            if no >= start and (end == '_' or no <= int(end)):
                yield no


# -------------------------------------------------------------------- #

if not os.path.isdir(args.output_dir):
    print('ERROR: Output path is not a directory!')
    exit(-1)

for test_run_no in get_test_run_numbers(args.from_tr, args.to_tr):
    print(f'Downloading data for test run no. {test_run_no}')

    gcs_compound_path = None
    gcs_paths = None
    try:
        gcs_compound_path = get_compound_result_file_path(test_run_no)
        if not gcs_compound_path:
            gcs_paths = list(get_result_file_paths(test_run_no))
    except Exception as e:
        print(f'Failed to fetch patches for test run no. {test_run_no}, '
              f'cause: {e}')
        continue

    merged: defaultdict
    if gcs_compound_path:
        merged = download_and_split_compound(gcs_compound_path)
    else:
        merged = download_and_merge_legacy(gcs_paths)

    for project_name, merged_data in merged.items():
        project_dir = os.path.join(args.output_dir, project_name)
        out_filename = os.path.join(project_dir, f'meta-{test_run_no}.json')
        os.makedirs(project_dir, exist_ok=True)
        merged_json = json.dumps(merged_data, indent=4)
        with open(out_filename, 'w') as f:
            f.write(merged_json)

print('DONE')
