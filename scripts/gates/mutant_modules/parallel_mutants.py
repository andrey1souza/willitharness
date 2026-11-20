SOURCE = 'scripts/gates/mutants.py'

TESTS = (
    'tests/gates/test_mutants_parallel.py',
)

MUTANTS = (
    ('survivor-counted-as-killed', SOURCE, 'killed += 0 if survived else 1', 'killed += 1'),
    ('survivor-printed-as-killed', SOURCE, '("SURVIVED " if survived else "killed   ")', '"killed   "'),
    ('table-order-lost', SOURCE, 'zip(mutants, pool.map(', 'zip(reversed(mutants), pool.map('),
    ('jobs-option-ignored', SOURCE, 'make_pool(max_workers=jobs)', 'make_pool(max_workers=SINGLE_JOB)'),
    ('jobs-not-passed-to-the-runner', SOURCE, 'runner(name, arguments.tests, arguments.jobs)', 'runner(name, arguments.tests, SINGLE_JOB)'),
    ('default-jobs-not-wired', SOURCE, 'default=default_jobs(os.cpu_count())', 'default=SINGLE_JOB'),
    ('cpu-cap-becomes-floor', SOURCE, 'min(MAX_DEFAULT_JOBS, cpu_count or SINGLE_JOB)', 'max(MAX_DEFAULT_JOBS, cpu_count or SINGLE_JOB)'),
    ('unknown-cpu-count-crashes', SOURCE, 'cpu_count or SINGLE_JOB', 'cpu_count'),
    ('zero-jobs-accepted', SOURCE, 'if value < SINGLE_JOB:', 'if value < 0:'),
)
