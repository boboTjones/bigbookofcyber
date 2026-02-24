#!/usr/bin/env python3

"""
scan-and-fetch.py - Scan cloned repositories and fetch GitHub API metadata

Combines build-api-urls.py and fetch-repo-data.py into a single pipeline:
  1. Scans a directory of cloned git repos and extracts their GitHub API URLs
  2. Fetches metadata for each repo from the GitHub API
  3. Writes all responses to a JSON array file for later ETL processing

Usage:
    python3 utils/scan-and-fetch.py [--dir DIR] [--output FILE] [--delay SECONDS]
                                    [--save-urls FILE]

Environment:
    GH_TOKEN  GitHub personal access token (required)

Notes:
    With a GitHub token the rate limit is 5,000 req/hour (~0.72s minimum delay).
    Default delay is 1.0 second, which keeps well within that limit.
    On a 429 or rate-limit 403, the script pauses until the X-RateLimit-Reset time.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path


DEFAULT_DELAY = 1.0
SKIP_DIRS = {'bigbookofcyber', 'utils', '.claude', '.git'}


# ---------------------------------------------------------------------------
# URL building (from build-api-urls.py)
# ---------------------------------------------------------------------------

def get_fetch_origin(repo_path):
    """Run `git remote -v` and return the fetch origin URL, or None."""
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
        if line.startswith('origin') and '(fetch)' in line:
            parts = line.split()
            if len(parts) >= 2:
                return parts[1]

    return None


def extract_owner_repo(remote_url):
    """
    Extract owner/repo from a GitHub remote URL.

    Handles HTTPS and SSH formats, with or without .git suffix or trailing slash.
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


def scan_repos(target_dir):
    """
    Walk target_dir and return a sorted list of GitHub API URLs.

    Also returns a list of error strings for repos that could not be resolved.
    """
    api_urls = []
    errors = []
    skipped_not_git = 0

    entries = sorted(target_dir.iterdir())
    candidates = [e for e in entries if e.is_dir() and e.name not in SKIP_DIRS and not e.name.startswith('.')]
    total = len(candidates)

    print(f'Scanning {total} directories in {target_dir} ...')

    for idx, entry in enumerate(candidates):
        if not (entry / '.git').exists():
            skipped_not_git += 1
            continue

        if (idx + 1) % 100 == 0:
            print(f'  {idx + 1}/{total} scanned ...')

        remote_url = get_fetch_origin(entry)
        if not remote_url:
            errors.append(f'no-origin: {entry.name}')
            continue

        owner_repo = extract_owner_repo(remote_url)
        if not owner_repo:
            errors.append(f'non-github: {entry.name}  ({remote_url})')
            continue

        api_urls.append(f'https://api.github.com/repos/{owner_repo}')

    api_urls.sort()

    print(f'  Found {len(api_urls)} GitHub repos'
          f'  (skipped {skipped_not_git} non-git dirs, {len(errors)} unresolvable)')

    return api_urls, errors


# ---------------------------------------------------------------------------
# HTTP fetching (from fetch-repo-data.py)
# ---------------------------------------------------------------------------

def fetch(url, token):
    """
    Make an authenticated GET request to the GitHub API.

    Returns (data_dict, http_status_code, rate_limit_remaining, reset_timestamp).
    HTTP error bodies are returned as dicts so they appear in the output file.
    """
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Accept', 'application/vnd.github+json')
    req.add_header('X-GitHub-Api-Version', '2022-11-28')
    req.add_header('User-Agent', 'bigbookofcyber-fetch/1.0')

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            reset_ts = int(resp.headers.get('X-RateLimit-Reset', 0))
            remaining = int(resp.headers.get('X-RateLimit-Remaining', -1))
            return data, resp.status, remaining, reset_ts

    except urllib.error.HTTPError as e:
        reset_ts = int(e.headers.get('X-RateLimit-Reset', 0))
        remaining = int(e.headers.get('X-RateLimit-Remaining', -1))
        try:
            body = json.loads(e.read().decode('utf-8'))
        except Exception:
            body = {'message': str(e), 'url': url}
        return body, e.code, remaining, reset_ts

    except urllib.error.URLError as e:
        return {'error': str(e), 'url': url}, 0, -1, 0

    except Exception as e:
        return {'error': str(e), 'url': url}, 0, -1, 0


