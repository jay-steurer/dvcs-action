#!/usr/bin/env python

import json
import re
from os import getenv
from sys import exit
from typing import Optional

import requests

_NO_JIRA_MARKER = "NO_JIRA"
_AAP_RE = "aap-[0-9]+"
comment_preamble = "DVCS PR Check Results:"
good_icon = "✅"
bad_icon = "❌"
http_headers = {}


class CommandException(Exception):
    pass


def get_previous_comments_urls(comments_url) -> list[str]:
    # Load the existing comments
    print("Getting comments ... ", end="")
    comments = requests.get(comments_url)
    print(comments.status_code)
    if comments.status_code != 200:
        raise CommandException("Failed to get existing comments!")

    response = []
    for comment in comments.json():
        if comment["body"].startswith(comment_preamble):
            response.append(comment["url"])

    return response


def delete_previous_comments(comments_urls: list[str]) -> None:
    comments_that_failed_to_delete = []
    for url in comments_urls:
        print("Deleting old comment ... ", end="")
        response = requests.delete(url, headers=http_headers)
        print(response.status_code)
        if response.status_code not in [204, 404]:
            comments_that_failed_to_delete.append(url)

    if len(comments_that_failed_to_delete) > 0:
        raise CommandException('\n'.join(comments_that_failed_to_delete))


def does_string_start_with_jira(string_to_match: str) -> Optional[str]:
    pr_title_re = re.compile(f"^({_AAP_RE}|{_NO_JIRA_MARKER})", re.IGNORECASE)
    matches = pr_title_re.match(string_to_match)
    if not matches:
        print(f"String {string_to_match} failed check")
        return None
    return matches.groups()[0]


def get_commit_jira_numbers(commit_url: str) -> list[str]:
    print("Getting commits ... ", end="")
    commits = requests.get(commit_url)
    print(commits.status_code)
    if commits.status_code != 200:
        raise CommandException("Failed to get commits!")
    comment_re = re.compile(f"({_AAP_RE}|{_NO_JIRA_MARKER})", re.IGNORECASE)
    possible_jiras = []
    for commit in commits.json():
        # TODO: How to check if this is a merge commit or a regular comment?
        matches = comment_re.match(commit["commit"]["message"])
        if matches:
            possible_jiras.append(matches.groups()[0])

    return possible_jiras


def make_decisions(
    pr_title_jira: Optional[str],
    possible_commit_jiras: list[str],
    source_branch_jira: Optional[str],
) -> str:
    # Lower case everything for comparison
    if pr_title_jira is not None:
        pr_title_jira = pr_title_jira.lower()
    if source_branch_jira is not None:
        source_branch_jira = source_branch_jira.lower()
    for index in range(0, len(possible_commit_jiras)):
        if possible_commit_jiras[index] is not None:
            possible_commit_jiras[index] = possible_commit_jiras[index].lower()

    decisions = [comment_preamble]
    # Now make th decisions if this is in good order....
    if not pr_title_jira:
        # If there is no PR title JIRA report bad
        decisions.append(f"* {bad_icon} Title: PR title does not start with a JIRA number (AAP-[0-9]+) or {_NO_JIRA_MARKER}")
    else:
        # Report the title is good
        decisions.append(f"* {good_icon} Title: JIRA number {pr_title_jira}")

    if not source_branch_jira:
        # If there is no Source Branch JIRA report bad
        decisions.append(f"* {bad_icon} Source Branch: The source branch of the PR does not start with a JIRA number (AAP-[0-9]+) or {_NO_JIRA_MARKER}")
    else:
        # Report the source branch is good
        decisions.append(f"* {good_icon} Source Branch: JIRA number {source_branch_jira}")

    if pr_title_jira is not None and source_branch_jira is not None and pr_title_jira != source_branch_jira:
        # If we have source and title JIRAS and there is a mismatch between the title and source branch JIRAs report the mismatch
        decisions.append(f"* {bad_icon} Mismatch: The JIRAs in the source branch {source_branch_jira} and title {pr_title_jira} do not match!")

    if len(possible_commit_jiras) == 0:
        # If we got no commit JIRAS the commits are bad
        decisions.append(f"* {bad_icon} Commits: No commits with a JIRA number (AAP-[0-9]+) or {_NO_JIRA_MARKER} found!")
    elif source_branch_jira == pr_title_jira:
        if source_branch_jira is None:
            # If the source branch JIRA and the title JIRA are missing and we have commit JIRAS report the commits as good
            decisions.append(f"* {good_icon} Commits: At least one JIRA number in commit messages {', '.join(possible_commit_jiras)}")
        else:
            # If the source branch JIRA matches the title JIRA and we have that JIRA in the commits, the commits are good
            if source_branch_jira in possible_commit_jiras:
                decisions.append(f"* {good_icon} Commits: At least one JIRA number in commit messages match the other JIRA numbers")
    else:
        # If we made it here, we have commit JIRAS but we have a mismatch between the source branch and title
        if source_branch_jira is not None and source_branch_jira not in possible_commit_jiras:
            decisions.append(f"* {bad_icon} Mismatch: No commit with source branch JIRA number")
        if pr_title_jira is not None and pr_title_jira not in possible_commit_jiras:
            decisions.append(f"* {bad_icon} Mismatch: No commit with PR title JIRA number")

    # Construct the new comment
    return "\n".join(decisions)


def main():
    # Get and validate the data from the environment (the GitHub action should pass this in)
    try:
        pull_request = json.loads(getenv("PULL_REQUEST", {}))
    except json.JSONDecodeError as jde:
        print(f"Failed to load json from string: {jde}")
        exit(255)

    GITHUB_TOKEN = getenv("GH_TOKEN")
    if not GITHUB_TOKEN:
        print("Did not get a github token, failing!")
        exit(255)

    pull_urls = pull_request.get("_links", {})
    comments_url = pull_request.get("_links", {}).get("comments", {}).get("href")

    http_headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        delete_previous_comments(get_previous_comments_urls(comments_url))
    except CommandException as ce:
        print("Failed to delete one or more comments:")
        print(ce)
        exit(255)

    # Check the PR title
    pr_title_jira = does_string_start_with_jira(pull_request.get("title"))

    # Check the PR commits
    try:
        possible_commit_jiras = get_commit_jira_numbers(pull_urls.get("commits", {}).get("href"))
    except CommandException as ce:
        print(f"Failed to get commits: {ce}")
        exit(255)

    # Check the PR source branch
    source_branch_jira = does_string_start_with_jira(pull_request.get("head", {}).get("ref", ""))

    new_comment_body = make_decisions(pr_title_jira, possible_commit_jiras, source_branch_jira)

    print("Results:")
    print(new_comment_body)

    # Post the new comment
    print("Creating new comment ... ", end="")
    response = requests.post(comments_url, json={"body": new_comment_body}, headers=http_headers)
    print(response.status_code)
    if response.status_code != 201:
        print("Failed to add new comment")

    # If we had any errors, print them and exit
    if bad_icon in new_comment_body:
        exit(255)


if __name__ == '__main__':
    main()
