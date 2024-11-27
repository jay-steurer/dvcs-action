from os import environ
from unittest import mock

import pytest
import requests_mock
from requests.exceptions import MissingSchema

import check_dvcs


class TestDoesStringStartWithJira:

    @pytest.mark.parametrize(
        "input,expected_return",
        [
            ("testing", None),
            (f'{check_dvcs._NO_JIRA_MARKER} other stuff', check_dvcs._NO_JIRA_MARKER),
            ('AAP-1234 other stuff', 'AAP-1234'),
        ],
    )
    def test_does_string_start_with_jira_function(self, input, expected_return):
        result = check_dvcs.does_string_start_with_jira(input)
        assert result == expected_return


class TestGetPreviousCommentsUrls:

    def test_invalid_url(self):
        with pytest.raises(MissingSchema):
            check_dvcs.get_previous_comments_urls("www.example.com")

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
                [],
            ),
            (
                [
                    {
                        "body": f"{check_dvcs.comment_preamble} This comment should match",
                        "url": "https://example.com/1",
                    },
                ],
                ["https://example.com/1"],
            ),
        ],
    )
    def test_valid_json(self, json, expected_result):
        with requests_mock.Mocker() as m:
            m.register_uri('GET', 'https://example.com', status_code=200, json=json)
            response = check_dvcs.get_previous_comments_urls("https://example.com")
            assert response == expected_result


class TestDeletePreviousComments:

    def test_good_delete(self):
        base_url = 'https://example.com/'
        with requests_mock.Mocker() as m:
            m.register_uri('DELETE', f'{base_url}1', status_code=404)
            m.register_uri('DELETE', f'{base_url}2', status_code=204)
            check_dvcs.delete_previous_comments([f'{base_url}1', f'{base_url}2'])

    def test_bad_deletes(self):
        base_url = 'https://example.com/'
        with requests_mock.Mocker() as m:
            m.register_uri('DELETE', f'{base_url}1', status_code=500)
            m.register_uri('DELETE', f'{base_url}2', status_code=201)
            m.register_uri('DELETE', f'{base_url}3', status_code=404)
            m.register_uri('DELETE', f'{base_url}4', status_code=204)
            with pytest.raises(check_dvcs.CommandException) as ce:
                check_dvcs.delete_previous_comments(
                    [
                        f'{base_url}1',
                        f'{base_url}2',
                        f'{base_url}3',
                        f'{base_url}4',
                    ]
                )
            assert f'{base_url}1' in str(ce.value)
            assert f'{base_url}2' in str(ce.value)
            assert f'{base_url}3' not in str(ce.value)
            assert f'{base_url}4' not in str(ce.value)


class TestGitCommitJiraNumbers:

    def test_invalid_url(self):
        with pytest.raises(MissingSchema):
            check_dvcs.get_commit_jira_numbers("www.example.com")

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
                    {"commit": {"message": "This is wrong"}},
                ],
                [],
            ),
            (
                [
                    {"commit": {"message": f"{check_dvcs._NO_JIRA_MARKER} This has the no jira marker"}},
                ],
                [check_dvcs._NO_JIRA_MARKER],
            ),
            (
                [
                    {"commit": {"message": "AAP-1234 This has the jira marker"}},
                ],
                ['AAP-1234'],
            ),
            (
                [
                    {"commit": {"message": "ABC-0909 This has wrong jira marker format"}},
                ],
                [],
            ),
        ],
    )
    def test_json_return(self, json, expected_result):
        with requests_mock.Mocker() as m:
            m.register_uri('GET', 'https://example.com', status_code=200, json=json)
            response = check_dvcs.get_commit_jira_numbers("https://example.com")
            assert response == expected_result


class TestMain:

    @pytest.mark.parametrize(
        "json",
        [
            "{'bad': 'json',}",
            "",
        ],
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
        ],
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


class TestMakeDecisions:

