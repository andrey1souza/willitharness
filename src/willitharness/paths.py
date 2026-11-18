from pathlib import Path


class PathOutsideRoot(Exception):
    pass


def inside(root, candidate):
    assert isinstance(root, Path), f"inside needs a Path root, got {root!r}. Fix: pass pathlib.Path."
    assert root.is_dir(), f"{root} is not a directory. Rule: paths are resolved under a real directory. Fix: pass the project directory."
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    if not resolved.is_relative_to(resolved_root):
        raise PathOutsideRoot(
            f"{candidate} resolves to {resolved}, outside {resolved_root}. "
            "Rule: a plan path stays inside the project directory. Fix: copy the file into the project or run from its folder."
        )
    assert resolved == resolved_root or resolved_root in resolved.parents, f"{resolved} escaped {resolved_root} after the check"
    return resolved
