from github import Github
import os

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise Exception("Please set your GITHUB_TOKEN environment variable.")

g = Github(GITHUB_TOKEN)

def is_dependabot_pr(pr):
    return pr.user.login == "dependabot[bot]"

def merge_dependabot_pr(pr):
    try:
        if pr.mergeable_state == 'clean' or pr.mergeable_state == 'unstable' or pr.mergeable_state == 'has_hooks':
            print(f"Merging PR #{pr.number} in {pr.base.repo.full_name} - {pr.title}")
            pr.merge(merge_method="squash", commit_message="Auto-merged by script - Dependabot PR")
            print(f"PR #{pr.number} merged.")
        else:
            print(f"PR #{pr.number} in {pr.base.repo.full_name} not mergeable (state: {pr.mergeable_state})")
    except Exception as e:
        print(f"Failed to merge PR #{pr.number} in {pr.base.repo.full_name}: {e}")

def main():
    repos = g.get_user().get_repos()
    
    for repo in repos:
        perm = repo.permissions
        if not perm.push:
            continue

        print(f"Checking repo: {repo.full_name}")
        pulls = repo.get_pulls(state='open', sort='updated', direction='desc')
        
        for pr in pulls:
            if is_dependabot_pr(pr):
                print(f"Found dependabot PR #{pr.number} in {repo.full_name}: {pr.title}")
                merge_dependabot_pr(pr)

if __name__ == "__main__":
    main()
