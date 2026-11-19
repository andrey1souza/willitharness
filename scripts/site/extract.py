import json
import re
from pathlib import Path

from willitharness.paths import inside

README_FILE = "README.md"
CONTRACT_FILE = "docs/contract.md"
GATE_STATUS_FILE = "build/gate_status.json"
LIVE_RESULT_FILE = "fixtures/results/g4_4.json"
LIMITS_HEADING = "## Honest limits"
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


def readme_data(root):
    lines = read_source_lines(root, README_FILE)
    assert lines[0].startswith(TITLE_PREFIX), f"{README_FILE} must open with a '# name' title, got {lines[0]!r}. Fix: restore the title."
    description = next(line for line in lines[1:] if line.strip())
    limits = section_bullets(lines, LIMITS_HEADING)
    data = {"file": README_FILE, "title": lines[0][len(TITLE_PREFIX):], "description": description, "limits": limits}
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
    assert rows and limits, f"{LIVE_RESULT_FILE} needs rows and limits. Rule: the page shows the result with its limits. Fix: restore them."
    data = {**document, "file": LIVE_RESULT_FILE, "rows": rows, "completed_rows": completed, "limits": limits}
    assert isinstance(data["claims"], dict), f"{LIVE_RESULT_FILE} needs a claims table, got {data.get('claims')!r}. Rule: held-back phrases are checked against it. Fix: add claims."
    return data


def site_data(root):
    data = {"readme": readme_data(root), "contract": contract_data(root), "gates": gate_data(root), "live": live_data(root)}
    assert set(data) == {"readme", "contract", "gates", "live"}, f"site data must have four parts, got {sorted(data)}"
    assert all(part["file"] for part in data.values()), f"every part names its source file, got {data}"
    return data
