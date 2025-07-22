import os
import sys
import time
import logging
import argparse
from github import Github
from github.GithubException import GithubException

logging.basicConfig(
    filename='dependabot_automerge.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("Error: Please set your GITHUB_TOKEN environment variable.")
    sys.exit(1)

g = Github(GITHUB_TOKEN)

def is_dependabot_pr(pr, bots=None):
    if bots is None:
        bots = ["dependabot[bot]", "github-security[bot]"]
    return pr.user.login in bots

def check_pr_mergeable(pr, wait_seconds=5):
    """
    GitHub sometimes delays mergeability calculation, so retry a few times.
    """
    for i in range(5):
        pr.update()
        if pr.mergeable is not None:
            return pr.mergeable
        time.sleep(wait_seconds)
    return False

def is_ci_passed(pr):
    """
    Check if required status checks have passed on the PR's HEAD commit.
    """
    statuses = pr.get_combined_status().statuses
    if not statuses.totalCount:
        logging.info(f"PR #{pr.number}: No CI statuses found.")
        return False

    for status in statuses:
        if status.state != "success":
            logging.info(f"PR #{pr.number}: Status check '{status.context}' is '{status.state}'.")
            return False
    return True

def merge_dependabot_pr(pr, merge_method="squash", dry_run=False):
    logging.info(f"Evaluating PR #{pr.number} in {pr.base.repo.full_name}: '{pr.title}'")
    
    if dry_run:
        print(f"[Dry-run] Would merge PR #{pr.number} in {pr.base.repo.full_name}")
        return
    
    try:
        if not check_pr_mergeable(pr):
            logging.info(f"PR #{pr.number} is not mergeable.")
            print(f"PR #{pr.number} in {pr.base.repo.full_name} not mergeable.")
            return
        
        if not is_ci_passed(pr):
            logging.info(f"PR #{pr.number} CI checks not passed.")
            print(f"PR #{pr.number} in {pr.base.repo.full_name} CI not passed.")
            return

        print(f"Merging PR #{pr.number} in {pr.base.repo.full_name} - {pr.title}")
        pr.merge(merge_method=merge_method, commit_message="Auto-merged by dependabot-auto-merge script")
        logging.info(f"PR #{pr.number} merged successfully.")
        print(f"PR #{pr.number} merged.")
    except GithubException as e:
        logging.error(f"Failed to merge PR #{pr.number} due to error: {e}")
        print(f"Failed to merge PR #{pr.number} in {pr.base.repo.full_name}: {e}")

def get_repos_with_write_access():
    repos = []
    for repo in g.get_user().get_repos():
        if repo.permissions.push:
            repos.append(repo)
    return repos

def main(args):
    repos = get_repos_with_write_access()
    print(f"Found {len(repos)} repos with write access.")
    for repo in repos:
        if args.exclude_repos and repo.name in args.exclude_repos:
            print(f"Skipping excluded repo: {repo.full_name}")
            continue
        
        print(f"Checking repo: {repo.full_name}")
        pulls = repo.get_pulls(state='open', sort='updated', direction='desc')
        
        for pr in pulls:
            if is_dependabot_pr(pr):
                merge_dependabot_pr(pr, merge_method=args.merge_method, dry_run=args.dry_run)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-merge Dependabot PRs on your repos.")
    parser.add_argument("--merge-method", choices=["merge", "squash", "rebase"], default="squash",
                        help="Merge method to use for merging PRs.")
    parser.add_argument("--dry-run", action="store_true", help="Do not actually merge, just show what would be done.")
    parser.add_argument("--exclude-repos", nargs="*", default=[],
                        help="List of repo names to exclude from merging.")
    args = parser.parse_args()
    main(args)
