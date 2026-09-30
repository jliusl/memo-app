import { defineConfig, devices } from '@playwright/test';

const FRONTEND_PORT = 4173;
const BACKEND_PORT = 8000;

/**
 * See https://playwright.dev/docs/test-configuration.
 *
 * The app under test is `src/` - see docs/adr/0001. Both servers below are started here
 * rather than left to the developer, so that `npx playwright test` is the whole recipe.
 */
export default defineConfig({
  testDir: './tests',
  /*
   * Serial on purpose. Every test shares one database and resets it from the API, so two
   * workers running at the same time would wipe each other's fixtures mid-test. Getting
   * parallelism back means giving each worker its own account and never resetting
   * globally - worth doing, but only once the suite is large enough to notice.
   */
  fullyParallel: false,
  workers: 1,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /*
     * The built app, served by Vite's preview server, which also proxies /api to the
     * backend. Testing the app and the API on one origin is what makes the session cookie
     * a first-party cookie, so what the tests exercise is what production would look like.
     */
    baseURL: `http://localhost:${FRONTEND_PORT}`,

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],

  webServer: [
    {
      // ENV=test is what registers POST /api/__test__/reset. Without it the suite has no
      // way to get a known starting state, which is the point of that route - see
      // docs/adr/0001. An environment variable beats the .env file in pydantic-settings,
      // so this wins even though .env says ENV=dev.
      // --loop names a selector event loop, which Windows needs before the app is even
      // imported (uvicorn builds the loop first, so an in-app fix would be too late).
      // It is a no-op on Linux, where that is already the default. See src/backend/app/loop.py.
      command:
        'uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --loop app.loop:selector_event_loop',
      cwd: 'src/backend',
      env: { ENV: 'test' },
      url: `http://127.0.0.1:${BACKEND_PORT}/api/health`,
      reuseExistingServer: !process.env.CI,
      stdout: 'pipe',
      stderr: 'pipe',
      timeout: 60_000,
    },
    {
      // Built, not dev-served: a stale dist would be a false pass, so the build is part of
      // starting the server rather than a step someone has to remember.
      command: `npm run build && npm run preview -- --port ${FRONTEND_PORT} --strictPort`,
      cwd: 'src/frontend',
      url: `http://localhost:${FRONTEND_PORT}`,
      reuseExistingServer: !process.env.CI,
      stdout: 'pipe',
      stderr: 'pipe',
      timeout: 120_000,
    },
  ],
});
