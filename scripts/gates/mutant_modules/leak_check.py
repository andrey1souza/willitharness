SOURCE = 'scripts/gates/leak_check.py'

TESTS = (
    'tests/gates/test_leak_check.py',
)

MUTANTS = (
    ('home-path-ignored', SOURCE, 'if HOME_PATH.search(line)]', 'if False]'),
    ('leak-exits-clean', SOURCE, 'code = EXIT_LEAK if leaks else EXIT_CLEAN', 'code = EXIT_CLEAN'),
    ('clean-exits-leak', SOURCE, 'code = EXIT_LEAK if leaks else EXIT_CLEAN', 'code = EXIT_LEAK'),
    ('only-first-folder-scanned', SOURCE, 'for folder in scanned for path', 'for folder in scanned[:1] for path'),
    ('linux-home-ignored', SOURCE, '(?:/Users|/home)/', '(?:/Users)/'),
    ('summary-count-fixed', SOURCE, 'count=len(leaks)', 'count=1'),
    ('binary-file-crashes', SOURCE, '    except UnicodeDecodeError:\n        return []\n', '    except OSError:\n        return []\n'),
    ('no-folder-accepted', SOURCE, '    if not arguments:\n        print(USAGE, file=sys.stderr)\n        return EXIT_USAGE\n', ''),
    ('location-line-dropped', SOURCE, 'f"{path}:{number}"', 'f"{path}"'),
)
