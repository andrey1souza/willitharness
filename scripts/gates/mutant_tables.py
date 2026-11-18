import importlib.util
from pathlib import Path

MODULE_DIRECTORY = Path(__file__).resolve().parent / "mutant_modules"
REQUIRED_NAMES = ("TESTS", "MUTANTS")


def load_modules(directory):
    assert directory.is_dir(), f"{directory} is not a directory. Rule: each mutation module is one file there. Fix: restore the folder."
    modules = {}
    for path in sorted(directory.glob("*.py")):
        spec = importlib.util.spec_from_file_location(f"mutant_module_{path.stem}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        missing = [name for name in REQUIRED_NAMES if not hasattr(module, name)]
        assert not missing, f"{path.name} lacks {missing}. Rule: a mutation module defines TESTS and MUTANTS. Fix: add them."
        modules[path.stem] = (module.TESTS, module.MUTANTS)
    assert modules, f"{directory} holds no mutation modules. Rule: a gate with no mutants proves nothing. Fix: add one."
    return modules


MODULES = load_modules(MODULE_DIRECTORY)