## test scenarios (happy path)
## PR has NO_JIRA_MARKER, Commit has NO_JIRA_MARKER, SB has NO_JIRA_MARKER,
## PR has a valid JIRA marker, commit has a valid Jira marker, SB has a valid JIRA marker
### Validate upper case/lower case JIRA markers

    @pytest.mark.parametrize(
        "pr_title_jira,possible_commit_jiras,source_branch_jira",
        [
            (
                f'{check_dvcs._NO_JIRA_MARKER}',
                [f'{check_dvcs._NO_JIRA_MARKER}'],
                f'{check_dvcs._NO_JIRA_MARKER}',
            ),
            (
                'AAP-1234',
                ['AAP-1234', f"{check_dvcs._NO_JIRA_MARKER} no marker", 'AAP-5678 Some other marker but only one has to be valid'],
                'aap-1234',
            ),
            (
                'AAP-1234',
                ['AAP-1234', 'AAP-1234 testing valid marker', f"{check_dvcs._NO_JIRA_MARKER} Testing valid marker"],
                'aap-1234',
            ),
            (
                'AAP-1234',
                ['AAP-1234', 'AAP-1234 testing valid marker', 'AAP-1234 testing valid marker'],
                'aap-1234',
            ),
            (
                'aap-1234',
                ['aap-1234', 'aap-1234 testing valid marker', 'aap-1234 testing valid marker'],
                'aap-1234',
            ),
        ],
    )
    def test_good_result(self, pr_title_jira, possible_commit_jiras, source_branch_jira):
        result = check_dvcs.make_decisions(pr_title_jira, possible_commit_jiras, source_branch_jira)
        assert check_dvcs.bad_icon not in result

# test scenarios (broken path)
## PR title is none
## PR title does not match expected format
## Commit is empty
## Commit has no JIRA marker
## Commit JIRA markers don't match PR and SB JIRA markers
## Source branch is none
## Source branch does not match jira
## Source branch does not match expected format
### Validate AAP-1234 marker format

    @pytest.mark.parametrize(
        "pr_title_jira,possible_commit_jiras,source_branch_jira,expected_in_message",
        [
            (
                None,
                [f'{check_dvcs._NO_JIRA_MARKER}'],
                f'{check_dvcs._NO_JIRA_MARKER}',
                f"* {check_dvcs.bad_icon} Title: PR title does not start with a JIRA number",
            ),
            (
                'Title title', ## it fails on mismatch instead of the PR title, is it the correct behavior?
                [f'{check_dvcs._NO_JIRA_MARKER}', 'Title title'],
                f'{check_dvcs._NO_JIRA_MARKER}',
                f"* {check_dvcs.bad_icon} Mismatch: The JIRAs in the source branch no_jira and title title title do not match!",
            ),
            (
                f"{check_dvcs._NO_JIRA_MARKER}", ## it does not show an error message for no jira commit
                ['This is a commit', 'this is another commit', 'this is another commit'],
                f'{check_dvcs._NO_JIRA_MARKER}',
                f"* {check_dvcs.bad_icon} / not the result ?",
            ),
            (
                f"{check_dvcs._NO_JIRA_MARKER}", #results don't show a mismatch
                ['AAP-1234', 'this is another commit aap-1234'],
                f'{check_dvcs._NO_JIRA_MARKER}',
                f"* {check_dvcs.bad_icon} Mismatch: The JIRAs in the source branch",
            ),
            (
                f"{check_dvcs._NO_JIRA_MARKER}",
                [f'{check_dvcs._NO_JIRA_MARKER}'],
                None,
                f"* {check_dvcs.bad_icon} Source Branch: The source branch of the PR does not start with",
            ),
            (
                'AAP-1234 this is a title',
                ['AAP-1234', 'aap-1234', 'aap-1234 this is a commit with jira numbers'],
                'aap-1234 this is the source branch',
                f"* {check_dvcs.bad_icon} Mismatch: The JIRAs in the source branch",
            ),
            (
                'AAP-1234 this is a title',
                ['AAP-1234', 'aap-1234', 'aap-1234 this is a commit with jira numbers'],
                'aap-1234 this is the source branch',
                f"* {check_dvcs.bad_icon} Mismatch: The JIRAs in the source branch",
            ),
                        (
                'ABC-0900 this is a title',
                ['ABC-0900', 'ABC-0900', 'ABC-0900 this is a commit with jira numbers'],
                'ABC-0900 this is the source branch',
                f"* {check_dvcs.bad_icon} Mismatch: No commit with source branch JIRA number",
            ),
        ],
    )
    def test_bad_result(self, pr_title_jira, possible_commit_jiras, source_branch_jira, expected_in_message):
        result = check_dvcs.make_decisions(pr_title_jira, possible_commit_jiras, source_branch_jira)
        assert expected_in_message in result
        #print("Result from make_decisions:", result)
