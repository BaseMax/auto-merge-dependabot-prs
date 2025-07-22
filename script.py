import os
import sys
import time
import logging
import argparse
from typing import List, Optional
from github import Github, Repository, PullRequest
from github.GithubException import GithubException, RateLimitExceededException

logging.basicConfig(
    filename="dependabot_automerge.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_github_client(token_env_var: str = "GITHUB_TOKEN") -> Github:
    token = os.getenv(token_env_var)
    if not token:
        logger.error(f"Environment variable '{token_env_var}' is not set.")
        print(f"Error: Please set your {token_env_var} environment variable.")
        sys.exit(1)
    return Github(token)


def is_dependabot_pr(pr: PullRequest.PullRequest, bots: Optional[List[str]] = None) -> bool:
    if bots is None:
        bots = ["dependabot[bot]", "github-security[bot]"]
    return pr.user.login in bots


def wait_for_mergeable(pr: PullRequest.PullRequest, attempts: int = 5, delay: int = 5) -> bool:
    for _ in range(attempts):
        try:
            pr.update()
        except GithubException as e:
            logger.warning(f"Failed to update PR #{pr.number}: {e}")
            return False
        if pr.mergeable is not None:
            return pr.mergeable
        time.sleep(delay)
    return False


def ci_checks_passed(pr: PullRequest.PullRequest) -> bool:
    try:
        combined_status = pr.get_combined_status()
    except GithubException as e:
        logger.warning(f"Failed to get combined status for PR #{pr.number}: {e}")
        return False

    if combined_status.total_count == 0:
        logger.info(f"PR #{pr.number}: No CI status checks found.")
        return False

    for status in combined_status.statuses:
        if status.state.lower() != "success":
            logger.info(f"PR #{pr.number}: CI check '{status.context}' state is '{status.state}'.")
            return False
    return True


def merge_pr(pr: PullRequest.PullRequest, merge_method: str = "squash", dry_run: bool = False) -> None:
    repo_name = pr.base.repo.full_name
    logger.info(f"Evaluating PR #{pr.number} in {repo_name}: '{pr.title}'")

    if dry_run:
        print(f"[Dry-run] Would merge PR #{pr.number} in {repo_name} - '{pr.title}'")
        return

    if pr.is_merged():
        logger.info(f"PR #{pr.number} in {repo_name} is already merged.")
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
    try:
        user = github_client.get_user()
        repos = [repo for repo in user.get_repos() if repo.permissions.push]
        return repos
    except RateLimitExceededException as e:
        logger.error(f"GitHub API rate limit exceeded: {e}")
        sys.exit(1)
    except GithubException as e:
        logger.error(f"GitHub API error: {e}")
        sys.exit(1)


def main(args: argparse.Namespace) -> None:
    github_client = get_github_client()
    repos = get_user_repos_with_write_access(github_client)
    print(f"Found {len(repos)} repositories with write access.")

    excluded = set(args.exclude_repos or [])
    for repo in repos:
        if repo.name in excluded:
            print(f"Skipping excluded repository: {repo.full_name}")
            continue

        print(f"Checking repository: {repo.full_name}")
        try:
            pulls = repo.get_pulls(state="open", sort="updated", direction="desc")
        except GithubException as e:
            logger.warning(f"Failed to fetch PRs for {repo.full_name}: {e}")
            continue

        for pr in pulls:
            if is_dependabot_pr(pr):
                merge_pr(pr, merge_method=args.merge_method, dry_run=args.dry_run)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-merge Dependabot PRs on your repositories.")
    parser.add_argument(
        "--merge-method",
        choices=["merge", "squash", "rebase"],
        default="squash",
        help="Merge method to use when merging PRs.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show PRs that would be merged without actually merging.",
    )
    parser.add_argument(
        "--exclude-repos",
        nargs="*",
        default=[],
        help="List of repository names to exclude from processing.",
    )
    args = parser.parse_args()

    main(args)
