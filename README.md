This action validates the following in a PR:
1. A commit in the pull request has the JIRA issue key in the commit message. Note, that the commit cannot be a merge commit.
1. The JIRA issue key is at the beginning of the pull request title.
1. The source branch name also includes the JIRA issue key at the beginning of the branch name.

To use this action create a github workflow like:
```yaml
on:
  pull_request:
    types: [opened, edited, reopened, synchronize]

jobs:
  dvcs_pr_checker:
    runs-on: ubuntu-latest
    name: Check the PR for DVCS integration
    steps:
      - id: foo
        uses: ansible/dvcs-action@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}

```
