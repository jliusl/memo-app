"""Put the Allure results where the repository expects them, from any directory.

`--alluredir` resolves against the working directory rather than the root directory, which
makes every spelling of it wrong somewhere: `../../allure-results` is right from
`src/backend/` - where this suite is run - and writes to the root of the drive from the
repository root. Anchoring it to this file instead gives one location for both.

Deliberately not in `addopts`, because that is the one mechanism that cannot do this: a
pytest option in `pyproject.toml` is a fixed string, with no way to ask where it is.

Read by `allure-pytest` as the directory to write into; `--clean-alluredir` in `addopts`
then empties it per run, so results from an earlier run never mix into the next report.
See README.md for the commands that read it back.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def pytest_configure(config):
    if config.option.allure_report_dir is None:
        config.option.allure_report_dir = str(REPO_ROOT / "allure-results")
