#!/usr/bin/env python3
"""
PyPI package integrity check for TheiaMCR (CRA-RA-002 PY-08).

For one released version this script:
1. Downloads the wheel and sdist from PyPI and checks that their SHA-256 matches the hash PyPI publishes.
2. Installs the wheel with `pip install --require-hashes` to show that the published file is accepted.
3. Changes one byte in a copy of the wheel and installs it the same way, to show that pip rejects a tampered file.
4. Reads the PyPI provenance (trusted publishing attestation) of each file and checks that it was published by the
   expected GitHub repository.

Usage:
    python .github/scripts/verify_pypi_integrity.py [--version 3.5.2] [--require-provenance] [--output report.md]

The version defaults to the one in pyproject.toml.  Exit code 0 = all checks passed, 1 = a check failed.
Only the Python standard library and pip are needed.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

PROJECT = 'TheiaMCR'
EXPECTED_REPOSITORY = 'cliquot22/TheiaMCR'
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def projectVersion():
    with open(os.path.join(REPO_ROOT, 'pyproject.toml'), encoding='utf-8') as f:
        match = re.search(r'^version\s*=\s*"([^"]+)"', f.read(), re.MULTILINE)
    return match.group(1)


def getJson(url, accept='application/json'):
    request = urllib.request.Request(url, headers={'Accept': accept, 'User-Agent': 'TheiaMCR-integrity-check'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def releaseFiles(version, waitMinutes):
    """Return the PyPI file list for the version, waiting for a new upload to appear."""
    url = f'https://pypi.org/pypi/{PROJECT}/{version}/json'
    deadline = time.monotonic() + waitMinutes * 60
    while True:
        try:
            return getJson(url)['urls']
        except urllib.error.HTTPError as e:
            if e.code != 404 or time.monotonic() > deadline:
                raise
        print(f'{PROJECT} {version} not on PyPI yet, retrying in 20 s...')
        time.sleep(20)


def download(url, folder):
    path = os.path.join(folder, url.rsplit('/', 1)[-1])
    urllib.request.urlretrieve(url, path)
    return path


def sha256(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def pipInstall(findLinks, version, hashValue, target):
    """pip install the version from a local folder only, requiring the given hash.  Return (accepted, output)."""
    requirements = os.path.join(target, 'requirements.txt')
    os.makedirs(target, exist_ok=True)
    with open(requirements, 'w', encoding='utf-8') as f:
        f.write(f'{PROJECT}=={version} --hash=sha256:{hashValue}\n')
    run = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '--no-index', '--find-links', findLinks, '--require-hashes',
         '--no-deps', '--disable-pip-version-check', '--target', os.path.join(target, 'site'), '-r', requirements],
        capture_output=True, text=True)
    return run.returncode == 0, (run.stdout + run.stderr).strip()


def provenance(version, filename):
    """Return the publisher of each attestation for the file, or None if PyPI has no provenance for it."""
    url = f'https://pypi.org/integrity/{PROJECT}/{version}/{filename}/provenance'
    try:
        data = getJson(url, accept='application/vnd.pypi.integrity.v1+json')
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    return [bundle.get('publisher', {}) for bundle in data.get('attestation_bundles', [])]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--version', default=None, help='version to check (default: pyproject.toml version)')
    parser.add_argument('--require-provenance', action='store_true',
                        help='fail if a file has no trusted publishing provenance')
    parser.add_argument('--wait', type=float, default=0, help='minutes to wait for the version to appear on PyPI')
    parser.add_argument('--output', default=None, help='also write the report to this Markdown file')
    args = parser.parse_args()
    version = args.version or projectVersion()

    lines = [f'# PyPI integrity check: {PROJECT} {version}', '',
             f'- **Date**: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}',
             f'- **PyPI**: https://pypi.org/project/{PROJECT}/{version}/',
             f'- **pip**: {subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, text=True).stdout.split(" from ")[0]}',
             '']
    results = []

    def check(name, passed, detail='', label=None):
        results.append(passed)
        lines.append(f'| {name} | {label or ("PASS" if passed else "FAIL")} | {detail} |')

    files = releaseFiles(version, args.wait)
    work = tempfile.mkdtemp(prefix='theiamcr-integrity-')
    try:
        lines += ['## 1. Published files match the PyPI hashes', '', '| Check | Result | Detail |', '|---|---|---|']
        downloaded = {}
        for info in files:
            path = download(info['url'], work)
            downloaded[info['packagetype']] = (path, info['digests']['sha256'])
            actual = sha256(path)
            check(f'`{info["filename"]}` SHA-256', actual == info['digests']['sha256'], f'`{actual}`')
        check('wheel and sdist both published', {'bdist_wheel', 'sdist'} <= set(downloaded), ', '.join(sorted(downloaded)))

        lines += ['', '## 2. pip accepts the published wheel and rejects a tampered copy', '',
                  'Each copy is installed with `pip install --require-hashes`, using the SHA-256 published on PyPI.', '',
                  '| Check | Result | Detail |', '|---|---|---|']
        wheel, wheelHash = downloaded['bdist_wheel']
        goodDir = os.path.join(work, 'good')
        tamperedDir = os.path.join(work, 'tampered')
        os.makedirs(goodDir)
        os.makedirs(tamperedDir)
        shutil.copy(wheel, goodDir)
        tamperedWheel = shutil.copy(wheel, tamperedDir)
        with open(tamperedWheel, 'r+b') as f:
            data = bytearray(f.read())
            data[len(data) // 2] ^= 0xFF            # change one byte in the middle of the file
            f.seek(0)
            f.write(data)

        accepted, output = pipInstall(goodDir, version, wheelHash, os.path.join(work, 'install-good'))
        check('published wheel installs', accepted, 'accepted' if accepted else output.splitlines()[-1])
        accepted, output = pipInstall(tamperedDir, version, wheelHash, os.path.join(work, 'install-tampered'))
        rejectedForHash = (not accepted) and 'do not match the hashes' in output.lower()
        check('tampered wheel (1 byte changed) is rejected', rejectedForHash,
              f'tampered SHA-256 `{sha256(tamperedWheel)}`; pip: "THESE PACKAGES DO NOT MATCH THE HASHES"'
              if rejectedForHash else output.splitlines()[-1] if output else 'installed')

        lines += ['', '## 3. Provenance (trusted publishing)', '', '| Check | Result | Detail |', '|---|---|---|']
        for info in files:
            publishers = provenance(version, info['filename'])
            label = None
            if publishers is None:
                detail = 'no provenance on PyPI (not uploaded with trusted publishing)'
                passed = not args.require_provenance
                label = None if args.require_provenance else 'N/A'
            else:
                repos = {p.get('repository') for p in publishers}
                detail = '; '.join(f'{p.get("kind")} {p.get("repository")} workflow `{p.get("workflow")}`'
                                   f' environment `{p.get("environment")}`' for p in publishers)
                passed = repos == {EXPECTED_REPOSITORY}
            check(f'`{info["filename"]}` provenance', passed, detail, label)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    overall = all(results)
    lines += ['', f'**Overall: {"PASS" if overall else "FAIL"}**', '']
    report = '\n'.join(lines)
    print(report)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
    return 0 if overall else 1


if __name__ == '__main__':
    sys.exit(main())
