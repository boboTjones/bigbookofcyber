#!/usr/bin/env python3

"""
deduplicate-urls.py - Clean and deduplicate GitHub repository URLs

Handles:
- Trailing slashes
- .git suffixes
- URLs pointing to subdirectories (/tree/, /blob/, /wiki/, etc.)
- Fragment identifiers (#)
- Query parameters (?)
- Random trailing characters
"""

import re
import sys
from pathlib import Path

def normalize_github_url(url):
    """
    Normalize a GitHub URL to just the base repository URL.

    Examples:
        https://github.com/user/repo/ -> https://github.com/user/repo
        https://github.com/user/repo.git -> https://github.com/user/repo
        https://github.com/user/repo/tree/master -> https://github.com/user/repo
        https://github.com/user/repo#section -> https://github.com/user/repo
    """
    url = url.strip()

    # Skip empty lines
    if not url:
        return None

    # Skip non-GitHub URLs
    if not url.startswith('https://github.com/'):
        return None

    # Remove fragment (#) and query string (?)
    url = re.sub(r'[#?].*$', '', url)

    # Remove .git suffix
    url = re.sub(r'\.git$', '', url)

    # Remove trailing slashes
    url = url.rstrip('/')

    # Extract just owner/repo from URLs with subdirectories
    # Match: https://github.com/owner/repo[/anything]
    match = re.match(r'(https://github\.com/[^/]+/[^/]+)', url)
    if match:
        return match.group(1)

    return url

def deduplicate_urls(input_file, output_file):
    """
    Read URLs from input file, normalize, deduplicate, and write to output file.
    """
    print(f"Reading URLs from: {input_file}")

    with open(input_file, 'r') as f:
        lines = f.readlines()

    print(f"Total lines read: {len(lines)}")

    # Normalize and collect unique URLs
    unique_urls = set()
    skipped = 0

    for line in lines:
        normalized = normalize_github_url(line)
        if normalized:
            unique_urls.add(normalized)
        else:
            skipped += 1

    # Sort URLs alphabetically
    sorted_urls = sorted(unique_urls)

    print(f"Unique URLs after deduplication: {len(sorted_urls)}")
    print(f"Duplicates removed: {len(lines) - len(sorted_urls) - skipped}")
    print(f"Lines skipped (empty/non-GitHub): {skipped}")

    # Write to output file
    with open(output_file, 'w') as f:
        for url in sorted_urls:
            f.write(url + '\n')

    print(f"\nCleaned URLs written to: {output_file}")

    return len(lines), len(sorted_urls)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 deduplicate-urls.py <input_file> [output_file]")
        print("\nExample:")
        print("  python3 deduplicate-urls.py bigbookofcyber/raw_list.txt")
        print("  python3 deduplicate-urls.py bigbookofcyber/raw_list.txt bigbookofcyber/clean_list.txt")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.txt', '_clean.txt')

    if not Path(input_file).exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    total, unique = deduplicate_urls(input_file, output_file)

    print("\nSummary:")
    print(f"  Original: {total} lines")
    print(f"  Cleaned:  {unique} unique URLs")
    print(f"  Saved:    {total - unique} duplicates removed")
