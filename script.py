import os
import sys
import time
import logging
import argparse
from typing import List, Optional
from github import Github, Repository, PullRequest
from github.GithubException import GithubException

logging.basicConfig(
    filename='dependabot_automerge.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def get_github_client(token_env_var: str = "GITHUB_TOKEN") -> Github:
    """
    Initialize and return a Github client from an environment variable token.
    """
    token = os.getenv(token_env_var)
    if not token:
        logger.error(f"Environment variable '{token_env_var}' is not set.")
        print(f"Error: Please set your {token_env_var} environment variable.")
        sys.exit(1)
    return Github(token)


def is_dependabot_pr(pr: PullRequest.PullRequest, bots: Optional[List[str]] = None) -> bool:
    """
    Check if the PR was opened by Dependabot or specified bots.
    """
    if bots is None:
        bots = ["dependabot[bot]", "github-security[bot]"]
    return pr.user.login in bots


def wait_for_mergeable(pr: PullRequest.PullRequest, max_attempts: int = 5, delay_seconds: int = 5) -> bool:
    """
    Wait until GitHub sets the mergeable status on a PR or max attempts reached.
    """
    for _ in range(max_attempts):
        pr.update()
        if pr.mergeable is not None:
            return pr.mergeable
        time.sleep(delay_seconds)
    return False


def ci_checks_passed(pr: PullRequest.PullRequest) -> bool:
    """
    Check if all combined status checks for the PR's head commit have succeeded.
    """
    combined_status = pr.get_combined_status()
    if combined_status.total_count == 0:
        logger.info(f"PR #{pr.number}: No CI status checks found.")
        return False

    for status in combined_status.statuses:
        if status.state.lower() != "success":
            logger.info(f"PR #{pr.number}: CI check '{status.context}' state is '{status.state}'.")
            return False
    return True


def merge_pr(pr: PullRequest.PullRequest, merge_method: str = "squash", dry_run: bool = False) -> None:
    """
    Attempt to merge the PR if possible, respecting dry run mode.
    """
    repo_name = pr.base.repo.full_name
    logger.info(f"Evaluating PR #{pr.number} in {repo_name}: '{pr.title}'")

    if dry_run:
        print(f"[Dry-run] Would merge PR #{pr.number} in {repo_name} - '{pr.title}'")
        return

    if not wait_for_mergeable(pr):
        logger.info(f"PR #{pr.number} in {repo_name} is not mergeable.")
        print(f"PR #{pr.number} in {repo_name} is not mergeable.")
        return

    if not ci_checks_passed(pr):
        logger.info(f"PR #{pr.number} in {repo_name} failed CI checks.")
        print(f"PR #{pr.number} in {repo_name} failed CI checks.")
        return

    try:
        print(f"Merging PR #{pr.number} in {repo_name} - '{pr.title}'")
        pr.merge(merge_method=merge_method, commit_message="Auto-merged by dependabot-auto-merge script")
        logger.info(f"PR #{pr.number} in {repo_name} merged successfully.")
        print(f"PR #{pr.number} merged successfully.")
    except GithubException as e:
        logger.error(f"Failed to merge PR #{pr.number} in {repo_name}: {e}")
        print(f"Failed to merge PR #{pr.number} in {repo_name}: {e}")


def get_user_repos_with_write_access(github_client: Github) -> List[Repository.Repository]:
    """
    Retrieve all repositories the authenticated user has write access to.
    """
    user = github_client.get_user()
    repos = []
    for repo in user.get_repos():
        if repo.permissions.push:
            repos.append(repo)
    return repos


def main(args: argparse.Namespace) -> None:
    github_client = get_github_client()
    repos = get_user_repos_with_write_access(github_client)
    print(f"Found {len(repos)} repositories with write access.")

    for repo in repos:
        if args.exclude_repos and repo.name in args.exclude_repos:
            print(f"Skipping excluded repository: {repo.full_name}")
            continue

        print(f"Checking repository: {repo.full_name}")
        pulls = repo.get_pulls(state='open', sort='updated', direction='desc')

        for pr in pulls:
            if is_dependabot_pr(pr):
                merge_pr(pr, merge_method=args.merge_method, dry_run=args.dry_run)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-merge Dependabot PRs on your repositories.")
    parser.add_argument(
        "--merge-method",
        choices=["merge", "squash", "rebase"],
        default="squash",
        help="Merge method to use when merging PRs."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show PRs that would be merged without actually merging."
    )
    parser.add_argument(
        "--exclude-repos",
        nargs="*",
        default=[],
        help="List of repository names to exclude from processing."
    )
    args = parser.parse_args()

    main(args)
