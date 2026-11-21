import ast
import json
import posixpath
import re
import subprocess
import sys
from html import unescape
from pathlib import Path

import brand_gates
import contrast
import extract
import render
from markup import tags_of
from willitharness.paths import PathOutsideRoot, inside

HEADING = re.compile(r"^h([1-6])$")
FIRST_LEVEL = 1
MAX_LEVEL_STEP = 1
EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//)", re.IGNORECASE)
TBODY = re.compile(r"<tbody>(.*?)</tbody>", re.DOTALL)
SOURCE_ELEMENT = re.compile(r"<(tr|li)\b([^>]*)>(.*?)</\1>", re.DOTALL)
SOURCE_ATTRIBUTE = re.compile(r'data-source="([^"]+):(\d+)"')
FIRST_CELL = re.compile(r"<td\b[^>]*>(.*?)</td>", re.DOTALL)
TAG = re.compile(r"<[^>]+>")
KEY_CHARS = 20
BACKTICK = "`"
SOURCE_FOLDERS = ("site", "scripts/site", "build/site")
MUTANT_DIRECTORY = "scripts/gates/mutant_modules"
COLLECT_COMMAND = ("-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", "-o", "addopts=", "-m", "not live")
COLLECTED = re.compile(r"^(\d+)(?:/\d+)? tests? collected", re.MULTILINE)
TRACE_COVERED = re.compile(r"all (\d+) IDs covered")
REPO_PASSED = re.compile(r"(\d+) checks passed")
MUTANT_RESULT = re.compile(r"(\d+) of (\d+) mutants killed")
FIRST_NUMBER = re.compile(r"\d+")
CELL = re.compile(r"<td\b[^>]*>(.*?)</td>", re.DOTALL)
GATE_COLUMN_COUNT = 3
STATUS_COMMAND = "scripts/site/build.py"
COUNTED = "counted"
PASSED = "passed"
TESTS_LABEL = "Tests"
MUTANTS_LABEL = "Mutants"
TRACE_LABEL = "Contract IDs covered"
REPO_LABEL = "Repository checks"
GATE_LABELS = (TESTS_LABEL, MUTANTS_LABEL, TRACE_LABEL, REPO_LABEL)
GATE_SCRIPTS = {TRACE_LABEL: ("scripts/gates/trace_check.py", TRACE_COVERED), REPO_LABEL: ("scripts/gates/repo_checks.py", REPO_PASSED)}


def element_text(markup):
    assert isinstance(markup, str), f"element_text needs markup text, got {type(markup).__name__}. Fix: pass the element body."
    text = unescape(TAG.sub("", markup)).strip()
    assert "<" not in text, f"markup left a tag in {text!r}. Fix: correct TAG."
    return text


def tag_problems(page, tag, seen):
    assert page.endswith(".html"), f"a page name ends in .html, got {page!r}. Fix: pass the page file name."
    assert isinstance(seen, set), f"seen ids must be a set, got {type(seen).__name__}. Fix: pass set()."
    problems = []
    identifier = tag.attributes.get("id")
    if identifier is not None:
        if identifier in seen:
            problems.append(f"{page}:{tag.line} repeats the id {identifier!r}. Rule: an id is unique. Fix: rename one.")
        seen.add(identifier)
    if tag.name == "img" and "alt" not in tag.attributes:
        problems.append(f"{page}:{tag.line} has an img without alt. Rule: every image has alt text. Fix: add alt.")
    reference = tag.attributes.get("src") or (tag.attributes.get("href") if tag.name != "a" else None)
    if reference and EXTERNAL.match(reference):
        problems.append(f"{page}:{tag.line} loads {reference} from outside. Rule: the site loads nothing external. Fix: inline or remove it.")
    assert all(problem.startswith(page) for problem in problems), f"every problem names the page, got {problems}"
    return problems


