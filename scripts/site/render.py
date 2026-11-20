import re
from html import escape
from pathlib import Path
from string import Template

from willitharness.paths import inside

TEMPLATE_FILE = "site/src/index.html"
STYLE_FILE = "site/src/style.css"
PAGE_NAME = "index.html"
STYLE_NAME = "style.css"
CODE_SPAN = re.compile(r"`([^`]+)`")
QUESTION_COLUMNS = ("Question", "Name", "Asks", "Answer")
DECISION_COLUMNS = ("Case", "When", "Decision")
GATE_COLUMNS = ("Gate", "Status", "Result")
LIVE_COLUMNS = ("Task", "Arm C", "Arm B", "Verdict", "Noise", "Effect")
COMPLETED_COLUMNS = ("Task", "Arm C", "Arm B", "Verdict", "Note")
TONES = {
    "FixLoading": "warn",
    "Keep": "keep",
    "ReplaceWithGuard": "keep",
    "DeleteCandidate": "bad",
    "NeedsMoreRuns": "warn",
    "CannotDecide": "warn",
    "passed": "keep",
    "failed": "bad",
    "FirstHigher": "keep",
    "FirstLower": "bad",
    "NoiseOk": "keep",
    "RuleLowersViolations": "keep",
}


def inline(text):
    assert isinstance(text, str), f"inline needs text, got {type(text).__name__}. Fix: pass the source text."
    rendered = CODE_SPAN.sub(lambda found: f"<code>{found.group(1)}</code>", escape(text, quote=False))
    assert rendered.count("<code>") == rendered.count("</code>"), f"unbalanced code spans in {text!r}. Fix: close every backtick."
    return rendered


def source_attribute(file, line):
    assert line >= 1, f"a source line counts from 1, got {line}. Fix: pass the line number from extract."
    assert file, "a source file name is needed. Fix: pass the path from extract."
    return f'data-source="{escape(file)}:{line}"'


def status_cell(word):
    assert word, "a status needs its word. Rule: status is never colour alone. Fix: pass the status text."
    tone = TONES.get(word, "warn")
    assert tone in ("keep", "warn", "bad"), f"tone {tone!r} is not a design token. Fix: use keep, warn or bad."
    return f'<td><span class="status {tone}">{escape(word)}</span></td>'


def table_row(file, line, cells):
    assert cells, "a row needs cells. Fix: pass the cell html."
    assert all(cell.startswith("<td") for cell in cells), f"cells must be td elements, got {cells!r}"
    return f"<tr {source_attribute(file, line)}>{''.join(cells)}</tr>"


def plain(text):
    assert isinstance(text, str), f"plain needs text, got {type(text).__name__}. Fix: pass the source text."
    cell = f"<td>{inline(text)}</td>"
    assert cell.endswith("</td>"), f"cell {cell!r} must close. Fix: correct plain."
    return cell


def identifier(text):
    assert isinstance(text, str), f"identifier needs text, got {type(text).__name__}. Fix: pass the id text."
    cell = f'<td><span class="id">{escape(text)}</span></td>'
    assert escape(text) in cell, f"identifier {text!r} lost in {cell!r}. Fix: correct identifier."
    return cell


def table_rows(file, items, cells_of):
    assert items, f"a table of {file} needs items. Fix: run extract or status.py first."
    assert callable(cells_of), f"cells_of must build the cells of one item, got {cells_of!r}. Fix: pass a cell builder."
    rows = "\n".join(table_row(file, item["line"], cells_of(item)) for item in items)
    assert rows.count("<tr ") == len(items), f"one row per item expected, got {rows!r}"
    return rows


def question_cells(item):
    assert "asks" in item, f"a question item needs asks, got {sorted(item)}. Fix: pass extract output."
    cells = [identifier(item["id"]), plain(item["name"]), plain(item["asks"]), plain(item["answer"])]
    assert len(cells) == len(QUESTION_COLUMNS), f"a question row has {len(QUESTION_COLUMNS)} cells, got {len(cells)}. Fix: match the table head."
    return cells


def decision_cells(item):
    assert "when" in item, f"a decision item needs when, got {sorted(item)}. Fix: pass extract output."
    cells = [identifier(item["id"]), plain(item["when"]), status_cell(item["decision"])]
    assert len(cells) == len(DECISION_COLUMNS), f"a decision row has {len(DECISION_COLUMNS)} cells, got {len(cells)}. Fix: match the table head."
    return cells


def gate_cells(item):
    assert "status" in item, f"a gate item needs status, got {sorted(item)}. Fix: pass extract output."
    cells = [plain(item["label"]), status_cell(item["status"]), plain(item["result"])]
    assert len(cells) == len(GATE_COLUMNS), f"a gate row has {len(GATE_COLUMNS)} cells, got {len(cells)}. Fix: match the table head."
    return cells


