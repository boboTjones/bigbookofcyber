#!/usr/bin/env python3

"""
generate-catalog.py - Generate SECURITY_TOOLS_CATALOG.md from git repositories

Analyzes all git repositories in the current directory and creates a comprehensive
catalog with metadata, system requirements, build instructions, and categorization.
"""

import os
import re
import subprocess
from pathlib import Path
from datetime import datetime
import json

# Category keywords for classification
CATEGORY_KEYWORDS = {
    'Threat intelligence': [
        'threat', 'intelligence', 'ioc', 'indicator', 'misp', 'stix', 'taxii',
        'threat hunting', 'threat feed', 'apt', 'malware analysis', 'sandbox'
    ],
    'Incident Response (Blue Team)': [
        'incident response', 'dfir', 'forensics', 'blue team', 'defender',
        'memory forensic', 'disk forensic', 'triage', 'volatility'
    ],
    'Offensive Security (Red Team)': [
        'pentest', 'penetration', 'exploit', 'red team', 'adversary',
        'offensive', 'attack', 'payload', 'c2', 'command and control',
        'post-exploitation', 'privilege escalation'
    ],
    'Security Operations (SOC)': [
        'siem', 'log management', 'security operations', 'soc', 'detection',
        'monitoring', 'alert', 'correlation'
    ],
    'Application Security': [
        'appsec', 'sast', 'dast', 'dependency scan', 'code analysis',
        'web application', 'api security', 'injection', 'xss', 'sqli',
        'vulnerability scanner', 'burp', 'owasp'
    ],
    'Network/Infrastructure Security': [
        'network security', 'infrastructure', 'firewall', 'ids', 'ips',
        'packet', 'traffic analysis', 'pcap', 'wireshark', 'nmap',
        'port scan', 'network monitor'
    ],
    'Governance, Risk Management, Compliance and Audit': [
        'compliance', 'audit', 'governance', 'risk', 'grc', 'policy',
        'standard', 'regulation', 'gdpr', 'hipaa', 'pci'
    ],
    'Educational stuff': [
        'learning', 'tutorial', 'course', 'training', 'ctf', 'challenge',
        'practice', 'lab', 'exercise', 'workshop', 'educational'
    ],
    'Security blogs': [
        'blog', 'article', 'writeup', 'write-up', 'research', 'paper'
    ]
}

# Files that indicate system requirements
REQUIREMENT_FILES = {
    'requirements.txt': 'Python',
    'package.json': 'Node.js/JavaScript',
    'Gemfile': 'Ruby',
    'Cargo.toml': 'Rust',
    'go.mod': 'Go',
    'pom.xml': 'Java/Maven',
    'build.gradle': 'Java/Gradle',
    'Dockerfile': 'Docker',
    'docker-compose.yml': 'Docker Compose',
    'setup.py': 'Python',
    'pyproject.toml': 'Python',
    'composer.json': 'PHP',
    'packages.config': '.NET/NuGet',
    '*.csproj': '.NET/C#',
    'CMakeLists.txt': 'C/C++/CMake',
    'Makefile': 'Make/C/C++'
}

# Build/install documentation files
BUILD_DOC_FILES = [
    'README.md', 'README.rst', 'README.txt', 'README',
    'INSTALL.md', 'INSTALL.txt', 'INSTALL',
    'BUILD.md', 'BUILD.txt', 'BUILD',
    'BUILDING.md', 'CONTRIBUTING.md',
    'Makefile', 'CMakeLists.txt'
]


