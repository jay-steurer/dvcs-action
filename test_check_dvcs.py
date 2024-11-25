#!/usr/bin/env python

import unittest
from check_dvcs import does_string_start_with_jira
from check_dvcs import delete_previous_comment_if_needed
from check_dvcs import get_commit_jira_numbers

class TestDeletePreviousComment(unittest.TestCase):

    def test_delete_previous_comment(self):
        self.assertEqual(delete_previous_comment_if_needed("Deleting previous comment ... "))

    def test_fail_delete_previous_comment(self):
        self.assertEqual(delete_previous_comment_if_needed("Failed to delete previous comment"))

class TestStringStartWithJira(unittest.TestCase):

    def test_string_start_with_jira_ticket(self):
        self.assertEqual(does_string_start_with_jira("JIRA-1234 This is a PR"), "JIRA-1234")

    def test_string_with_no_jira_ticket(self):
        self.assertEqual(does_string_start_with_jira("NO-JIRA: Minor changes"), "NO-JIRA")

    def test_empty_string(self):
        """Test with an empty string."""
        self.assertIsNone(does_string_start_with_jira(""), "The PR string came back as None")

class TestCommitJiraNumber(unittest.TestCase):

    def test_commit_jira_numbers(self):
        self.assertEqual(get_commit_jira_numbers("JIRA-1234 this is a commit message"), "JIRA-1234")

    def test_commit_without_jira_numbers(self):
        self.assertEqual(get_commit_jira_numbers("This is a commit message"),"Failed to get commits!")


if __name__ == '__main__':
    unittest.main()
