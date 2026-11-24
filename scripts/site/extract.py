import json
import re
import tomllib
from pathlib import Path

from willitharness.paths import inside

README_FILE = "README.md"
LICENSE_FILE = "LICENSE"
PROJECT_FILE = "pyproject.toml"
CONTRACT_FILE = "docs/contract.md"
GATE_STATUS_FILE = "build/gate_status.json"
LIVE_RESULT_FILE = "fixtures/results/g4_4.json"
LIMITS_HEADING = "## Honest limits"
COMMANDS_HEADING = "## What works today"
OFFLINE_HEADING = "## Try it offline"
INSTALL_HEADING = "## Install"
ISOLATION_HEADING = "## Limits of isolation"
QUESTIONS_HEADING = "## 3. The four questions"
DECISIONS_HEADING = "## 6. Decision table (exact)"
SECTION_PREFIX = "## "
BULLET_PREFIX = "- "
CONTINUATION_PREFIX = "  "
QUESTION_BULLET = re.compile(r"^(Q\d+) ([\w ]+): (.+?\?)(.*)$")
RESULT_TEXT = re.compile(r"Result: ([^.]*)\.")
AFTER_QUESTION = re.compile(r"^\s*([^.]*)\.")
DECISION_BULLET = re.compile(r"^(D\d+) (.+?) gives (\w+)")
TITLE_PREFIX = "# "
QUESTION_IDS = ("Q1", "Q2", "Q3", "Q4")
COMMAND_COLUMNS = ("Command", "What it does", "Status")
TABLE_BAR = "|"
STATUS_WORDS = re.compile(r"^(works|not built \(T\d+\))$")
SHELL_FENCE = "```sh"
FENCE = "```"


def read_source_lines(root, relative):
    assert isinstance(root, Path), f"read_source_lines needs a Path root, got {root!r}. Fix: pass the repository root."
    assert relative, "read_source_lines needs a relative file name. Fix: pass the path under the root."
    lines = inside(root, relative).read_text().splitlines()
    assert lines, f"{relative} is empty. Rule: every source file has content. Fix: restore it."
    return lines


def section_bullets(lines, heading):
    assert heading.startswith(SECTION_PREFIX), f"a heading starts with {SECTION_PREFIX!r}, got {heading!r}. Fix: pass the full heading line."
    assert heading in lines, f"the source has no {heading!r} section. Rule: the site reads this section. Fix: restore the heading."
    bullets = []
    first = lines.index(heading) + 1
    for number, line in enumerate(lines[first:], start=first + 1):
        if line.startswith(SECTION_PREFIX):
            break
        if line.startswith(BULLET_PREFIX):
            bullets.append({"line": number, "text": line[len(BULLET_PREFIX):].strip()})
        elif line.startswith(CONTINUATION_PREFIX) and bullets:
            bullets[-1]["text"] += " " + line.strip()
    assert bullets, f"the section {heading!r} holds no bullets. Rule: the site lists them. Fix: restore the bullets."
    return bullets


def section_lines(lines, heading):
    assert heading.startswith(SECTION_PREFIX), f"a heading starts with {SECTION_PREFIX!r}, got {heading!r}. Fix: pass the full heading line."
    assert lines.count(heading) == 1, f"the source holds {lines.count(heading)} {heading!r} headings, not one. Rule: the site reads one section. Fix: restore the heading."
    first = lines.index(heading) + 1
    following = [number for number, line in enumerate(lines[first:], start=first) if line.startswith(SECTION_PREFIX)]
    last = following[0] if following else len(lines)
    return [(number, line) for number, line in enumerate(lines[first:last], first + 1)]


def paragraph_text(numbered, heading):
    assert numbered is not None, "paragraph_text needs numbered lines. Fix: pass section_lines output."
    filled = [(number, line.strip()) for number, line in numbered if line.strip()]
    assert filled, f"the section {heading!r} holds no text. Rule: the site shows its paragraph. Fix: restore it."
    return {"line": filled[0][0], "text": " ".join(line for _, line in filled)}


def summary_paragraph(lines):
    assert isinstance(lines, list) and lines, f"summary_paragraph needs the README lines, got {lines!r}. Fix: pass read_source_lines output."
    body = lines[1:next(number for number, line in enumerate(lines) if number and line.startswith(SECTION_PREFIX))]
    paragraphs = [paragraph for paragraph in "\n".join(body).split("\n\n") if paragraph.strip()]
    assert len(paragraphs) >= 2, f"{README_FILE} needs the description and one more paragraph under the title, got {len(paragraphs)}. Fix: restore it."
    first_line = next(number for number, line in enumerate(lines, start=1) if line == paragraphs[1].splitlines()[0])
    summary = {"line": first_line, "text": " ".join(line.strip() for line in paragraphs[1].splitlines())}
    assert summary["text"], f"{README_FILE} gave an empty summary, got {summary}. Fix: restore the paragraph."
    return summary