def wait_for_reset(reset_ts, label='rate limit reset'):
    """Sleep until the GitHub rate limit reset timestamp, plus a small buffer."""
    now = time.time()
    wait = max(reset_ts - now + 2, 1)
    wake = datetime.fromtimestamp(reset_ts).strftime('%H:%M:%S')
    print(f'\n  [rate limit] waiting {wait:.0f}s until {wake} ({label})')
    time.sleep(wait)


def fetch_all(api_urls, token, output_path, delay):
    """Fetch each URL and stream responses into a JSON array file."""
    total = len(api_urls)
    ok_count = 0
    err_count = 0
    start_time = time.time()

    print(f'\nFetching {total} repos -> {output_path}')
    print(f'Delay: {delay}s between requests')
    print(f'Started: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()

    with open(output_path, 'w') as out:
        out.write('[\n')

        for idx, url in enumerate(api_urls):
            label = '/'.join(url.split('/')[-2:])
            prefix = f'[{idx + 1}/{total}]'

            data, status, remaining, reset_ts = fetch(url, token)

            if status == 200:
                ok_count += 1
                status_str = '200'
            else:
                err_count += 1
                status_str = str(status) if status else 'ERR'

            elapsed = time.time() - start_time
            rate = (idx + 1) / elapsed if elapsed > 0 else 0
            eta_s = (total - idx - 1) / rate if rate > 0 else 0
            eta_str = f'{int(eta_s // 60)}m{int(eta_s % 60):02d}s'

            print(f'{prefix} {label:<45} {status_str}  (remaining: {remaining}  eta: {eta_str})')

            if idx > 0:
                out.write(',\n')
            out.write(json.dumps(data, indent=2))
            out.flush()

            if status in (429, 403) and remaining == 0 and reset_ts:
                wait_for_reset(reset_ts, label=f'after {label}')
                continue

            if idx < total - 1:
                time.sleep(delay)

        out.write('\n]\n')

    elapsed_total = time.time() - start_time
    print()
    print(f'Done.  {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'  Total:    {total}')
    print(f'  Success:  {ok_count}')
    print(f'  Errors:   {err_count}')
    print(f'  Elapsed:  {int(elapsed_total // 60)}m{int(elapsed_total % 60):02d}s')
    print(f'  Output:   {output_path}')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    script_dir = Path(__file__).parent.resolve()
    logs_dir = script_dir / 'logs'

    parser = argparse.ArgumentParser(
        description='Scan cloned repos and fetch GitHub API metadata into a JSON array.'
    )
    parser.add_argument(
        '--dir', '-d',
        default=str(Path.cwd()),
        help='Directory containing cloned repositories (default: cwd)'
    )
    parser.add_argument(
        '--output', '-o',
        default=str(logs_dir / 'github-api-responses.json'),
        help='Output JSON array file (default: logs/github-api-responses.json)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=DEFAULT_DELAY,
        help=f'Seconds to sleep between API requests (default: {DEFAULT_DELAY})'
    )
    parser.add_argument(
        '--save-urls',
        metavar='FILE',
        default=None,
        help='Optionally save the collected API URLs to a text file before fetching'
    )
    return parser.parse_args()


def main():
    args = parse_args()

    token = os.environ.get('GH_TOKEN', '').strip()
    if not token:
        print('Error: GH_TOKEN environment variable is not set.')
        print('  export GH_TOKEN=your_token_here')
        sys.exit(1)

    target_dir = Path(args.dir).resolve()
    if not target_dir.is_dir():
        print(f'Error: directory not found: {target_dir}')
        sys.exit(1)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Phase 1: scan
    api_urls, errors = scan_repos(target_dir)

    if errors:
        script_dir = Path(__file__).parent.resolve()
        error_file = script_dir / 'logs' / 'scan-and-fetch-errors.txt'
        error_file.parent.mkdir(parents=True, exist_ok=True)
        with open(error_file, 'w') as f:
            f.write(f'# scan-and-fetch errors - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
            for line in errors:
                f.write(line + '\n')
        print(f'  Scan errors logged to: {error_file}')

    if args.save_urls:
        url_path = Path(args.save_urls)
        url_path.parent.mkdir(parents=True, exist_ok=True)
        with open(url_path, 'w') as f:
            for url in api_urls:
                f.write(url + '\n')
        print(f'  API URLs saved to: {url_path}')

    if not api_urls:
        print('No GitHub repos found. Exiting.')
        sys.exit(0)

    print()

    # Phase 2: fetch
    fetch_all(api_urls, token, output_path, args.delay)


if __name__ == '__main__':
    main()
