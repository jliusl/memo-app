# Sandbox

Throwaway tests from before the memo app existed. Kept for reference; nothing here is run by
CI and nothing here should be extended.

- `example.spec.ts` — the `npm init playwright` scaffold demo. It drives the **live**
  playwright.dev site, and because `playwright.config.ts` has `testDir: './tests'` it used to
  run on every CI build, making CI depend on a third party's uptime.
- `test_example.py`, `test_codegen.py` — `playwright codegen --target python` output, driving
  playwright.dev and a blog.

The real suites live in `tests/` (browser E2E, TypeScript) and `src/backend/tests/` (API,
pytest). Run `pytest` from `src/backend/`, not from the repository root, or it will collect
the files in here.
