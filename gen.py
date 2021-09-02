import jinja2
from argparse import ArgumentParser
import os
import shutil

import deploy
from generate_graph_page import generate_graph_html
from generate_index_page import generate_index_html
from project_results import ProjectResults

JINJA2_TEMPLATES_DIR = 'html'
GRAPHVIZ_TEMPLATE_PATH = os.path.join(JINJA2_TEMPLATES_DIR, 'graphviz.html')
INDEX_TEMPLATE_PATH = os.path.join(JINJA2_TEMPLATES_DIR, 'index.html')

CHARTJS_ZOOM_PATH = 'js/chartjs-plugin-zoom.min.js'

def load_template(path: str):
    with open(path, 'r') as t:
        return jinja2.Template(t.read(), trim_blocks=True, lstrip_blocks=True)

parser = ArgumentParser()

parser.add_argument('data_dir', type=str,
                    help='Directory containing json data files')
parser.add_argument('-o', '--out_dir', nargs=1, type=str,
                    help='Save outputs in a given directory')
parser.add_argument('-d', '--deploy', nargs=1, type=str,
                    help='Deploy the website to Github Pages using the '
                         'configuration at given path')
parser.add_argument('-a', '--amend', action='store_true',
                    help='Replace the last commit on github when using `--deploy` '
                         'instead of pushing a new one on top of the branch.')

args = parser.parse_args()

if not os.path.isdir(args.data_dir):
    print('Path needs to be a path to a directory')
    exit(-1)

graph_pages = {}

graph_viz_template = load_template(GRAPHVIZ_TEMPLATE_PATH)
index_template = load_template(INDEX_TEMPLATE_PATH)

results = []

for project_name in os.listdir(args.data_dir):
    project_dir = os.path.join(args.data_dir, project_name)
    if not os.path.isdir(project_dir):
        print(f'Skipping `{project_dir}` because it''s not a directory.')
        continue

    project_results = ProjectResults(project_name, project_dir)
    results.append(project_results)

    graph_pages[project_name] = \
        generate_graph_html(graph_viz_template, project_results)

index_page = generate_index_html(index_template, results)

chartjs_zoom_script: str
with open(CHARTJS_ZOOM_PATH, 'r') as f:
    chartjs_zoom_script = f.read()

if args.out_dir:
    graphs_dir = os.path.join(args.out_dir[0], 'graphs')
    os.makedirs(graphs_dir, exist_ok=True)
    for project_name, html in graph_pages.items():
        page_path = os.path.join(graphs_dir, f'{project_name}.html')
        try:
            with open(page_path, 'w') as out_file:
                out_file.write(html)
        except Exception as e:
            print(f'Unable to write to the output file {page_path}: {e}')
            exit(-1)
    
    index_path = os.path.join(args.out_dir[0], 'index.html')
    with open(index_path, 'w') as out_file:
        out_file.write(index_page)
    
    js_dir = os.path.join(args.out_dir[0], 'js')
    os.makedirs(js_dir, exist_ok=True)
    shutil.copy(CHARTJS_ZOOM_PATH,
                os.path.join(args.out_dir[0], CHARTJS_ZOOM_PATH))

if args.deploy:
    print('Deploying website to Github Pages...')
    
    pages = {}
    for project_name, html in graph_pages.items():
        pages[f'graphs/{project_name}.html'] = html
    pages['index.html'] = index_page
    pages[CHARTJS_ZOOM_PATH] = chartjs_zoom_script
    
    deploy.github_deploy_pages(args.deploy[0], pages,
                               'auto-deploy', amend=args.amend)