def heading_problems(page, tags):
    assert page.endswith(".html"), f"a page name ends in .html, got {page!r}. Fix: pass the page file name."
    levels = [(int(HEADING.match(tag.name).group(1)), tag.line) for tag in tags if HEADING.match(tag.name)]
    problems = []
    top = [level for level, _ in levels if level == FIRST_LEVEL]
    if len(top) != FIRST_LEVEL:
        problems.append(f"{page} has {len(top)} h1 headings. Rule: one h1 per page. Fix: keep one.")
    previous = 0
    for level, line in levels:
        if level > previous + MAX_LEVEL_STEP:
            problems.append(f"{page}:{line} jumps from h{previous} to h{level}. Rule: heading levels do not skip. Fix: add the missing level.")
        previous = level
    assert all(problem.startswith(page) for problem in problems), f"every problem names the page, got {problems}"
    return problems


def structure_problems(page, html):
    assert page.endswith(".html"), f"a page name ends in .html, got {page!r}. Fix: pass the page file name."
    tags = [tag for tag in tags_of(html) if not tag.closing]
    seen = set()
    problems = [problem for tag in tags for problem in tag_problems(page, tag, seen)]
    problems += [f"{page}:{tag.line} has a table without a caption. Rule: every table is named. Fix: add a caption." for tag in tags if tag.name == "table" and "<caption>" not in html]
    problems += heading_problems(page, tags)
    assert all(isinstance(problem, str) for problem in problems), f"problems must be text, got {problems!r}"
    return problems


def reference_problem(page, tag, files, identifiers):
    assert page in files, f"{page} is not among the built files {sorted(files)}. Fix: pass the built files."
    assert isinstance(identifiers, dict), f"identifiers must map pages to id sets, got {type(identifiers).__name__}. Fix: build the map."
    reference = tag.attributes.get("href") or tag.attributes.get("src")
    if not reference or EXTERNAL.match(reference):
        return ""
    path, _, anchor = reference.partition("#")
    target = page if not path else posixpath.normpath(posixpath.join(posixpath.dirname(page), path))
    if target not in files:
        return f"{page}:{tag.line} points at {reference}, but the site holds no {target}. Rule: every link and asset resolves. Fix: add the file or correct the path."
    if anchor and anchor not in identifiers.get(target, set()):
        return f"{page}:{tag.line} points at {reference}, but {target} has no id {anchor!r}. Rule: anchors resolve. Fix: add the id."
    return ""


def link_problems(files):
    assert isinstance(files, dict), f"files must map names to text, got {type(files).__name__}. Fix: pass the built files."
    assert files, "the site has no files. Fix: build it first."
    identifiers = {name: {tag.attributes["id"] for tag in tags_of(text) if "id" in tag.attributes} for name, text in files.items() if name.endswith(".html")}
    found = [reference_problem(page, tag, files, identifiers) for page in identifiers for tag in tags_of(files[page]) if not tag.closing]
    problems = [problem for problem in found if problem]
    assert all(isinstance(problem, str) for problem in problems), f"problems must be text, got {problems!r}"
    return problems


def expected_texts(data):
    assert set(data) == {"readme", "contract", "gates", "live"}, f"site data needs four parts, got {sorted(data)}. Fix: pass site_data output."
    contract, gates, live = data["contract"], data["gates"], data["live"]
    texts = [item["id"] for item in contract["questions"]] + [item["when"] for item in contract["decisions"]]
    texts += [item["label"] for item in gates["rows"]] + [item["result"] for item in gates["rows"]]
    texts += [item["task"] for item in live["rows"]] + [item["text"] for item in live["limits"] + live["explanation"] + data["readme"]["limits"]] + [item["results"] for item in live["history"]]
    assert texts and all(isinstance(text, str) for text in texts), f"expected texts must be non-empty strings, got {texts!r}"
    return texts


def coverage_problems(page, html, data):
    assert page.endswith(".html"), f"a page name ends in .html, got {page!r}. Fix: pass the page file name."
    shown = brand_gates.visible_text(html)
    assert shown, f"{page} shows no text. Rule: a page has content. Fix: render it."
    return [
        f"{page} does not show {text[:KEY_CHARS * 2]!r}. Rule: every row of the data appears on the page. Fix: render it."
        for text in expected_texts(data)
        if text.replace(BACKTICK, "") not in shown
    ]


