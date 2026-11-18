import io
import re
import tokenize
from html import unescape
from pathlib import Path

from markup import sentences_of, tags_of, text_blocks

BYTES_PER_KIB = 1024
PAGE_BUDGET_KIB = 64
TOTAL_BUDGET_KIB = 128
PAGE_BUDGET_BYTES = PAGE_BUDGET_KIB * BYTES_PER_KIB
TOTAL_BUDGET_BYTES = TOTAL_BUDGET_KIB * BYTES_PER_KIB
MAX_TITLE_CHARS = 60
MAX_DESCRIPTION_CHARS = 160
MAX_SENTENCE_WORDS = 20
MIN_SHORT_SENTENCE_PERCENT = 80
PERCENT = 100
EXAMPLE_COUNT = 3
HYPE_PHRASES = (
    "revolutionary", "game-changing", "game changing", "cutting-edge", "cutting edge", "world-class", "world class",
    "seamless", "seamlessly", "effortless", "effortlessly", "best-in-class", "best in class", "supercharge",
    "supercharged", "unleash", "unleashed", "10x", "blazing fast", "next-generation", "state-of-the-art",
)
HOLD_BACK_PHRASES = ("proven", "reproduced", "released", "nobody", "works on Linux")
REQUIRED_META = (("name", "description"), ("name", "viewport"), ("property", "og:title"), ("property", "og:description"), ("name", "twitter:card"))
HYPE_PATTERN = re.compile(r"(?<![\w-])(?:" + "|".join(re.escape(phrase) for phrase in HYPE_PHRASES) + r")(?![\w-])", re.IGNORECASE)
DIGIT_RUN = re.compile(r"\d+")
PLACEHOLDER = re.compile(r"\$\$|\$\{?\w+\}?")
TAG = re.compile(r"<[^>]*>")
STYLE_COMMENT = re.compile(r"/\*")
MARKUP_COMMENT = re.compile(r"<!--")
CHARSET = "charset"


def visible_text(html):
    assert isinstance(html, str), f"visible_text needs html text, got {type(html).__name__}. Fix: pass the page body."
    text = " ".join(text_blocks(html))
    assert isinstance(text, str), f"visible text of {html[:40]!r} must be a string, got {type(text).__name__}. Fix: join the blocks."
    return text


def hype_problems(page, html):
    assert page.endswith(".html"), f"a page name ends in .html, got {page!r}. Fix: pass the page file name."
    found = sorted({match.group(0).lower() for match in HYPE_PATTERN.finditer(visible_text(html))})
    assert all(phrase in HYPE_PHRASES or phrase.replace(" ", "-") in HYPE_PHRASES for phrase in found), f"hype matches {found} are not all in HYPE_PHRASES. Fix: align the pattern and the list."
    return [f"{page} uses the hype word {phrase!r}. Rule: the site states facts, not praise. Fix: delete the word." for phrase in found]


def hold_back_problems(page, html, claims):
    assert isinstance(claims, dict), f"claims must map phrases to booleans, got {type(claims).__name__}. Fix: read the claims from the result file."
    assert all(isinstance(value, bool) for value in claims.values()), f"every claim must be true or false, got {claims!r}"
    text = visible_text(html)
    return [
        f"{page} says {phrase!r} but the data file does not mark it true. Rule: a claim not proven stays off the page. Fix: delete the phrase or record the proof in the data file."
        for phrase in HOLD_BACK_PHRASES
        if re.search(rf"(?<![\w-]){re.escape(phrase)}(?![\w-])", text, re.IGNORECASE) and claims.get(phrase) is not True
    ]


def missing_meta(page, tags, attribute, value):
    assert attribute and value, f"a meta requirement names an attribute and a value, got {attribute!r} and {value!r}. Fix: correct REQUIRED_META."
    assert page.endswith(".html"), f"a page name ends in .html, got {page!r}. Fix: pass the page file name."
    found = [tag for tag in tags if tag.name == "meta" and tag.attributes.get(attribute) == value]
    if found and (found[0].attributes.get("content") or "").strip():
        return ""
    return f"{page} lacks <meta {attribute}=\"{value}\" content=...>. Rule: every page declares its meta tags. Fix: add the tag with content."


def missing_charset(page, tags):
    assert page.endswith(".html"), f"a page name ends in .html, got {page!r}. Fix: pass the page file name."
    assert isinstance(tags, list), f"tags must be a list, got {type(tags).__name__}. Fix: pass parsed tags."
    if any(tag.name == "meta" and CHARSET in tag.attributes for tag in tags):
        return []
    return [f"{page} lacks <meta charset>. Rule: every page declares its encoding. Fix: add it."]


