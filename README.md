# Big Book of Cyber

A curated collection of security tools, organized by category, with analysis and documentation.

## About This Project

This repository catalogs **1,380 security tools** across multiple categories, providing a comprehensive reference for security professionals, researchers, and enthusiasts.

Each category has its own directory with a detailed README listing all relevant tools.

---

## Categories

### [Threat Intelligence](threatintel/) (103 tools)
Tools for gathering, analyzing, and acting on threat intelligence data.

### [Offensive Security (Red Team)](offsec/) (46 tools)
Penetration testing, exploitation, and red team tools for security assessment.

### [Application Security](appsec/) (59 tools)
Tools for securing applications, including SAST, DAST, dependency scanning, and more.

### [Network/Infrastructure Security](netsec/) (48 tools)
Network monitoring, infrastructure security, and hardening tools.

### [Incident Response (Blue Team)](increp/) (13 tools)
Tools for detecting, responding to, and recovering from security incidents.

### [Security Operations (SOC)](soc/) (16 tools)
SIEM, log management, and security monitoring platforms.

### [Governance, Risk & Compliance](grca/) (9 tools)
GRC, audit, and compliance management tools.

### [Education & Resources](education/) (30 tools)
Educational resources, tutorials, security blogs, and learning materials.

### [Miscellaneous](misc/) (1,056 tools)
Tools awaiting categorization or that don't fit neatly into other categories.

---

## Statistics

| Category | Tool Count | Directory |
|----------|------------|-----------|
| Threat Intelligence | 103 | [threatintel/](threatintel/) |
| Application Security | 59 | [appsec/](appsec/) |
| Network/Infrastructure Security | 48 | [netsec/](netsec/) |
| Offensive Security (Red Team) | 46 | [offsec/](offsec/) |
| Education & Resources | 30 | [education/](education/) |
| Security Operations (SOC) | 16 | [soc/](soc/) |
| Incident Response (Blue Team) | 13 | [increp/](increp/) |
| Governance, Risk & Compliance | 9 | [grca/](grca/) |
| Miscellaneous | 1,056 | [misc/](misc/) |
| **TOTAL** | **1,380** | |

---

## Workflow & Plans

### Current Status
- Tools cataloged and organized by category
- Metadata extracted (author, last update, description)
- Selecting top 100 most popular tools (by stars/activity)
- Systematic evaluation and blog post writing in progress

### Selection Criteria for Deep Dives
- **Popularity:** GitHub stars, forks, community engagement
- **Activity:** Updated within the last year
- **Impact:** Tools that solve real security problems
- **Coverage:** Representation across all categories

### Planned Content
Each tool evaluation will include:
- Detailed setup and configuration guide
- Real-world use cases and examples
- Pros and cons analysis
- Integration with other tools
- Security considerations
- Blog post with hands-on demonstrations

---

## Using This Repository

### Browse by Category
Navigate to any category directory and read the README to see all tools in that category.

### Find Specific Tools
Use GitHub's search functionality or `grep` to find tools by name or keyword:

```bash
# Search all READMEs for a keyword
grep -r "keyword" */README.md

# List all tools with specific technology
grep -r "Python" */README.md
```

### Check Last Updated
Each tool entry includes the last commit date to help identify actively maintained projects.

---

## Contributing

This is a living document. As tools are evaluated:
- Tools may be recategorized from `misc/` to appropriate categories
- New categories may be added
- Tool descriptions will be enhanced based on hands-on evaluation
- Blog posts and detailed guides will be added

---

## Related Files

- **[SECURITY_TOOLS_CATALOG.md](SECURITY_TOOLS_CATALOG.md)** - Original complete catalog (all categories in one file)
---

## License

This is a curated collection of links to open source security tools. Each tool has its own license - please refer to individual repositories for licensing information.

---

**Last Updated:** 2026-02-13

**Maintained by:** Erin L Ptacek (aka boboTjones)

---
