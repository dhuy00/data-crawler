"""Test suite for the data-crawler project.

Run via:
    pytest                    # all
    pytest tests/test_models.py -v
    pytest -m smoke           # smoke tests only

Each test is independent — no shared network. Smoke tests under
`tests/smoke/` may touch real URLs and are skipped if `RUN_NETWORK_TESTS=1`
is not in the environment.
"""