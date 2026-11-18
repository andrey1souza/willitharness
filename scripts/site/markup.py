import re
from html import unescape
from typing import NamedTuple

SKIPPED_TEXT_ELEMENTS = ("style", "script", "head")
BLOCK_ELEMENTS = ("p", "li", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "caption", "dd", "dt")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
WHITESPACE = re.compile(r"\s+")
TOKEN = re.compile(r"<!--.*?-->|<(/?)([A-Za-z][\w-]*)([^>]*)>|([^<]+)", re.DOTALL)
ATTRIBUTE = re.compile(r"([\w:-]+)(?:\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s\"'>]+)))?")


class Tag(NamedTuple):
    name: str
    attributes: dict
    closing: bool
    line: int


class Parsed(NamedTuple):
    tags: list
    blocks: list


def attributes_of(text):
    assert isinstance(text, str), f"attributes_of needs text, got {type(text).__name__}. Fix: pass the tag attribute text."
    found = {name: unescape(next((value for value in values if value), "")) for name, *values in ATTRIBUTE.findall(text)}
    assert all(isinstance(value, str) for value in found.values()), f"attribute values must be text, got {found!r}"
    return found


def parsed(html):
    assert isinstance(html, str), f"parsed needs html text, got {type(html).__name__}. Fix: pass the page body."
    tags, blocks, open_blocks = [], [], []
    skipping = 0
    for found in TOKEN.finditer(html):
        slash, name, attribute_text, text = found.groups()
        if name:
            name = name.lower()
            line = html.count("\n", 0, found.start()) + 1
            tags.append(Tag(name, {} if slash else attributes_of(attribute_text), bool(slash), line))
            step = -1 if slash else 1
            skipping += step if name in SKIPPED_TEXT_ELEMENTS else 0
            if name in BLOCK_ELEMENTS and not slash:
                open_blocks.append([])
            elif name in BLOCK_ELEMENTS and open_blocks:
                blocks.append(WHITESPACE.sub(" ", "".join(open_blocks.pop())).strip())
        elif text and not skipping and open_blocks:
            open_blocks[-1].append(unescape(text))
    assert skipping == 0, f"unbalanced head, style or script elements, depth {skipping}. Rule: every element closes. Fix: close it."
    return Parsed(tags, blocks)


def tags_of(html):
    assert isinstance(html, str), f"tags_of needs html text, got {type(html).__name__}. Fix: pass the page body."
    tags = parsed(html).tags
    assert all(isinstance(tag, Tag) for tag in tags), f"every parsed item of {html[:40]!r} must be a Tag. Fix: correct parsed."
    return tags


def text_blocks(html):
    assert isinstance(html, str), f"text_blocks needs html text, got {type(html).__name__}. Fix: pass the page body."
    blocks = [block for block in parsed(html).blocks if block]
    assert all(isinstance(block, str) for block in blocks), f"blocks must be text, got {blocks!r}"
    return blocks


def sentences_of(block):
    assert isinstance(block, str), f"sentences_of needs text, got {type(block).__name__}. Fix: pass a text block."
    parts = [part.strip() for part in SENTENCE_END.split(unescape(block)) if part.strip()]
    assert all(parts), f"empty sentence in {block!r}. Fix: strip empty parts."
    return parts
