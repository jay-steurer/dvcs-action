#!/usr/bin/env python

import pytest
import unittest
from unittest import mock
from os import environ
import requests_mock

import check_dvcs
from requests.exceptions import MissingSchema


class TestDoesStringStartWithJira:

    @pytest.mark.parametrize(
        "input,expected_return",
        [
            ("testing", None),
            (f'{check_dvcs._NO_JIRA_MARKER} other stuff', check_dvcs._NO_JIRA_MARKER),
        ]
    )
    def test_does_string_start_with_jira_function(self, input, expected_return):
        result = check_dvcs.does_string_start_with_jira(input)
        assert result == expected_return


class TestGetPreviousCommentsUrls():

    def test_invalid_url(self):
        with pytest.raises(MissingSchema):
            check_dvcs.get_previous_comments_urls("www.google.com")

    def test_invalid_status_code(self):
        with pytest.raises(check_dvcs.CommandException):
            with requests_mock.Mocker() as m:
                m.register_uri('GET', 'https://example.com', status_code=404)
                check_dvcs.get_previous_comments_urls("https://example.com")

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
                        "body": f"{check_dvcs.comment_preamble} This comment should match",
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
            response = check_dvcs.get_previous_comments_urls("https://example.com")
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
            check_dvcs.get_commit_jira_numbers("www.google.com")

    def test_invalid_status_code(self):
        with pytest.raises(check_dvcs.CommandException):
            with requests_mock.Mocker() as m:
                m.register_uri('GET', 'https://example.com', status_code=404)
                check_dvcs.get_commit_jira_numbers("https://example.com")

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
                            "message": f"{check_dvcs._NO_JIRA_MARKER} This has the no jira marker"
                        }
                    },
                ],
                [check_dvcs._NO_JIRA_MARKER]
            ),
        ]
    )
    def test_json_return(self, json, expected_result):
        with requests_mock.Mocker() as m:
            m.register_uri('GET', 'https://example.com', status_code=200, json=json)
            response = check_dvcs.get_commit_jira_numbers("https://example.com")
            assert response == expected_result


#    def test_commit_jira_numbers(self):
#        self.assertEqual(get_commit_jira_numbers("JIRA-1234 this is a commit message"), "JIRA-1234")
#
#    def test_commit_without_jira_numbers(self):
#        self.assertEqual(get_commit_jira_numbers("This is a commit message"),"Failed to get commits!")


class TestMain:

    @pytest.mark.parametrize(
        "json",
        [
            "{'bad': 'json',}",
            "",
        ]
    )
    def test_invalid_pull_input(self, capsys, json):
        environ['PULL_REQUEST'] = json
        with pytest.raises(SystemExit) as e:
            check_dvcs.main()
        output = capsys.readouterr()
        assert "Failed to load json from string" in output.out
        assert e.value.code == 255

    @pytest.mark.parametrize(
        "token",
        [
            None,
            "",
        ]
    )
    def test_github_invalid_token(self, capsys, token):
        environ['PULL_REQUEST'] = "{}"
        if token:
            environ['GH_TOKEN'] = token
        with pytest.raises(SystemExit) as e:
            check_dvcs.main()
        output = capsys.readouterr()
        assert "Did not get a github token, failing" in output.out
        assert e.value.code == 255

    def test_delete_previous_commit_fails(self, capsys):
        environ['PULL_REQUEST'] = "{}"
        environ['GH_TOKEN'] = "asdf1234"
        with mock.patch('check_dvcs.get_previous_comments_urls', side_effect=check_dvcs.CommandException("Failing on purpose")):
            with pytest.raises(SystemExit) as e:
                check_dvcs.main()
            output = capsys.readouterr()
            assert "Failed to delete one or more comments" in output.out
            assert e.value.code == 255

    def test_fail_to_get_commits(self, capsys):
        environ['PULL_REQUEST'] = '{"title": "junk"}'
        environ['GH_TOKEN'] = "asdf1234"
        with mock.patch('check_dvcs.get_previous_comments_urls', return_value=[]):
            with mock.patch('check_dvcs.get_commit_jira_numbers', side_effect=check_dvcs.CommandException("Failing on purpose")):
                with pytest.raises(SystemExit) as e:
                    check_dvcs.main()
                output = capsys.readouterr()
                assert "Failed to get commits" in output.out
                assert e.value.code == 255

    def test_failed_to_add_comment(self, capsys):
        environ['PULL_REQUEST'] = '{"title": "junk", "_links": {"comments": {"href": "https://example.com"}}}'
        environ['GH_TOKEN'] = "asdf1234"
        with mock.patch('check_dvcs.get_previous_comments_urls', return_value=[]):
            with mock.patch('check_dvcs.get_commit_jira_numbers', return_value=[]):
                with mock.patch('check_dvcs.make_decisions', return_value=""):
                    with requests_mock.Mocker() as m:
                        m.register_uri('POST', 'https://example.com', status_code=404)
                        check_dvcs.main()  # We don't raise an exception for this.
                        output = capsys.readouterr()
                        assert "Failed to add new comment" in output.out

    def test_failed_check(self):
        environ['PULL_REQUEST'] = '{"title": "junk", "_links": {"comments": {"href": "https://example.com"}}}'
        environ['GH_TOKEN'] = "asdf1234"
        with mock.patch('check_dvcs.get_previous_comments_urls', return_value=[]):
            with mock.patch('check_dvcs.get_commit_jira_numbers', return_value=[]):
                with requests_mock.Mocker() as m:
                    m.register_uri('POST', 'https://example.com', status_code=201)
                    with pytest.raises(SystemExit) as e:
                        check_dvcs.main()
                    assert e.value.code == 255