def source_problem(root, element, attributes, body):
    assert element in ("tr", "li"), f"only rows and list items cite sources, got {element!r}. Fix: correct SOURCE_ELEMENT."
    cited = SOURCE_ATTRIBUTE.search(attributes)
    assert isinstance(root, Path) and body is not None, f"source_problem needs a Path root and a body, got {root!r} and {body!r}. Fix: pass the parsed element."
    if not cited:
        return f"a <{element}> has no data-source. Rule: every row traces to a source file and line. Fix: render the attribute."
    file, line = cited.group(1), int(cited.group(2))
    try:
        lines = inside(root, file).read_text().splitlines()
    except (PathOutsideRoot, FileNotFoundError):
        return f"a <{element}> cites {file}, which is not a file in the repository. Rule: sources exist. Fix: correct the source."
    if not 1 <= line <= len(lines):
        return f"a <{element}> cites {file}:{line}, but the file has {len(lines)} lines. Rule: the line exists. Fix: correct the source."
    first = FIRST_CELL.search(body)
    key = element_text(first.group(1) if element == "tr" and first else body)[:KEY_CHARS].replace(BACKTICK, "")
    if key not in lines[line - 1].replace(BACKTICK, ""):
        return f"a <{element}> starting {key!r} cites {file}:{line}, which does not hold that text. Rule: a row's source line holds the row. Fix: regenerate the page."
    return ""


def trace_problems(root, page, html):
    assert page.endswith(".html"), f"a page name ends in .html, got {page!r}. Fix: pass the page file name."
    assert isinstance(root, Path), f"trace_problems needs a Path root, got {root!r}. Fix: pass the repository root."
    elements = [(tag, attributes, body) for body_html in TBODY.findall(html) for tag, attributes, body in SOURCE_ELEMENT.findall(body_html) if tag == "tr"]
    elements += [found for found in SOURCE_ELEMENT.findall(html) if found[0] == "li"]
    assert elements, f"{page} has no traceable rows. Rule: the page shows data rows. Fix: render them."
    return [f"{page}: {problem}" for problem in (source_problem(root, *element) for element in elements) if problem]


def mutant_total(root):
    assert isinstance(root, Path), f"mutant_total needs a Path root, got {root!r}. Fix: pass the repository root."
    total = 0
    for path in sorted(inside(root, MUTANT_DIRECTORY).glob("*.py")):
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "MUTANTS" for target in node.targets):
                total += len(node.value.elts)
    assert total > 0, f"{MUTANT_DIRECTORY} lists no mutants. Rule: every gate module has mutants. Fix: add them."
    return total


def script_count(root, label):
    assert label in GATE_SCRIPTS, f"no gate script is known for {label!r}. Fix: use one of {sorted(GATE_SCRIPTS)}."
    script, pattern = GATE_SCRIPTS[label]
    run = subprocess.run([sys.executable, str(inside(root, script))], cwd=root, capture_output=True, text=True)
    found = pattern.search(run.stdout)
    assert found, f"{script} printed no line matching {pattern.pattern!r}: {run.stdout!r} {run.stderr!r}. Rule: the status is recomputed from real output. Fix: repair the gate."
    return int(found.group(1))


def collected_tests(root):
    assert isinstance(root, Path), f"collected_tests needs a Path root, got {root!r}. Fix: pass the repository root."
    run = subprocess.run([sys.executable, *COLLECT_COMMAND], cwd=root, capture_output=True, text=True)
    found = COLLECTED.search(run.stdout)
    assert found, f"pytest collected nothing countable: {run.stdout[-200:]!r}. Fix: repair the test collection."
    return int(found.group(1))


def recomputed_counts(root):
    assert isinstance(root, Path), f"recomputed_counts needs a Path root, got {root!r}. Fix: pass the repository root."
    counts = {
        TESTS_LABEL: collected_tests(root),
        MUTANTS_LABEL: mutant_total(root),
        TRACE_LABEL: script_count(root, TRACE_LABEL),
        REPO_LABEL: script_count(root, REPO_LABEL),
    }
    assert all(count > 0 for count in counts.values()), f"every recomputed count must be positive, got {counts}"
    return counts


