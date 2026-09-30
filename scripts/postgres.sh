#!/usr/bin/env bash
#
# Run a local PostgreSQL 17 from the official Windows binaries, with nothing installed
# system-wide: no installer, no Windows service, no administrator rights. Everything -
# binaries and data - lives under POSTGRES_HOME, which defaults to D:/pgsql, the drive with
# room on this machine.
#
# This is the route that needs no Docker at all. It is no longer what this machine uses day
# to day - docker compose up -d postgres is - and the two cannot run at the same time,
# because the container publishes 5432 and restarts with the machine. `stop` the container
# (or this) before starting the other.
#
# CI uses a postgres:17 service container. All three routes agree on the same credentials and
# the same two database names, so the application does not know or care which one it is
# talking to.
#
#   ./scripts/postgres.sh init     create the cluster, the role, and both databases
#   ./scripts/postgres.sh start    start the server in the background
#   ./scripts/postgres.sh stop     stop it
#   ./scripts/postgres.sh status   say whether it is running
#   ./scripts/postgres.sh psql     open a psql shell as the memo role
#   ./scripts/postgres.sh logs     show the server log
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Drive-letter paths on purpose. A POSIX path like /d/pgsql gets rewritten by Git Bash on
# its way to a native binary, and pg_ctl would then be handed a path that does not exist.
POSTGRES_HOME="${POSTGRES_HOME:-D:/pgsql}"
PGDATA="${PGDATA:-$POSTGRES_HOME/data}"
PGPORT="${PGPORT:-5432}"
BIN="$POSTGRES_HOME/bin"

MEMO_PASSWORD="${MEMO_PASSWORD:-memo}"
SUPERUSER_PASSWORD="${SUPERUSER_PASSWORD:-postgres}"

die() {
  echo "error: $*" >&2
  exit 1
}

# Called before anything else, because from the wrong shell the failure below would be
# reported as a missing PostgreSQL. WSL and Linux cannot run Windows .exe binaries with
# drive-letter paths: they would need their own PostgreSQL and their own data directory, so
# telling them that here is more use than a path that quietly does not exist.
require_windows_host() {
  case "$(uname -s)" in
    MINGW* | MSYS* | CYGWIN*) return 0 ;;
  esac
  cat >&2 <<'EOF'
error: this script drives the Windows PostgreSQL binaries, so it only runs under Git Bash.

  Running it from WSL or any other Linux shell fails for a reason that has nothing to do
  with PostgreSQL being missing: /mnt/d/pgsql holds .exe files that expect Windows paths,
  and they cannot serve a Linux data directory. Use Docker instead:

      docker compose up -d postgres

  Or run it through Git Bash, which PowerShell can also reach - by full path, because a bare
  `bash` on a Windows PATH is usually C:\Windows\System32\bash.exe, the WSL launcher:

      & 'C:\Program Files\Git\bin\bash.exe' scripts/postgres.sh status
EOF
  exit 1
}

require_binaries() {
  # Every subcommand except `logs` goes through here, so this is the one place the wrong
  # shell gets caught.
  require_windows_host
  [ -x "$BIN/initdb.exe" ] || die "no PostgreSQL at $POSTGRES_HOME. Expected $BIN/initdb.exe to exist."
  [ -x "$BIN/pg_ctl.exe" ] || die "no PostgreSQL at $POSTGRES_HOME. Expected $BIN/pg_ctl.exe to exist."
}

# -w on every psql call so that a missing password fails immediately instead of sitting
# there waiting for input that a scripted run will never provide.
psql_admin() {
  PGPASSWORD="$SUPERUSER_PASSWORD" "$BIN/psql.exe" -w -h localhost -p "$PGPORT" -U postgres "$@"
}

is_running() {
  "$BIN/pg_ctl.exe" -D "$PGDATA" status >/dev/null 2>&1
}

cmd_init() {
  require_binaries
  if [ -d "$PGDATA" ]; then
    die "$PGDATA already exists. Remove it if you really mean to start over."
  fi

  # --pwfile rather than an interactive prompt, for the same reason as -w above: the
  # superuser needs a password, because host connections require scram and there is no
  # Unix socket to fall back on with Windows binaries.
  local pwfile
  pwfile="$(cygpath -w "$(mktemp)")"
  printf '%s\n' "$SUPERUSER_PASSWORD" > "$pwfile"
  trap 'rm -f "$pwfile"' RETURN

  # UTF8 with the C locale: the default locale on a Chinese Windows install picks the GBK
  # code page, which initdb refuses to combine with UTF8.
  "$BIN/initdb.exe" \
    -D "$PGDATA" \
    -U postgres \
    --pwfile="$pwfile" \
    --encoding=UTF8 \
    --locale=C \
    --auth-local=trust \
    --auth-host=scram-sha-256

  cmd_start

  # The application's credentials, matching .env and docker-compose.yml.
  psql_admin -d postgres -v ON_ERROR_STOP=1 -q \
    -c "CREATE ROLE memo LOGIN PASSWORD '$MEMO_PASSWORD';" \
    -c "CREATE DATABASE memo_dev OWNER memo;"

  # The same file docker-compose mounts and CI runs, so the test database is defined once.
  psql_admin -d memo_dev -v ON_ERROR_STOP=1 -q -f "$REPO_ROOT/docker/initdb/01-create-test-db.sql"

  echo
  echo "ready: memo_dev and memo_test on localhost:$PGPORT, role 'memo'."
  echo "next:  cd src/backend && uv run alembic upgrade head"
}

cmd_start() {
  require_binaries
  if is_running; then
    echo "already running on port $PGPORT."
    return
  fi
  # -l is not optional here: without a log file pg_ctl cannot detach cleanly on Windows.
  "$BIN/pg_ctl.exe" -D "$PGDATA" -l "$PGDATA/server.log" -o "-p $PGPORT" -w start
}

cmd_stop() {
  require_binaries
  if ! is_running; then
    echo "not running."
    return
  fi
  "$BIN/pg_ctl.exe" -D "$PGDATA" -m fast -w stop
}

cmd_status() {
  require_binaries
  if is_running; then
    echo "running on port $PGPORT, data in $PGDATA"
  else
    echo "not running (data in $PGDATA)"
    return 1
  fi
}

cmd_psql() {
  require_binaries
  PGPASSWORD="$MEMO_PASSWORD" exec "$BIN/psql.exe" -w -h localhost -p "$PGPORT" -U memo -d memo_dev
}

cmd_logs() {
  [ -f "$PGDATA/server.log" ] || die "no log yet at $PGDATA/server.log"
  tail -n 40 "$PGDATA/server.log"
}

case "${1:-}" in
  init) cmd_init ;;
  start) cmd_start ;;
  stop) cmd_stop ;;
  status) cmd_status ;;
  psql) cmd_psql ;;
  logs) cmd_logs ;;
  *)
    echo "usage: $0 {init|start|stop|status|psql|logs}" >&2
    exit 2
    ;;
esac
