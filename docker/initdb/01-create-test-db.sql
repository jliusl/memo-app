-- Runs once, on first container boot, before any application connects.
-- The test database is a separate database in the same container so that
-- `memo_test` can be reset without touching development data.
CREATE DATABASE memo_test OWNER memo;
