def plant(folder, name, text):
    assert name and "/" not in name, f"plant needs a plain file name, got {name!r}. Fix: use write_tree for paths."
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(text)
    assert (folder / name).is_file(), f"plant did not create {folder / name}"
    return folder


def write_tree(root, files):
    assert files, f"write_tree got no files for {root}. Fix: name at least one file."
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    assert all((root / name).is_file() for name in files), f"write_tree left a file missing under {root}"
    return root