def meta_problems(page, html):
    assert page.endswith(".html"), f"a page name ends in .html, got {page!r}. Fix: pass the page file name."
    tags = [tag for tag in tags_of(html) if not tag.closing]
    problems = [problem for attribute, value in REQUIRED_META if (problem := missing_meta(page, tags, attribute, value))]
    problems += missing_charset(page, tags)
    titles = re.findall(r"<title>([^<]*)</title>", html)
    if len(titles) != 1 or not titles[0].strip() or len(titles[0]) > MAX_TITLE_CHARS:
        problems.append(f"{page} needs one title of 1 to {MAX_TITLE_CHARS} characters, got {titles}. Rule: titles stay short. Fix: edit the title.")
    description = next((tag.attributes.get("content", "") for tag in tags if tag.attributes.get("name") == "description"), "")
    if len(description) > MAX_DESCRIPTION_CHARS:
        problems.append(f"{page} has a description of {len(description)} characters, over {MAX_DESCRIPTION_CHARS}. Rule: descriptions stay short. Fix: shorten it.")
    if not any(tag.name == "html" and tag.attributes.get("lang") for tag in tags):
        problems.append(f"{page} lacks a lang attribute on <html>. Rule: every page names its language. Fix: add lang.")
    assert all(isinstance(problem, str) for problem in problems), f"problems must be text, got {problems!r}"
    return problems



def budget_problems(sizes):
    assert isinstance(sizes, dict), f"sizes must map file names to byte counts, got {type(sizes).__name__}. Fix: pass the built sizes."
    assert sizes, "the site has no files to weigh. Fix: build the site first."
    problems = [
        f"{name} weighs {size} bytes, over the page budget of {PAGE_BUDGET_BYTES}. Rule: pages stay light. Fix: cut content."
        for name, size in sizes.items()
        if size > PAGE_BUDGET_BYTES
    ]
    total = sum(sizes.values())
    if total > TOTAL_BUDGET_BYTES:
        problems.append(f"the site weighs {total} bytes, over the total budget of {TOTAL_BUDGET_BYTES}. Rule: the whole site stays light. Fix: cut content.")
    return problems


def style_problems(files):
    assert isinstance(files, dict), f"files must map page names to html, got {type(files).__name__}. Fix: pass the built pages."
    assert all(isinstance(html, str) for html in files.values()), f"every page must be html text, got {files!r}. Fix: pass the built pages."
    problems = []
    for page, html in files.items():
        sentences = [sentence for block in text_blocks(html) for sentence in sentences_of(block)]
        long = [sentence for sentence in sentences if len(sentence.split()) > MAX_SENTENCE_WORDS]
        share = PERCENT * (len(sentences) - len(long)) // max(len(sentences), 1)
        if share < MIN_SHORT_SENTENCE_PERCENT:
            examples = "; ".join(sentence[:60] for sentence in long[:EXAMPLE_COUNT])
            problems.append(f"{page} has {share} percent of sentences within {MAX_SENTENCE_WORDS} words, under {MIN_SHORT_SENTENCE_PERCENT}. Rule: ASD-STE100 shape. Fix: shorten, for example: {examples}.")
    return problems


def typed_number_problems(name, template):
    assert isinstance(template, str), f"typed_number_problems needs template text, got {type(template).__name__}. Fix: pass the file body."
    assert name, "a template needs a file name. Fix: pass its path."
    problems = []
    for number, line in enumerate(template.splitlines(), start=1):
        prose = unescape(PLACEHOLDER.sub("", TAG.sub("", line)))
        for digits in DIGIT_RUN.findall(prose):
            problems.append(f"{name}:{number} types the number {digits} by hand. Rule: every number comes from a data file. Fix: use a placeholder.")
    return problems


def rendered_number_problems(page, html, corpus):
    assert isinstance(corpus, str), f"corpus must be the data as text, got {type(corpus).__name__}. Fix: pass json.dumps of the data."
    assert page.endswith(".html"), f"a page name ends in .html, got {page!r}. Fix: pass the page file name."
    allowed = set(DIGIT_RUN.findall(corpus))
    shown = DIGIT_RUN.findall(visible_text(html))
    return [f"{page} shows the number {digits}, which no data file holds. Rule: digits come only from data. Fix: derive it from a data file." for digits in sorted(set(shown) - allowed)]


def comment_problems(sources):
    assert isinstance(sources, dict), f"sources must map file names to text, got {type(sources).__name__}. Fix: pass the files."
    assert all(isinstance(text, str) for text in sources.values()), f"every source must be text, got {sources!r}. Fix: pass the file bodies."
    problems = []
    for name, text in sources.items():
        if name.endswith(".py"):
            comments = [token for token in tokenize.generate_tokens(io.StringIO(text).readline) if token.type == tokenize.COMMENT]
            problems += [f"{name}:{token.start[0]} holds a comment. Rule: names carry intent, so code has no comments. Fix: delete it or rename." for token in comments]
        elif STYLE_COMMENT.search(text) or MARKUP_COMMENT.search(text):
            problems.append(f"{name} holds a comment. Rule: names carry intent, so code has no comments. Fix: delete it.")
    return problems


def stray_markdown_problems(root, folders):
    assert isinstance(root, Path), f"stray_markdown_problems needs a Path root, got {root!r}. Fix: pass the repository root."
    assert folders, "name at least one folder to scan. Fix: pass the site folders."
    found = [path for folder in folders if (root / folder).is_dir() for path in sorted((root / folder).rglob("*.md"))]
    return [f"{path.relative_to(root)} is a markdown file in a site folder. Rule: the site adds no md files. Fix: delete it." for path in found]
