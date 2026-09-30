# The memo app is the System Under Test

This repository began as a Playwright harness — agents, an MCP test server, and CI — driving throwaway tests against third-party sites (playwright.dev, a blog). We can control neither their DOM nor their data, which makes the `healer` agent meaningless: when a test breaks because someone else changed their page, there is nothing to repair. We are therefore adding a real memo application under `src/` whose DOM, data, and failure modes are ours.

The consequence, and the reason this is written down: **the memo app is not a demo.** It must ship with a stable accessible locator contract, a test-only reset path that does not exist outside the test environment, and a CI-runnable startup. A future reader who finds an application inside a Playwright repository should not delete those test hooks as clutter.

Considered and rejected: keeping third-party sites as the target (no control, so automated repair is impossible), and treating the memo app as an ordinary side project that happens to live here (which would have dropped the test hooks entirely).
