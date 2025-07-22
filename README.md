# Auto Merge Dependabot PRs

A Python script to automatically find and merge open Dependabot pull requests across all your personal repositories and repositories you have write access to. It merges only Dependabot PRs that have passed all required CI checks and are mergeable.

---

## Features

- Scans all repositories with write access for open Dependabot PRs.
- Checks that PRs are mergeable and have passing CI status checks.
- Supports three GitHub merge methods: `merge`, `squash`, and `rebase`.
- Dry-run mode to preview PRs that would be merged without actually merging.
- Option to exclude specific repositories from the scan.
- Handles GitHub API rate limits and errors gracefully.
- Logs actions and errors to a file `dependabot_automerge.log`.

---

## Requirements

- Python 3.7+
- [PyGithub](https://pypi.org/project/PyGithub/)

```bash
pip install PyGithub
````

* A GitHub personal access token with `repo` permissions.
  Create one at [GitHub Developer Settings](https://github.com/settings/tokens) and set it as an environment variable:

```bash
export GITHUB_TOKEN="your_personal_access_token"
```

---

## Usage

Run the script with optional arguments:

```bash
python script.py [--merge-method {merge,squash,rebase}] [--dry-run] [--exclude-repos repo1 repo2 ...]
```

### Arguments

| Argument          | Description                                           | Default  |
| ----------------- | ----------------------------------------------------- | -------- |
| `--merge-method`  | Merge strategy to use: `merge`, `squash`, or `rebase` | `squash` |
| `--dry-run`       | Show which PRs would be merged without merging them   | False    |
| `--exclude-repos` | Space-separated list of repository names to exclude   | None     |

### Example

Merge Dependabot PRs in all repos using squash method, excluding a repo called `test-repo`:

```bash
python script.py --merge-method squash --exclude-repos test-repo
```

Preview what would be merged (dry run):

```bash
python script.py --dry-run
```

---

## Logging

All actions and errors are logged to `dependabot_automerge.log` in the script directory.

---

## License

MIT License © 2025 Max Base

See [LICENSE](LICENSE) for details.

---

## Disclaimer

Use this script at your own risk. It assumes you trust Dependabot PRs and that your CI checks are correctly configured.

---

## Author

Max Base

[https://github.com/BaseMax](https://github.com/BaseMax)
