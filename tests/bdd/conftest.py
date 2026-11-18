import re
from pathlib import Path

import pytest
from pytest_bdd import parsers, then

FEATURES = Path(__file__).resolve().parents[2] / "features"
TAG = re.compile(r"(?<!\S)@([A-Za-z0-9-]+)")


def pytest_configure(config):
    tags = set()
    for path in FEATURES.glob("*.feature"):
        tags.update(TAG.findall(path.read_text()))
    assert tags, f"no feature tags found in {FEATURES}. Fix: check the features directory."
    for tag in sorted(tags):
        config.addinivalue_line("markers", f"{tag}: scenario tag from the features directory")


@then(parsers.parse("the command fails with exit code {code:d}"))
def command_fails_with_code(world, code):
    assert world["exit_code"] == code, f"expected exit code {code}, got {world['exit_code']}; world {world}"


@then(parsers.parse('the message says "{text}"'))
def message_says(world, text):
    assert text in world["message"], f"expected the message to say {text!r}, got {world['message']!r}"


@pytest.fixture
def world():
    return {}