def table_cells(line):
    assert line.startswith(TABLE_BAR) and line.endswith(TABLE_BAR), f"a table row starts and ends with {TABLE_BAR!r}, got {line!r}. Fix: restore the row."
    cells = tuple(cell.strip() for cell in line.strip(TABLE_BAR).split(TABLE_BAR))
    assert all(cells), f"a table row has an empty cell, got {line!r}. Fix: fill every cell."
    return cells


def command_rows(lines):
    numbered = [(number, line) for number, line in section_lines(lines, COMMANDS_HEADING) if line.startswith(TABLE_BAR)]
    assert len(numbered) >= 3, f"{README_FILE} section {COMMANDS_HEADING!r} needs a header, a separator and a row, got {len(numbered)} table lines. Fix: restore the table."
    header, separator, body = table_cells(numbered[0][1]), table_cells(numbered[1][1]), numbered[2:]
    assert header == COMMAND_COLUMNS, f"the command table head must be {COMMAND_COLUMNS}, got {header}. Fix: restore the head."
    assert all(set(cell) <= {"-", ":"} for cell in separator), f"the second table line must be the separator, got {separator}. Fix: restore it."
    rows = []
    for number, line in body:
        cells = table_cells(line)
        assert len(cells) == len(COMMAND_COLUMNS), f"{README_FILE}:{number} has {len(cells)} cells, not {len(COMMAND_COLUMNS)}. Rule: the site reads three columns. Fix: restore the row."
        assert STATUS_WORDS.match(cells[2]), f"{README_FILE}:{number} has the status {cells[2]!r}. Rule: a status reads 'works' or 'not built (Tn)'. Fix: restore it."
        rows.append({"line": number, "command": cells[0], "does": cells[1], "status": cells[2]})
    return rows


def shell_blocks(numbered):
    blocks, current, label = [], None, ""
    for number, line in numbered:
        if current is None and line == SHELL_FENCE:
            assert label and not label.startswith(FENCE), f"{README_FILE}:{number} opens a code block with no sentence before it. Rule: the site labels each block. Fix: add the sentence."
            current = {"line": number + 1, "label": label, "lines": []}
        elif current is not None and line == FENCE:
            blocks.append({"line": current["line"], "label": current["label"], "text": "\n".join(current["lines"])})
            current = None
        elif current is not None:
            current["lines"].append(line)
        elif line.strip():
            label = line.strip()
    assert current is None, f"{README_FILE} leaves a code block open at line {current['line']}. Fix: close it."
    return blocks


def command_section(lines, heading):
    assert isinstance(lines, list) and lines, f"command_section needs the README lines, got {lines!r}. Fix: pass read_source_lines output."
    numbered = section_lines(lines, heading)
    lead = paragraph_text(numbered[:1], heading)
    blocks = shell_blocks(numbered)
    assert blocks and all(block["text"] for block in blocks), f"{README_FILE} section {heading!r} needs sh code blocks with commands. Rule: the site shows the commands. Fix: restore them."
    assert lead["text"], f"{README_FILE} section {heading!r} has no lead sentence, got {lead}. Fix: restore it."
    return {"lead": lead, "blocks": blocks}


def isolation_data(lines):
    assert isinstance(lines, list) and lines, f"isolation_data needs the README lines, got {lines!r}. Fix: pass read_source_lines output."
    paragraph = paragraph_text(section_lines(lines, ISOLATION_HEADING), ISOLATION_HEADING)
    assert paragraph["text"], f"{README_FILE} section {ISOLATION_HEADING!r} is empty. Fix: restore it."
    return paragraph


def project_data(root):
    project = tomllib.loads(inside(root, PROJECT_FILE).read_text())["project"]
    repository = project["urls"]["Repository"]
    license_name = read_source_lines(root, LICENSE_FILE)[0].strip()
    assert repository.startswith("https://"), f"{PROJECT_FILE} Repository must be an https link, got {repository!r}. Fix: restore it."
    assert license_name, f"{LICENSE_FILE} opens with no license name. Fix: restore it."
    return {"file": PROJECT_FILE, "license_file": LICENSE_FILE, "repository": repository, "license": license_name}


def readme_data(root):
    lines = read_source_lines(root, README_FILE)
    assert lines[0].startswith(TITLE_PREFIX), f"{README_FILE} must open with a '# name' title, got {lines[0]!r}. Fix: restore the title."
    description = next(line for line in lines[1:] if line.strip())
    limits = section_bullets(lines, LIMITS_HEADING)
    data = {
        "file": README_FILE,
        "title": lines[0][len(TITLE_PREFIX):],
        "description": description,
        "limits": limits,
        "summary": summary_paragraph(lines),
        "commands": command_rows(lines),
        "offline": command_section(lines, OFFLINE_HEADING),
        "install": command_section(lines, INSTALL_HEADING),
        "isolation": isolation_data(lines),
    }
    assert data["title"] and data["description"], f"{README_FILE} gave an empty title or description, got {data}. Fix: restore them."
    return data


