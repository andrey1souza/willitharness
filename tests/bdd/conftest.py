import pytest
from pytest_bdd import parsers, then

@then(parsers.parse("the command fails with exit code {code:d}"))
def command_fails_with_code(world, code):
    assert world["exit_code"] == code, f"expected exit code {code}, got {world['exit_code']}; world {world}"


@then(parsers.parse('the message says "{text}"'))
def message_says(world, text):
    assert text in world["message"], f"expected the message to say {text!r}, got {world['message']!r}"


@pytest.fixture
def world():
    return {}