def status_document(counts):
    assert set(counts) == set(GATE_LABELS), f"counts {sorted(counts)} differ from the gates {sorted(GATE_LABELS)}. Rule: every gate is counted. Fix: pass recomputed_counts output."
    assert all(count > 0 for count in counts.values()), f"counts must be positive, got {counts}"
    rows = [
        {"label": TESTS_LABEL, "status": COUNTED, "result": f"{counts[TESTS_LABEL]} collected"},
        {"label": MUTANTS_LABEL, "status": COUNTED, "result": f"{counts[MUTANTS_LABEL]} listed"},
        {"label": TRACE_LABEL, "status": PASSED, "result": f"{counts[TRACE_LABEL]} covered"},
        {"label": REPO_LABEL, "status": PASSED, "result": f"{counts[REPO_LABEL]} checks passed"},
    ]
    assert [row["label"] for row in rows] == list(GATE_LABELS), f"rows must follow GATE_LABELS, got {rows}"
    return {"command": STATUS_COMMAND, "gates": rows}


def rendered_count_problems(html, counts):
    assert isinstance(html, str), f"rendered_count_problems needs page text, got {type(html).__name__}. Fix: pass the rendered page."
    assert set(counts) == set(GATE_LABELS), f"counts {sorted(counts)} differ from the gates {sorted(GATE_LABELS)}. Fix: pass recomputed_counts output."
    shown = {label: [] for label in counts}
    for _, attributes, body in (found for found in SOURCE_ELEMENT.findall(html) if found[0] == "tr"):
        cells = [element_text(cell) for cell in CELL.findall(body)]
        if extract.GATE_STATUS_FILE in attributes and len(cells) == GATE_COLUMN_COUNT and cells[0] in shown:
            shown[cells[0]].append(cells[-1])
    problems = []
    for label, results in shown.items():
        rows = len(results)
        numbers = FIRST_NUMBER.findall(results[0]) if rows == 1 else []
        if rows != 1:
            problems.append(f"{label}: the page shows {rows} rows for this gate. Rule: one row per gate. Fix: render the gate table from the generated record.")
        elif not numbers or int(numbers[0]) != counts[label]:
            problems.append(f"{label}: the page shows {results[0]!r} but this build counted {counts[label]}. Rule: the page text equals the counts of the same run. Fix: render the count unchanged.")
    assert all(isinstance(problem, str) for problem in problems), f"problems must be text, got {problems!r}"
    return problems


def source_texts(root):
    assert isinstance(root, Path), f"source_texts needs a Path root, got {root!r}. Fix: pass the repository root."
    files = sorted(inside(root, "scripts/site").glob("*.py")) + [inside(root, render.STYLE_FILE), inside(root, render.TEMPLATE_FILE)]
    texts = {str(path.relative_to(root.resolve())): path.read_text() for path in files}
    assert texts, "no site source files found. Fix: restore scripts/site and site/src."
    return texts


def site_problems(root, files, data, counts):
    assert isinstance(root, Path), f"site_problems needs a Path root, got {root!r}. Fix: pass the repository root."
    assert render.PAGE_NAME in files, f"the built files lack {render.PAGE_NAME}, got {sorted(files)}. Fix: build the site first."
    corpus = json.dumps(data)
    claims = data["live"]["claims"]
    sources = source_texts(root)
    problems = link_problems(files) + brand_gates.budget_problems({name: len(text.encode()) for name, text in files.items()})
    problems += contrast.contrast_problems(files[render.STYLE_NAME]) + brand_gates.style_problems({render.PAGE_NAME: files[render.PAGE_NAME]})
    for page in (name for name in files if name.endswith(".html")):
        html = files[page]
        problems += structure_problems(page, html) + coverage_problems(page, html, data) + trace_problems(root, page, html)
        problems += brand_gates.hype_problems(page, html) + brand_gates.hold_back_problems(page, html, claims)
        problems += brand_gates.meta_problems(page, html) + brand_gates.rendered_number_problems(page, html, corpus)
    problems += brand_gates.typed_number_problems(render.TEMPLATE_FILE, sources[render.TEMPLATE_FILE])
    problems += brand_gates.comment_problems({**sources, **files}) + brand_gates.stray_markdown_problems(root, SOURCE_FOLDERS)
    problems += rendered_count_problems(files[render.PAGE_NAME], counts)
    return problems
