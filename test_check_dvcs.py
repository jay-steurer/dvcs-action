#!/usr/bin/env python

import pytest
import unittest
from unittest import mock
import requests_mock

from check_dvcs import does_string_start_with_jira, _NO_JIRA_MARKER, get_commit_jira_numbers, CommandException, comment_preamble, get_previous_comments_urls
from requests.exceptions import MissingSchema


class TestDoesStringStartWithJira:

    @pytest.mark.parametrize(
        "input,expected_return",
        [
            ("testing", None),
            (f'{_NO_JIRA_MARKER} other stuff', _NO_JIRA_MARKER),
        ]
    )
    def test_does_string_start_with_jira_function(self, input, expected_return):
        result = does_string_start_with_jira(input)
        assert result == expected_return


class TestGetPreviousCommentsUrls():

    def test_invalid_url(self):
        with pytest.raises(MissingSchema):
            get_previous_comments_urls("www.google.com")

    def test_invalid_status_code(self):
        with pytest.raises(CommandException):
            with requests_mock.Mocker() as m:
                m.register_uri('GET', 'https://example.com', status_code=404)
                get_previous_comments_urls("https://example.com")

    @pytest.mark.parametrize(
        "json,expected_result",
        [
            ([], []),
            (
                [
                    {
                        "body": "This comment does not match",
                        "url": "https://example.com/1",
                    },
                ],
                []
            ),
            (
                [
                    {
                        "body": f"{comment_preamble} This comment should match",
                        "url": "https://example.com/1",
                    },
                ],
                ["https://example.com/1"]
            ),
        ],
    )
    def test_valid_json(self, json, expected_result):
        with requests_mock.Mocker() as m:
            m.register_uri('GET', 'https://example.com', status_code=200, json=json)
            response = get_previous_comments_urls("https://example.com")
            assert response == expected_result



#
#    def test_delete_previous_comment(self):
#        self.assertEqual(delete_previous_comment_if_needed("Deleting previous comment ... "))
#
#    def test_fail_delete_previous_comment(self):
#        self.assertEqual(delete_previous_comment_if_needed("Failed to delete previous comment"))
#
#class TestStringStartWithJira(unittest.TestCase):
#
#    def test_string_start_with_jira_ticket(self):
#        self.assertEqual(does_string_start_with_jira("AAP-1234 This is a PR"), "AAP-1234")
#
#    def test_string_with_no_jira_ticket(self):
#        self.assertEqual(does_string_start_with_jira(f"{_NO_JIRA_MARKER}: Minor changes"), _NO_JIRA_MARKER)
#
#    def test_empty_string(self):
#        """Test with an empty string."""
#        self.assertIsNone(does_string_start_with_jira(""), "The PR string came back as None")
#
#    def test_random_string(self):
#        """Test with an random string."""
#        self.assertIsNone(does_string_start_with_jira("999990 - This is a PR"), "This is some PR title that does not match")
#


class TestGitCommitJiraNumbers():

    def test_invalid_url(self):
        with pytest.raises(MissingSchema):
            get_commit_jira_numbers("www.google.com")

    def test_invalid_status_code(self):
        with pytest.raises(CommandException):
            with requests_mock.Mocker() as m:
                m.register_uri('GET', 'https://example.com', status_code=404)
                get_commit_jira_numbers("https://example.com")

    @pytest.mark.parametrize(
        "json,expected_result",
        [
            ([], []),
            (
                [
                    {
                        "commit": {
                            "message": "This is wrong"
                        }
                    },
                ],
                []
            ),
            (
                [
                    {
                        "commit": {
                            "message": f"{_NO_JIRA_MARKER} This has the no jira marker"
                        }
                    },
                ],
                [_NO_JIRA_MARKER]
            ),
        ]
    )
    def test_json_return(self, json, expected_result):
        with requests_mock.Mocker() as m:
            m.register_uri('GET', 'https://example.com', status_code=200, json=json)
            response = get_commit_jira_numbers("https://example.com")
            assert response == expected_result


#    def test_commit_jira_numbers(self):
#        self.assertEqual(get_commit_jira_numbers("JIRA-1234 this is a commit message"), "JIRA-1234")
#
#    def test_commit_without_jira_numbers(self):
#        self.assertEqual(get_commit_jira_numbers("This is a commit message"),"Failed to get commits!")


#if __name__ == '__main__':
#    unittest.main()
