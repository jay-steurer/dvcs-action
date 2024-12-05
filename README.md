# Usage

This action validates the following in a PR:
1. A commit in the pull request has the JIRA issue key in the commit message. Note, that the commit cannot be a merge commit.
1. The JIRA issue key is at the beginning of the pull request title.
1. The source branch name also includes the JIRA issue key at the beginning of the branch name.

To use this action create a github workflow like:
```yaml
on:
  pull_request_target:
    type: opened, synchronize, reopened, edited
jobs:
  dvcs_pr_checker:
    permissions:
      contents: read
      pull-requests: write
    runs-on: ubuntu-latest
    name: Check the PR for DVCS integration
    steps:
      - id: foo
        uses: ansible/dvcs-action@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
```


# Testing locally

In order to test locally we need to set an environment variable called `PULL_REQUEST`. 
This can be accomplished by doing a curl command (change <repo> and <pull number> to match what you want to test):
```
export PULL_REQUEST=$(curl https://api.github.com/repos/ansible/<repo>/pulls/<pull number>)
```

After that is set you can run the python scrip with the `--dry-run` command to prevent it from trying to update the PR you are testing:
```
./check_dvcs.py --dry-run
```

This will add additional debugging statements as well as not trying to modify the PR.

NOTE: this will use unauthenticated GitHub API requests which are throttled by default. If you hit your limit you will need to wait until your counter resets to test again.