class RepositoryAnalyzer:
    def __init__(self, repo_path):
        self.path = Path(repo_path)
        self.name = self.path.name
        self.data = {}

    def is_git_repo(self):
        """Check if directory is a git repository"""
        return (self.path / '.git').exists()

    def get_remote_url(self):
        """Get the remote repository URL"""
        try:
            result = subprocess.run(
                ['git', 'config', '--get', 'remote.origin.url'],
                cwd=self.path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                # Clean up git URL
                url = url.replace('.git', '')
                url = re.sub(r'^git@github\.com:', 'https://github.com/', url)
                return url
        except Exception:
            pass
        return None

    def get_author(self):
        """Extract repository author from URL or git log"""
        url = self.get_remote_url()
        if url:
            match = re.search(r'github\.com/([^/]+)/', url)
            if match:
                return match.group(1)

        # Fallback to git log
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%an'],
                cwd=self.path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

        return 'Unknown'

    def get_last_commit_date(self):
        """Get the date of the last commit"""
        try:
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%cd', '--date=short'],
                cwd=self.path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return 'Unknown'

    def detect_requirements(self):
        """Detect system requirements from various files"""
        requirements = set()

        for file_pattern, tech in REQUIREMENT_FILES.items():
            if '*' in file_pattern:
                # Handle glob patterns
                pattern = file_pattern.replace('*', '')
                for file in self.path.rglob(f'*{pattern}'):
                    requirements.add(tech)
                    break
            else:
                if (self.path / file_pattern).exists():
                    requirements.add(tech)

        return sorted(requirements)

    def find_build_instructions(self):
        """Find files that contain build/install instructions"""
        build_files = []

        for doc_file in BUILD_DOC_FILES:
            file_path = self.path / doc_file
            if file_path.exists():
                build_files.append(doc_file)

        return build_files

    def extract_description(self):
        """Extract description/summary from README"""
        readme_files = ['README.md', 'README.rst', 'README.txt', 'README']

        for readme_name in readme_files:
            readme_path = self.path / readme_name
            if readme_path.exists():
                try:
                    with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(5000)  # Read first 5000 chars

                    # Try to extract first meaningful paragraph
                    # Skip title lines (starting with #)
                    lines = content.split('\n')
                    description_lines = []

                    for line in lines:
                        line = line.strip()
                        # Skip empty, title, or image lines
                        if not line or line.startswith('#') or line.startswith('!'):
                            continue
                        # Skip HTML tags
                        if line.startswith('<'):
                            continue
                        # Found description
                        if len(line) > 20:
                            description_lines.append(line)
                            if len(' '.join(description_lines)) > 200:
                                break

                    if description_lines:
                        description = ' '.join(description_lines[:3])  # First 3 lines
                        # Limit length
                        if len(description) > 500:
                            description = description[:497] + '...'
                        return description

                except Exception:
                    pass

        return 'No description available'

    def categorize(self, description, readme_content=''):
        """Categorize the repository based on keywords"""
        text = (self.name + ' ' + description + ' ' + readme_content).lower()

        category_scores = {}

        for category, keywords in CATEGORY_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                category_scores[category] = score

        if category_scores:
            # Return category with highest score
            return max(category_scores, key=category_scores.get)

        return 'Miscellaneous stuff to sort out later'

    def analyze(self):
        """Perform complete analysis of the repository"""
        if not self.is_git_repo():
            return None

        # Skip awesome lists (general programming)
        if 'awesome' in self.name.lower() and any(lang in self.name.lower() for lang in
            ['cpp', 'javascript', 'nodejs', 'python', 'ruby', 'dotnet', 'shell', 'java']):
            return None

        print(f"Analyzing: {self.name}")

        self.data = {
            'name': self.name,
            'author': self.get_author(),
            'remote_url': self.get_remote_url(),
            'last_commit': self.get_last_commit_date(),
            'requirements': self.detect_requirements(),
            'build_files': self.find_build_instructions(),
            'description': self.extract_description(),
        }

        self.data['category'] = self.categorize(self.data['description'])

        return self.data


def generate_catalog(output_file='bigbookofcyber/SECURITY_TOOLS_CATALOG.md'):
    """Generate the complete catalog from all repositories in CWD"""

    print("Scanning current directory for git repositories...")
    print()

    repos = []
    directories = [d for d in Path('.').iterdir() if d.is_dir() and not d.name.startswith('.')]

    print(f"Found {len(directories)} directories to analyze")
    print()

    for repo_dir in sorted(directories):
        analyzer = RepositoryAnalyzer(repo_dir)
        data = analyzer.analyze()
        if data:
            repos.append(data)

    print()
    print(f"Analyzed {len(repos)} security tool repositories")
    print()

    # Organize by category
    categories = {}
    for repo in repos:
        category = repo['category']
        if category not in categories:
            categories[category] = []
        categories[category].append(repo)

    # Sort repos within each category
    for category in categories:
        categories[category].sort(key=lambda x: x['name'].lower())

    # Generate markdown
    print(f"Generating catalog: {output_file}")

    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        f.write('# Security Tools Catalog\n\n')
        f.write('Comprehensive catalog of security tools and repositories.\n\n')
        f.write(f'**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
        f.write(f'**Total Repositories:** {len(repos)}\n\n')
        f.write('---\n\n')

        # Table of Contents
        f.write('## Table of Contents\n\n')
        for category in sorted(categories.keys()):
            count = len(categories[category])
            anchor = category.lower().replace(' ', '-').replace('(', '').replace(')', '').replace(',', '')
            f.write(f'- [{category}](#{anchor}) ({count} tools)\n')
        f.write('\n---\n\n')

        # Statistics
        f.write('## Statistics\n\n')
        f.write('| Category | Count |\n')
        f.write('|----------|-------|\n')
        for category in sorted(categories.keys(), key=lambda x: len(categories[x]), reverse=True):
            count = len(categories[category])
            f.write(f'| {category} | {count} |\n')
        f.write(f'| **TOTAL** | **{len(repos)}** |\n')
        f.write('\n---\n\n')

        # Categories and tools
        for category in sorted(categories.keys()):
            f.write(f'## {category}\n\n')

            for repo in categories[category]:
                f.write(f'### {repo["name"]}\n\n')

                if repo['remote_url']:
                    f.write(f'**Repository:** [{repo["remote_url"]}]({repo["remote_url"]})\n\n')

                f.write(f'**Author:** {repo["author"]}\n\n')
                f.write(f'**Last Updated:** {repo["last_commit"]}\n\n')

                if repo['requirements']:
                    f.write(f'**Requirements:** {", ".join(repo["requirements"])}\n\n')

                if repo['build_files']:
                    f.write(f'**Build Instructions:** See {", ".join(repo["build_files"])}\n\n')

                f.write(f'**Description:** {repo["description"]}\n\n')
                f.write('---\n\n')

    print()
    print('Catalog generation complete!')
    print()
    print('Summary:')
    print(f'  Total tools cataloged: {len(repos)}')
    print(f'  Categories: {len(categories)}')
    print(f'  Output file: {output_file}')


if __name__ == '__main__':
    import sys

    output_file = 'bigbookofcyber/SECURITY_TOOLS_CATALOG.md'
    if len(sys.argv) > 1:
        output_file = sys.argv[1]

    generate_catalog(output_file)
