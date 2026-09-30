"""Windows gives asyncio a `ProactorEventLoop` by default, and psycopg refuses to run its
async mode on one - it needs a selector loop. Linux has no proactor loop at all, so CI and
any production host never see this, which is exactly why it deserves one named place
instead of being rediscovered on the one machine that has the problem.

There are two ways in, because entry points differ in how they get an event loop:

* Anything that lets `asyncio.run` create the loop - Alembic, and pytest-asyncio - goes
  through the event loop policy, so calling `use_selector_event_loop()` before the loop
  exists is enough.
* uvicorn picks a loop *factory* and hands it to `asyncio.Runner`, which never consults the
  policy. There the factory has to be named on the command line, which is what
  `selector_event_loop` below is for:

      uv run uvicorn app.main:app --loop app.loop:selector_event_loop

  On Linux that flag is a no-op in effect: `SelectorEventLoop` is already the default.
"""

import asyncio
import sys

# A class is callable, so this satisfies uvicorn's expectation that `--loop` names
# something it can call with no arguments to get an event loop.
selector_event_loop = asyncio.SelectorEventLoop


def use_selector_event_loop() -> None:
    """Sets the policy for this process if it is running on Windows.

    Kept as a function rather than done at import time so that importing the package has no
    side effect on global interpreter state - only the entry points ask for this.
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
