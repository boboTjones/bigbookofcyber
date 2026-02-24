#!/usr/bin/env python3

"""
build-api-urls.py - Collect GitHub API URLs for all cloned repositories

For each git repository in the target directory, reads the fetch origin remote,
extracts the owner/repo path, and constructs the corresponding GitHub API URL.

Output: utils/logs/github-api-urls.txt

Usage:
    python3 utils/build-api-urls.py [target_dir]

    target_dir defaults to the current working directory.
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime


SKIP_DIRS = {'bigbookofcyber', 'utils', '.claude', '.git'}


def get_fetch_origin(repo_path):
    """
    Run `git remote -v` in repo_path and return the fetch origin URL, or None.
    """
    try:
        result = subprocess.run(
            ['git', 'remote', '-v'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    if result.returncode != 0:
        return None

    for line in result.stdout.splitlines():
        # Lines look like:
        #   origin  https://github.com/owner/repo.git (fetch)
        #   origin  git@github.com:owner/repo.git (fetch)
        if line.startswith('origin') and '(fetch)' in line:
            parts = line.split()
            if len(parts) >= 2:
                return parts[1]

    return None


def extract_owner_repo(remote_url):
    """
    Extract the owner/repo path from a GitHub remote URL.

    Handles:
        https://github.com/owner/repo.git
        https://github.com/owner/repo
        git@github.com:owner/repo.git
        git@github.com:owner/repo
    """
    # HTTPS format
    match = re.match(r'https://github\.com/([^/]+/[^/]+?)(?:\.git)?/?$', remote_url.strip())
    if match:
        return match.group(1)

    # SSH format
    match = re.match(r'git@github\.com:([^/]+/[^/]+?)(?:\.git)?/?$', remote_url.strip())
    if match:
        return match.group(1)

    return None


def build_api_url(owner_repo):
    return f"https://api.github.com/repos/{owner_repo}"


def main():
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    target_dir = target_dir.resolve()

    # Output goes in utils/logs/ relative to this script
    script_dir = Path(__file__).parent.resolve()
    logs_dir = script_dir / 'logs'
    logs_dir.mkdir(exist_ok=True)
    output_file = logs_dir / 'github-api-urls.txt'

    print(f"Scanning: {target_dir}")
    print(f"Output:   {output_file}")
    print()

    api_urls = []
    skipped_not_git = 0
    skipped_no_origin = 0
    skipped_not_github = 0
    errors = []

    entries = sorted(target_dir.iterdir())
    total = len([e for e in entries if e.is_dir() and e.name not in SKIP_DIRS])
    processed = 0

    for entry in entries:
        if not entry.is_dir():
            continue
        if entry.name in SKIP_DIRS or entry.name.startswith('.'):
            continue

        # Must be a git repo
        if not (entry / '.git').exists():
            skipped_not_git += 1
            continue

        processed += 1
        if processed % 100 == 0:
            print(f"  {processed}/{total} repos processed...")

        remote_url = get_fetch_origin(entry)
        if not remote_url:
            skipped_no_origin += 1
            errors.append(f"no-origin: {entry.name}")
            continue

        owner_repo = extract_owner_repo(remote_url)
        if not owner_repo:
            skipped_not_github += 1
            errors.append(f"non-github: {entry.name}  ({remote_url})")
            continue

        api_urls.append(build_api_url(owner_repo))

    # Write output
    api_urls.sort()
    with open(output_file, 'w') as f:
        for url in api_urls:
            f.write(url + '\n')

    print(f"\nDone.")
    print(f"  Repos scanned:       {processed}")
    print(f"  API URLs written:    {len(api_urls)}")
    print(f"  Skipped (not git):   {skipped_not_git}")
    print(f"  Skipped (no origin): {skipped_no_origin}")
    print(f"  Skipped (non-GitHub):{skipped_not_github}")

    if errors:
        error_file = logs_dir / 'build-api-urls-errors.txt'
        with open(error_file, 'w') as f:
            f.write(f"# build-api-urls errors - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            for line in errors:
                f.write(line + '\n')
        print(f"\n  Errors logged to: {error_file}")

    print(f"\n  Output: {output_file}")


if __name__ == '__main__':
    main()
