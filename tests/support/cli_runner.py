from willitharness import cli


def run_cli(capsys, arguments):
    assert isinstance(arguments, list), f"run_cli needs a list of arguments, got {arguments!r}. Fix: pass a list."
    code = cli.main(arguments)
    captured = capsys.readouterr()
    assert isinstance(code, int), f"cli.main returned {code!r}, not an exit code"
    return code, captured.out, captured.err
