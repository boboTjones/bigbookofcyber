#!/usr/bin/env python3

"""
fetch-repo-data.py - Fetch GitHub API metadata for all cloned repositories

Reads URLs from utils/logs/github-api-urls.txt, makes authenticated GET requests
to the GitHub API, and writes all responses to utils/logs/github-api-responses.json
as a single JSON array suitable for later ETL processing.

Usage:
    python3 utils/fetch-repo-data.py [--delay SECONDS] [--input FILE] [--output FILE]

Environment:
    GH_TOKEN  GitHub personal access token (required)

Notes:
    With a GitHub token the rate limit is 5,000 req/hour (~0.72s minimum delay).
    Default delay is 1.0 second, which keeps well within that limit.
    On a 429 or rate-limit 403, the script will pause until the reset time
    reported in the X-RateLimit-Reset header before resuming.
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DELAY = 1.0  # seconds between requests


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def fetch(url, token):
    """
    Make an authenticated GET request to the GitHub API.

    Returns (data_dict, http_status_code).
    On HTTP errors the error JSON body is still returned so it lands in the
    output file alongside successful responses.
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    script_dir = Path(__file__).parent.resolve()
    logs_dir = script_dir / 'logs'

    parser = argparse.ArgumentParser(
        description='Fetch GitHub API repo metadata and write to a JSON array file.'
    )
    parser.add_argument(
        '--input', '-i',
        default=str(logs_dir / 'github-api-urls.txt'),
        help='Path to newline-separated list of GitHub API URLs (default: logs/github-api-urls.txt)'
    )
    parser.add_argument(
        '--output', '-o',
        default=str(logs_dir / 'github-api-responses.json'),
        help='Path to output JSON array file (default: logs/github-api-responses.json)'
    )
    parser.add_argument(
        '--delay', '-d',
        type=float,
        default=DEFAULT_DELAY,
        help=f'Seconds to sleep between requests (default: {DEFAULT_DELAY})'
    )
    return parser.parse_args()


def main():
    args = parse_args()

    token = os.environ.get('GH_TOKEN', '').strip()
    if not token:
        print('Error: GH_TOKEN environment variable is not set.')
        print('  export GH_TOKEN=your_token_here')
        sys.exit(1)

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f'Error: input file not found: {input_path}')
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(input_path) as f:
        urls = [line.strip() for line in f if line.strip()]

    total = len(urls)
    print(f'Input:  {input_path}  ({total} URLs)')
    print(f'Output: {output_path}')
    print(f'Delay:  {args.delay}s between requests')
    print(f'Started: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()

    ok_count = 0
    err_count = 0
    start_time = time.time()

    with open(output_path, 'w') as out:
        out.write('[\n')

        for idx, url in enumerate(urls):
            # Extract owner/repo from URL for display
            label = '/'.join(url.split('/')[-2:])
            prefix = f'[{idx + 1}/{total}]'

            data, status, remaining, reset_ts = fetch(url, token)

            if status == 200:
                ok_count += 1
                status_str = '200'
            else:
                err_count += 1
                status_str = str(status) if status else 'ERR'

            # Elapsed and ETA
            elapsed = time.time() - start_time
            rate = (idx + 1) / elapsed if elapsed > 0 else 0
            eta_s = (total - idx - 1) / rate if rate > 0 else 0
            eta_str = f'{int(eta_s // 60)}m{int(eta_s % 60):02d}s'

            print(f'{prefix} {label:<45} {status_str}  (remaining: {remaining}  eta: {eta_str})')

            # Write to JSON array
            if idx > 0:
                out.write(',\n')
            out.write(json.dumps(data, indent=2))
            out.flush()

            # Handle rate limiting
            if status in (429, 403) and remaining == 0 and reset_ts:
                wait_for_reset(reset_ts, label=f'after {label}')
                continue  # skip the normal delay after a reset wait

            # Normal inter-request delay
            if idx < total - 1:
                time.sleep(args.delay)

        out.write('\n]\n')

    elapsed_total = time.time() - start_time
    print()
    print(f'Done.  {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'  Total:    {total}')
    print(f'  Success:  {ok_count}')
    print(f'  Errors:   {err_count}')
    print(f'  Elapsed:  {int(elapsed_total // 60)}m{int(elapsed_total % 60):02d}s')
    print(f'  Output:   {output_path}')


if __name__ == '__main__':
    main()