def question_row(bullet):
    assert "line" in bullet and "text" in bullet, f"a bullet has line and text, got {sorted(bullet)}. Fix: pass section_bullets output."
    matched = QUESTION_BULLET.match(bullet["text"])
    assert matched, f"contract line {bullet['line']} does not read 'Qn Name: question?'. Rule: the site parses the four questions. Fix: restore the format."
    identifier, name, asks, rest = matched.groups()
    result = RESULT_TEXT.search(rest) or AFTER_QUESTION.match(rest)
    assert result, f"contract line {bullet['line']} gives no answer type after the question. Rule: each question names its result. Fix: add 'Result: X.'."
    return {"id": identifier, "name": name, "asks": asks, "answer": result.group(1).strip(), "line": bullet["line"]}


def decision_row(bullet):
    assert "line" in bullet and "text" in bullet, f"a bullet has line and text, got {sorted(bullet)}. Fix: pass section_bullets output."
    matched = DECISION_BULLET.match(bullet["text"])
    assert matched, f"contract line {bullet['line']} does not read 'Dn when gives Decision'. Rule: the site parses the table. Fix: restore the format."
    identifier, when, decision = matched.groups()
    return {"id": identifier, "when": when, "decision": decision, "line": bullet["line"]}


def contract_data(root):
    lines = read_source_lines(root, CONTRACT_FILE)
    questions = [question_row(bullet) for bullet in section_bullets(lines, QUESTIONS_HEADING)]
    table = [bullet for bullet in section_bullets(lines, DECISIONS_HEADING) if DECISION_BULLET.match(bullet["text"])]
    assert table, f"{CONTRACT_FILE} has no decision rules of the form 'Dn ... gives X'. Rule: the site shows the table. Fix: restore them."
    data = {"file": CONTRACT_FILE, "questions": questions, "decisions": [decision_row(bullet) for bullet in table]}
    assert len(data["questions"]) == len(QUESTION_IDS), f"{CONTRACT_FILE} must hold the four questions {QUESTION_IDS}, got {[item['id'] for item in questions]}. Fix: restore them."
    return data


def json_line(lines, needle):
    assert needle, "json_line needs text to find. Fix: pass the JSON fragment."
    found = [number for number, line in enumerate(lines, start=1) if needle in line]
    assert len(found) == 1, f"{needle!r} occurs on {len(found)} lines, not one. Rule: a row traces to one line. Fix: make the JSON fragment unique."
    return found[0]


def json_source(root, relative):
    lines = read_source_lines(root, relative)
    document = json.loads("\n".join(lines))
    assert isinstance(document, dict), f"{relative} must hold a JSON object, got {type(document).__name__}. Fix: restore it."
    assert lines and document, f"{relative} is empty. Rule: the site reads it. Fix: restore it."
    return lines, document


def gate_data(root):
    lines, document = json_source(root, GATE_STATUS_FILE)
    rows = [{**gate, "line": json_line(lines, f'"label": {json.dumps(gate["label"])}')} for gate in document["gates"]]
    assert rows, f"{GATE_STATUS_FILE} lists no gates. Rule: the page shows gate status. Fix: run scripts/site/build.py."
    data = {"file": GATE_STATUS_FILE, "command": document["command"], "rows": rows}
    assert all("status" in row and "result" in row for row in rows), f"every gate row needs status and result, got {rows}. Fix: run scripts/site/build.py."
    return data


def live_data(root):
    lines, document = json_source(root, LIVE_RESULT_FILE)
    rows = [{**row, "line": json_line(lines, f'"row": {json.dumps(row["row"])}')} for row in document["rows"]]
    completed = [{**row, "line": json_line(lines, f'"row": {json.dumps(row["row"])}')} for row in document["completed_rows"]]
    limits = [{"text": limit, "line": json_line(lines, json.dumps(limit))} for limit in document["limits"]]
    explanation = [{"text": text, "line": json_line(lines, json.dumps(text))} for text in document["explanation"]]
    history = [{**item, "line": json_line(lines, f'"when": {json.dumps(item["when"])}')} for item in document["history"]]
    assert rows and limits, f"{LIVE_RESULT_FILE} needs rows and limits. Rule: the page shows the result with its limits. Fix: restore them."
    assert document["run"] == len(history) + 1, f"{LIVE_RESULT_FILE} is run {document['run']} with {len(history)} earlier runs. Rule: the current run follows its history. Fix: list every earlier run."
    data = {**document, "file": LIVE_RESULT_FILE, "rows": rows, "completed_rows": completed, "limits": limits, "explanation": explanation, "history": history}
    assert isinstance(data["claims"], dict), f"{LIVE_RESULT_FILE} needs a claims table, got {data.get('claims')!r}. Rule: held-back phrases are checked against it. Fix: add claims."
    return data


def site_data(root):
    data = {"readme": readme_data(root), "project": project_data(root), "contract": contract_data(root), "gates": gate_data(root), "live": live_data(root)}
    assert set(data) == {"readme", "project", "contract", "gates", "live"}, f"site data must have five parts, got {sorted(data)}"
    assert all(part["file"] for part in data.values()), f"every part names its source file, got {data}"
    return data
