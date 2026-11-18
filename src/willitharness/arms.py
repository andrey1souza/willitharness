import re

HEADING = re.compile(r"^(#{1,6}) +(.*?) *$")


def section_bounds(lines, name):
    assert name, "section_bounds needs a section name. Fix: pass the heading text without the # marks."
    assert lines, "section_bounds got no lines. Rule: a harness file has text. Fix: pass the file text split into lines."
    starts = []
    for index, line in enumerate(lines):
        matched = HEADING.match(line)
        if matched and matched.group(2) == name:
            starts.append((index, len(matched.group(1))))
    assert len(starts) == 1, f"the heading {name!r} occurs {len(starts)} times. Rule: a LOO arm removes exactly one section. Fix: name one existing heading."
    start, level = starts[0]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        matched = HEADING.match(lines[index])
        if matched and len(matched.group(1)) <= level:
            end = index
            break
    assert start < end, f"the section {name!r} is empty of lines: {start}..{end}"
    return start, end


def remove_section(text, name):
    assert isinstance(text, str), f"remove_section needs text, got {type(text).__name__}. Fix: pass the file contents."
    lines = text.splitlines(keepends=True)
    start, end = section_bounds(lines, name)
    result = "".join(lines[:start] + lines[end:])
    assert len(result) < len(text), f"removing {name!r} left the text as long as before: {len(result)} of {len(text)}"
    remaining = [HEADING.match(line) for line in result.splitlines()]
    assert not any(found and found.group(2) == name for found in remaining), f"the heading {name!r} is still in the result"
    return result
