import json
from github import Github, InputGitTreeElement

def github_connect(config: dict):
    github_cfg = config.get('github')
    if not github_cfg:
        print('ERROR: Can\'t find github configuration section')
        exit(-1)
    
    access_token = github_cfg.get('access_token')
    if access_token:
        return Github(access_token)
    
    print('WARNING: Github access token is not defined. Next authentication '
          'method: Username+Password. It\'s highly recommended to use tokens '
          'instead.')

    username = github_cfg.get('username')
    pwd = github_cfg.get('password')

    if (not username) or (not pwd):
        print('ERROR: Github username or passwrod missing from configuration.')
        exit(-1)
    
    return Github(username, pwd)

def github_repo_branch(config: dict):
    github_cfg = config.get('github')
    if not github_cfg:
        print('ERROR: Can\'t find github configuration section')
        exit(-1)
    
    repo_name = config['github'].get('repo')
    if not repo_name:
        print('ERROR: Missing repo name in configuration')
        exit(-1)
    branch_name = config['github'].get('branch')
    if not branch_name:
        print('ERROR: Missing branch name in configuration')
        exit(-1)
    
    return repo_name, branch_name

def github_deploy_pages(deploy_config_path: str, pages: 'dict[str, str]',
                        commit_msg: str, amend=False):
    deploy_config: str
    with open(deploy_config_path, 'r') as cfg_file:
        deploy_config = json.loads(cfg_file.read())
    
    repo_name, branch_name = github_repo_branch(deploy_config)
    g = github_connect(deploy_config)
    repo = g.get_user().get_repo(repo_name)
    branch_ref = repo.get_git_ref(f'heads/{branch_name}')
    branch_sha = branch_ref.object.sha
    base_tree = repo.get_git_tree(branch_sha)

    element_list = []
    for page_path, page_content in pages.items():
        elem = InputGitTreeElement(path=page_path, mode='100644', type='blob',
                                   content=page_content)
        element_list.append(elem)
    
    tree = repo.create_git_tree(element_list, base_tree)
    branch_tip = repo.get_git_commit(branch_sha)
    parents = [branch_tip] if not amend else branch_tip.parents

    commit = repo.create_git_commit(commit_msg, tree, parents)
    branch_ref.edit(commit.sha, force=amend)