def arm_cell(arm, hits, runs):
    assert 0 <= hits <= runs, f"arm {arm} has {hits} hits of {runs} runs. Rule: hits never exceed runs. Fix: correct the result file."
    assert arm, "an arm needs its label. Fix: pass the arm from the result file."
    return f"<td>{escape(arm)}: {hits} of {runs} runs</td>"


def live_cells(item):
    assert "first_arm" in item, f"a live item needs first_arm, got {sorted(item)}. Fix: pass extract output."
    cells = [
        identifier(item["task"]),
        arm_cell(item["first_arm"], item["first_hits"], item["first_runs"]),
        arm_cell(item["second_arm"], item["second_hits"], item["second_runs"]),
        status_cell(item["verdict"]),
        status_cell(item["noise"]),
        status_cell(item["effect"]),
    ]
    assert len(cells) == len(LIVE_COLUMNS), f"a live row has {len(LIVE_COLUMNS)} cells, got {len(cells)}. Fix: match the table head."
    return cells


def completed_cells(item):
    assert "note" in item, f"a completed item needs a note, got {sorted(item)}. Fix: pass extract output."
    cells = [
        identifier(item["task"]),
        arm_cell(item["first_arm"], item["first_hits"], item["first_runs"]),
        arm_cell(item["second_arm"], item["second_hits"], item["second_runs"]),
        status_cell(item["verdict"]),
        plain(item["note"]),
    ]
    assert len(cells) == len(COMPLETED_COLUMNS), f"a completed row has {len(COMPLETED_COLUMNS)} cells, got {len(cells)}. Fix: match the table head."
    return cells


def earlier_run_text(earlier):
    assert earlier["cost_usd"] > 0, f"the earlier run needs a cost, got {earlier}. Fix: restore the result file."
    text = (
        f"Run {earlier['run']} cost ${earlier['cost_usd']!r}. Arm C of stop-server had {earlier['stop_server_first_hits']} hits. "
        f"The completed row of backup-delete read {earlier['completed_backup_delete']}. {earlier['explanation']}"
    )
    assert earlier["explanation"] in text, f"the explanation must stay in the text, got {text!r}"
    return escape(text, quote=False)


def list_items(file, entries):
    assert entries, "a list needs entries. Fix: pass the extracted bullets."
    assert all("text" in entry and "line" in entry for entry in entries), f"entries need text and line, got {entries!r}"
    return "\n".join(f"<li {source_attribute(file, entry['line'])}>{inline(entry['text'])}</li>" for entry in entries)


def page_values(data):
    readme, contract, gates, live = data["readme"], data["contract"], data["gates"], data["live"]
    contract_file, live_file = contract["file"], live["file"]
    assert readme["description"], "the README gave no description. Fix: restore the line under the title."
    values = {
        "title": escape(readme["title"]),
        "description": escape(readme["description"], quote=True),
        "contract_file": escape(contract_file),
        "question_rows": table_rows(contract_file, contract["questions"], question_cells),
        "decision_rows": table_rows(contract_file, contract["decisions"], decision_cells),
        "gate_rows": table_rows(gates["file"], gates["rows"], gate_cells),
        "gate_command": escape(gates["command"]),
        "gate_file": escape(gates["file"]),
        "live_gate": escape(live["gate"]),
        "live_command": escape(live["command"]),
        "live_model": escape(live["model"]),
        "live_reps": live["reps_per_cell"],
        "live_date": escape(live["date"]),
        "live_cost": repr(live["cost_usd"]),
        "live_file": escape(live_file),
        "live_outcome": escape(live["outcome"]),
        "live_rows": table_rows(live_file, live["rows"], live_cells),
        "completed_rows": table_rows(live_file, live["completed_rows"], completed_cells),
        "earlier_run": earlier_run_text(live["earlier_run"]),
        "live_limits": list_items(live_file, live["limits"]),
        "limits": list_items(readme["file"], readme["limits"]),
        "readme_file": escape(readme["file"]),
    }
    assert all(value != "" for value in values.values()), f"no placeholder value may be empty, got {sorted(key for key, value in values.items() if value == '')}"
    return values


def render_site(root, data):
    assert isinstance(root, Path), f"render_site needs a Path root, got {root!r}. Fix: pass the repository root."
    assert set(data) == {"readme", "contract", "gates", "live"}, f"site data needs four parts, got {sorted(data)}. Fix: pass site_data output."
    page = Template(inside(root, TEMPLATE_FILE).read_text()).substitute(page_values(data))
    style = inside(root, STYLE_FILE).read_text()
    return {PAGE_NAME: page, STYLE_NAME: style}
