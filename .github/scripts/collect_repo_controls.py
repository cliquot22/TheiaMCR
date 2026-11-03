#!/usr/bin/env python3
"""
Repository and release-pipeline controls evidence for the CRA risk assessments (SW-09 / PY-09).

Collects the GitHub settings for one or more repositories, saves each API response as a file in an evidence
folder, and writes SUMMARY.md with a result for each check:
  1. Branch rules: the default branch blocks deletion and force pushes (rulesets or classic protection).
  2. Release run: the workflow runs for the release tag finished successfully on the tagged commit.
  3. Maintainer 2FA and collaborators: the authenticated account has 2FA on; who has access to the repository.
  4. Least-privilege tokens: the default workflow token is read-only and can't approve pull requests; every workflow
     sets a top-level `permissions:` block and grants write scopes only to the jobs that need them; secret names
     (never values), with a warning for any PyPI token left over from before trusted publishing.
  5. Pinned actions: every `uses:` in the workflows is pinned to a full 40-character commit SHA.
  6. Documented: the commit of each workflow file used for the release tag.

Usage:
    python .github/scripts/collect_repo_controls.py --repo cliquot22/TheiaMCR [--repo cliquot22/lensIQ ...]
           [--tag v3.5.2] [--out <folder>]

Authentication (checks 3 and 4 and the classic branch protection need it): a token in the GH_TOKEN or
GITHUB_TOKEN environment variable, or the GitHub CLI logged in (`gh auth login`).  A classic token needs the
`repo` and `read:user` scopes; a fine-grained token needs read access to Administration, Actions, Secrets,
Contents and Metadata.  Without a token the public checks still run and the others are marked NOT RUN.

The evidence folder holds repository settings: keep it in the CRA technical file, not in the public repository.
Only the Python standard library is needed.
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

API = 'https://api.github.com'
DOCUMENT_NUMBERS = {'TheiaMCR': '002', 'TheiaMCR_C': '003', 'lensIQ': '004'}      # CRA document number per product
SHA_PIN = re.compile(r'@[0-9a-f]{40}$')


def findToken():
    for name in ('GH_TOKEN', 'GITHUB_TOKEN'):
        if os.environ.get(name):
            return os.environ[name]
    try:
        run = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True, timeout=20)
        if run.returncode == 0 and run.stdout.strip():
            return run.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


class GitHub:
    def __init__(self, token):
        self.token = token

    def get(self, path):
        """Return (HTTP status, JSON data or error message)."""
        request = urllib.request.Request(API + path, headers={
            'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'TheiaMCR-repo-controls', **({'Authorization': f'Bearer {self.token}'} if self.token else {})})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as e:
            try:
                message = json.load(e).get('message', '')
            except Exception:
                message = ''
            return e.code, {'http_status': e.code, 'message': message}


class Evidence:
    """Saves API responses into the evidence folder and collects the summary rows."""
    def __init__(self, folder):
        self.folder = folder
        self.rows = []
        os.makedirs(folder, exist_ok=True)

    def save(self, name, data):
        path = os.path.join(self.folder, name)
        with open(path, 'w', encoding='utf-8') as f:
            if isinstance(data, str):
                f.write(data)
            else:
                json.dump(data, f, indent=2)
        return name

    def result(self, step, check, status, detail, files=()):
        self.rows.append((step, check, status, detail, ', '.join(f'`{f}`' for f in files)))


def notRun(status):
    return status in (401, 403)


def workflowFiles(gh, repo, ref):
    """Return {filename: text} for the files in .github/workflows at ref."""
    status, listing = gh.get(f'/repos/{repo}/contents/.github/workflows?ref={ref}')
    files = {}
    if status != 200:
        return files
    for item in listing:
        if item['name'].endswith(('.yml', '.yaml')):
            _, data = gh.get(f'/repos/{repo}/contents/{item["path"]}?ref={ref}')
            files[item['name']] = base64.b64decode(data['content']).decode('utf-8')
    return files


def permissionsReport(text):
    """Find the top-level permissions block and every write scope (with its job) in a workflow file."""
    lines = text.splitlines()
    topLevel = None
    writes = []
    job = None
    inJobs = False
    for number, line in enumerate(lines, 1):
        stripped = line.split('#', 1)[0].rstrip()
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip())
        if indent == 0:
            inJobs = stripped.startswith('jobs:')
            job = None
            if stripped.startswith('permissions:'):
                value = stripped.split(':', 1)[1].strip()
                block = [value] if value else []
                for following in lines[number:]:
                    following = following.split('#', 1)[0].rstrip()
                    if following.strip() and not following.startswith((' ', '\t')):
                        break
                    if following.strip():
                        block.append(following.strip())
                topLevel = ', '.join(block)
        elif inJobs and indent == 2 and stripped.endswith(':'):
            job = stripped.strip()[:-1]
        if re.search(r':\s*write\b|write-all', stripped):
            writes.append((number, job or 'workflow level', stripped.strip()))
    return topLevel, writes


def checkRepository(gh, repo, tag, outRoot):
    name = repo.split('/')[-1]
    folder = os.path.join(outRoot, f'CRA-GHS-{DOCUMENT_NUMBERS.get(name, "000")}_{name}_SW-09_RepoControls_{date.today()}')
    ev = Evidence(folder)

    status, info = gh.get(f'/repos/{repo}')
    if status != 200:
        sys.exit(f'{repo}: repository not found or not accessible ({status} {info.get("message")})')
    branch = info['default_branch']
    ev.save('00_repository.json', {k: info.get(k) for k in ('full_name', 'visibility', 'default_branch', 'html_url', 'pushed_at')})
    if tag is None:
        status, latest = gh.get(f'/repos/{repo}/releases/latest')
        tag = latest.get('tag_name') if status == 200 else None

    # 1. branch rules
    _, rules = gh.get(f'/repos/{repo}/rules/branches/{branch}')
    _, rulesets = gh.get(f'/repos/{repo}/rulesets?includes_parents=true')
    files = [ev.save('01_branch_rules_effective.json', rules), ev.save('01_rulesets.json', rulesets)]
    for ruleset in rulesets if isinstance(rulesets, list) else []:
        _, detail = gh.get(f'/repos/{repo}/rulesets/{ruleset["id"]}')
        files.append(ev.save(f'01_ruleset_{ruleset["id"]}.json', detail))
    protectionStatus, protection = gh.get(f'/repos/{repo}/branches/{branch}/protection')
    files.append(ev.save('01_branch_protection_classic.json', protection))
    ruleTypes = {r['type'] for r in rules} if isinstance(rules, list) else set()
    if protectionStatus == 200:
        if protection.get('allow_deletions', {}).get('enabled') is False:
            ruleTypes.add('deletion')
        if protection.get('allow_force_pushes', {}).get('enabled') is False:
            ruleTypes.add('non_fast_forward')
    blocked = {'deletion': 'deletion blocked', 'non_fast_forward': 'force push blocked'}
    missing = [text for rule, text in blocked.items() if rule not in ruleTypes]
    classic = {200: 'classic protection on', 404: 'no classic protection (rulesets are used)'}.get(
        protectionStatus, 'classic protection not read (needs a token)')
    ev.result('1', f'Branch `{branch}`: deletion and force pushes blocked', 'FAIL' if missing else 'PASS',
              (f'missing: {", ".join(missing)}' if missing else ', '.join(blocked.values())) +
              f'; rules: {", ".join(sorted(ruleTypes)) or "none"}; {classic}', files)
    ev.result('1', 'Required status checks / pull request review', 'N/A',
              'not used: single developer, direct pushes to the default branch (see R-08 / single-developer certification)')

    # 2. release workflow runs
    if tag:
        status, ref = gh.get(f'/repos/{repo}/git/ref/tags/{tag}')
        tagCommit = None
        if status == 200:
            tagCommit = ref['object']['sha']
            if ref['object']['type'] == 'tag':                     # annotated tag: follow it to the commit
                tagCommit = gh.get(f'/repos/{repo}/git/tags/{tagCommit}')[1]['object']['sha']
        _, runs = gh.get(f'/repos/{repo}/actions/runs?event=release&per_page=100')
        releaseRuns = [{k: run.get(k) for k in ('id', 'name', 'path', 'conclusion', 'status', 'head_sha', 'created_at', 'html_url')}
                       for run in runs.get('workflow_runs', []) if run.get('head_branch') == tag]
        files = [ev.save('02_release_runs.json', {'tag': tag, 'tag_commit': tagCommit, 'runs': releaseRuns})]
        failed = [r for r in releaseRuns if r['conclusion'] != 'success']
        wrongCommit = [r for r in releaseRuns if tagCommit and r['head_sha'] != tagCommit]
        status = 'FAIL' if failed or wrongCommit or not releaseRuns else 'PASS'
        detail = '; '.join(f'{r["name"]} run {r["id"]}: {r["conclusion"]}' for r in releaseRuns) or 'no release workflow runs found'
        if wrongCommit:
            detail += '; a run did not use the tagged commit'
        ev.result('2', f'Release `{tag}` workflow runs succeeded on commit `{(tagCommit or "?")[:12]}`', status, detail, files)
    else:
        ev.result('2', 'Release workflow runs', 'N/A', 'no release found')

    # 3. maintainer 2FA and collaborators
    status, user = gh.get('/user')
    if notRun(status) or not gh.token:
        ev.result('3', 'Maintainer 2FA (GitHub)', 'NOT RUN', 'needs a token')
    else:
        twoFactor = user.get('two_factor_authentication')
        files = [ev.save('03_github_2fa.json', {'login': user.get('login'), 'two_factor_authentication': twoFactor})]
        ev.result('3', f'Maintainer 2FA (GitHub account `{user.get("login")}`)',
                  'PASS' if twoFactor is True else 'FAIL' if twoFactor is False else 'REVIEW',
                  'two-factor authentication on' if twoFactor else 'two-factor authentication off' if twoFactor is False
                  else 'not returned: the token needs the read:user scope', files)
    status, collaborators = gh.get(f'/repos/{repo}/collaborators?per_page=100')
    if notRun(status):
        ev.result('3', 'Collaborators', 'NOT RUN', 'needs a token')
    else:
        people = [{'login': c['login'], 'role_name': c.get('role_name')} for c in collaborators]
        files = [ev.save('03_collaborators.json', people)]
        admins = [p['login'] for p in people if p['role_name'] == 'admin']
        ev.result('3', 'Collaborators', 'PASS' if len(people) == 1 and len(admins) == 1 else 'REVIEW',
                  '; '.join(f'{p["login"]} ({p["role_name"]})' for p in people), files)
    ev.result('3', 'Maintainer 2FA (PyPI)', 'MANUAL', 'screenshot of pypi.org Account settings → Two-factor authentication')

    # 4. least-privilege workflow tokens
    status, tokenDefaults = gh.get(f'/repos/{repo}/actions/permissions/workflow')
    if notRun(status):
        ev.result('4', 'Default workflow token', 'NOT RUN', 'needs a token')
    else:
        files = [ev.save('04_default_token.json', tokenDefaults)]
        readOnly = tokenDefaults.get('default_workflow_permissions') == 'read'
        noApprove = tokenDefaults.get('can_approve_pull_request_reviews') is False
        ev.result('4', 'Default workflow token is read-only and cannot approve pull requests',
                  'PASS' if readOnly and noApprove else 'FAIL',
                  f'default_workflow_permissions: {tokenDefaults.get("default_workflow_permissions")}; '
                  f'can_approve_pull_request_reviews: {tokenDefaults.get("can_approve_pull_request_reviews")}'
                  + ('' if readOnly and noApprove else ' (change under Settings → Actions → General → Workflow permissions)'),
                  files)

    workflows = workflowFiles(gh, repo, branch)
    report = []
    for filename, text in sorted(workflows.items()):
        topLevel, writes = permissionsReport(text)
        report.append({'file': filename, 'top_level_permissions': topLevel,
                       'write_scopes': [{'line': n, 'job': job, 'text': t} for n, job, t in writes]})
        topWrite = [w for w in writes if w[1] == 'workflow level']
        status = 'FAIL' if topLevel is None else 'REVIEW' if topWrite else 'PASS'
        detail = (f'top-level permissions: {topLevel or "missing"}; write scopes: ' +
                  ('; '.join(f'{job}: {t}' for _, job, t in writes) or 'none'))
        if topWrite:
            detail += ' (write scope at workflow level: move it to the job that needs it)'
        ev.result('4', f'Workflow `{filename}` permissions', status, detail)
    files4 = [ev.save('04_workflow_permissions.json', report)]
    if report:
        ev.rows[-1] = ev.rows[-1][:4] + (', '.join(f'`{f}`' for f in files4),)

    status, secrets = gh.get(f'/repos/{repo}/actions/secrets')
    if notRun(status):
        ev.result('4', 'Secrets (names only)', 'NOT RUN', 'needs a token')
    else:
        names = [s['name'] for s in secrets.get('secrets', [])]
        _, environments = gh.get(f'/repos/{repo}/environments')
        for environment in environments.get('environments', []):
            _, envSecrets = gh.get(f'/repos/{repo}/environments/{environment["name"]}/secrets')
            names += [f'{s["name"]} (environment {environment["name"]})' for s in envSecrets.get('secrets', [])]
        files = [ev.save('04_secrets.txt', '\n'.join(names) + ('\n' if names else ''))]
        pypiTokens = [n for n in names if re.search(r'pypi|twine', n, re.IGNORECASE)]
        ev.result('4', 'Secrets (names only)', 'REVIEW' if pypiTokens else 'PASS',
                  (', '.join(names) or 'none') + ('; PyPI token stored: delete it, trusted publishing needs none'
                                                  if pypiTokens else ''), files)

    # 5. pinned actions
    uses = []
    for filename, text in sorted(workflows.items()):
        for number, line in enumerate(text.splitlines(), 1):
            match = re.match(r'\s*(?:-\s*)?uses:\s*([^\s#]+)\s*(#.*)?$', line)
            if match:
                action = match.group(1).strip('\'"')
                pinned = action.startswith('./') or (action.startswith('docker://') and '@sha256:' in action) or bool(SHA_PIN.search(action))
                uses.append({'file': filename, 'line': number, 'uses': action, 'comment': (match.group(2) or '').lstrip('# '), 'pinned': pinned})
    files = [ev.save('05_actions_uses.json', uses)]
    unpinned = [u for u in uses if not u['pinned']]
    ev.result('5', 'Actions pinned to a full commit SHA', 'FAIL' if unpinned else 'PASS',
              ('not pinned: ' + '; '.join(f'{u["file"]} line {u["line"]} `{u["uses"]}`' for u in unpinned)) if unpinned
              else f'{len(uses)} action references, all pinned', files)
    status, policy = gh.get(f'/repos/{repo}/actions/permissions')
    if notRun(status):
        ev.result('5', 'Actions policy', 'NOT RUN', 'needs a token')
    else:
        files = [ev.save('05_actions_policy.json', policy)]
        detail = f'allowed_actions: {policy.get("allowed_actions")}'
        if 'sha_pinning_required' in policy:
            detail += f'; sha_pinning_required: {policy["sha_pinning_required"]}'
        ev.result('5', 'Actions policy', 'INFO', detail, files)

    # 6. documented: commit of each workflow file used for the release
    if tag:
        tagged = workflowFiles(gh, repo, tag)
        commits = []
        for filename in sorted(tagged):
            _, history = gh.get(f'/repos/{repo}/commits?path=.github/workflows/{filename}&sha={tag}&per_page=1')
            if history:
                commits.append({'file': filename, 'commit': history[0]['sha'], 'date': history[0]['commit']['committer']['date']})
        files = [ev.save('06_workflow_commits.json', {'tag': tag, 'workflows': commits})]
        ev.result('6', f'Workflow files used for `{tag}`', 'INFO',
                  '; '.join(f'{c["file"]} at `{c["commit"][:12]}`' for c in commits) or 'no workflow files at the tag', files)

    # summary
    lines = [f'# Repository controls evidence (SW-09): {repo}', '',
             f'- **Collected**: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}',
             f'- **Default branch**: `{branch}`', f'- **Release**: `{tag}`',
             f'- **Authenticated**: {"yes" if gh.token else "no (checks marked NOT RUN need a token)"}', '',
             '| Step | Check | Result | Detail | Evidence |', '|---|---|---|---|---|']
    lines += [f'| {s} | {c} | {r} | {d} | {f} |' for s, c, r, d, f in ev.rows]
    results = [r for _, _, r, _, _ in ev.rows]
    overall = 'FAIL' if 'FAIL' in results else 'INCOMPLETE' if {'NOT RUN', 'REVIEW', 'MANUAL'} & set(results) else 'PASS'
    lines += ['', f'**Overall: {overall}**', '',
              'PASS / FAIL: automatic result.  REVIEW: needs a decision.  MANUAL: evidence collected by hand.  '
              'INFO: recorded for the documentation.  NOT RUN: needs a token.  N/A: not applicable.', '']
    ev.save('SUMMARY.md', '\n'.join(lines))
    print('\n'.join(lines))
    print(f'Evidence saved in {folder}\n')
    return overall


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--repo', action='append', required=True, help='owner/name, repeat for several repositories')
    parser.add_argument('--tag', default=None, help='release tag to check (default: latest release of each repository)')
    parser.add_argument('--out', default='.', help='folder where the evidence folders are created (default: current folder)')
    args = parser.parse_args()
    token = findToken()
    if not token:
        print('No token found (GH_TOKEN, GITHUB_TOKEN or gh auth login): only the public checks will run.\n')
    gh = GitHub(token)
    results = [checkRepository(gh, repo, args.tag, args.out) for repo in args.repo]
    return 1 if 'FAIL' in results else 0


if __name__ == '__main__':
    sys.exit(main())
