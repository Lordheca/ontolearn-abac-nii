#!/usr/bin/env bash
#
# Start the whole OntoLearn Annotator stack locally: ABAC_NII first, then the annotator.
#
# The annotator delegates every authorization decision to ABAC_NII, and fails *closed*
# when it cannot reach it — so ABAC has to be up and answering before Next starts, or
# the whole UI looks broken in a way indistinguishable from "permission denied".
#
# Usage:
#   ./start-local.sh                # start everything, then run the dev server in the foreground
#   ./start-local.sh --seed         # also seed the annotator database (first run only)
#   ./start-local.sh --no-dev       # bring up the backing services only, don't start Next
#   ./start-local.sh --rebuild      # force a no-cache rebuild of the ABAC service image
#   ./start-local.sh --down         # stop both stacks
#
# Paths can be overridden: ABAC_DIR=... ANNOTATOR_DIR=... ./start-local.sh

set -euo pipefail

# ----------------------------------------------------------------- configuration

ABAC_DIR="${ABAC_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/ABAC_NII}"
ANNOTATOR_DIR="${ANNOTATOR_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/ontolearn-annotator}"

# Shared HS256 secret: the annotator signs its ABAC token with ABAC_SECRET, the
# inheritance_service verifies it with SECRET_KEY. They MUST be the same string.
SHARED_ABAC_SECRET="${SHARED_ABAC_SECRET:-local-dev-abac-secret}"

ABAC_PORT=5004      # inheritance_service (FastAPI)
OPA_PORT=8181       # Open Policy Agent
ABAC_DB_PORT=3306   # ABAC MySQL
ANNOTATOR_PORT=3000 # Next dev server
ANNOTATOR_DB_PORT=3307
MAILDEV_PORT=1080
MINIO_PORT=9000 #MinIO / S3
MINIO_CONSOLE_PORT=9001
# MinIO no longer publishes public images: quay.io answers 401 and Docker Hub removed
# them, so these pinned tags must already be in the local image cache (see
# handover/README.md, "MinIO images"). MINIO_IMAGE must match docker-compose.yml.
MINIO_IMAGE="quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z"
MINIO_MC_IMAGE="quay.io/minio/mc:RELEASE.2025-08-13T08-35-41Z"

DO_SEED=0
DO_DEV=1
DO_REBUILD=0
DO_DOWN=0

for arg in "$@"; do
	case "$arg" in
	--seed) DO_SEED=1 ;;
	--no-dev) DO_DEV=0 ;;
	--rebuild) DO_REBUILD=1 ;;
	--down) DO_DOWN=1 ;;
	-h | --help)
		sed -n '3,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
		exit 0
		;;
	*)
		echo "Unknown option: $arg (try --help)" >&2
		exit 2
		;;
	esac
done

# ----------------------------------------------------------------------- helpers

if [ -t 1 ]; then
	BOLD=$(printf '\033[1m') RED=$(printf '\033[31m') GREEN=$(printf '\033[32m')
	YELLOW=$(printf '\033[33m') BLUE=$(printf '\033[34m') RESET=$(printf '\033[0m')
else
	BOLD= RED= GREEN= YELLOW= BLUE= RESET=
fi

step() { printf '\n%s==>%s %s%s%s\n' "$BLUE" "$RESET" "$BOLD" "$*" "$RESET"; }
info() { printf '    %s\n' "$*"; }
ok() { printf '    %s✓%s %s\n' "$GREEN" "$RESET" "$*"; }
warn() { printf '    %s!%s %s\n' "$YELLOW" "$RESET" "$*"; }
die() {
	printf '\n%serror:%s %s\n' "$RED" "$RESET" "$*" >&2
	exit 1
}

# wait_for <label> <timeout_seconds> <command...>
wait_for() {
	local label="$1" timeout="$2" elapsed=0
	shift 2
	printf '    waiting for %s' "$label"
	while ! "$@" >/dev/null 2>&1; do
		if [ "$elapsed" -ge "$timeout" ]; then
			printf ' %stimeout%s\n' "$RED" "$RESET"
			return 1
		fi
		printf '.'
		sleep 3
		elapsed=$((elapsed + 3))
	done
	printf ' %sready%s (%ss)\n' "$GREEN" "$RESET" "$elapsed"
}

http_ok() { curl -sf -o /dev/null -m 10 "$1"; }
port_busy() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

# ------------------------------------------------------------------- preflight

step "Preflight"

# A missing image makes docker try to pull it, which fails with an opaque 401.
missing_images=()
for img in "$MINIO_IMAGE" "$MINIO_MC_IMAGE"; do
	docker image inspect "$img" >/dev/null 2>&1 || missing_images+=("$img")
done
if [ "${#missing_images[@]}" -gt 0 ]; then
	for img in "${missing_images[@]}"; do warn "missing local image: $img"; done
	die "MinIO images are no longer public — load them from a teammate's export (handover/README.md, \"MinIO images\")"
fi
ok "MinIO images present locally"

command -v docker >/dev/null || die "docker is not installed or not on PATH"
docker info >/dev/null 2>&1 || die "the docker daemon is not reachable — start Docker and retry"

if docker compose version >/dev/null 2>&1; then
	DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
	DC="docker-compose"
else
	die "neither 'docker compose' nor 'docker-compose' is available"
fi

[ -d "$ABAC_DIR" ] || die "ABAC_NII not found at $ABAC_DIR (override with ABAC_DIR=...)"
[ -d "$ANNOTATOR_DIR" ] || die "annotator not found at $ANNOTATOR_DIR (override with ANNOTATOR_DIR=...)"

ABAC_DC="$DC -f $ABAC_DIR/docker-compose.yml"
ANNOTATOR_DC="$DC -f $ANNOTATOR_DIR/docker-compose.yml -f $ANNOTATOR_DIR/docker-compose.dev.yml"

ok "docker ready, using '$DC'"
info "ABAC_NII:  $ABAC_DIR"
info "annotator: $ANNOTATOR_DIR"

# ------------------------------------------------------------------------ --down

if [ "$DO_DOWN" -eq 1 ]; then
	step "Stopping both stacks"
	(cd "$ANNOTATOR_DIR" && $ANNOTATOR_DC down) || warn "annotator stack: nothing to stop"
	(cd "$ABAC_DIR" && $ABAC_DC down) || warn "ABAC stack: nothing to stop"
	ok "stopped (databases keep their volumes)"
	exit 0
fi

command -v node >/dev/null || die "node is not installed"
command -v npm >/dev/null || die "npm is not installed"
ok "node $(node -v), npm $(npm -v)"

# A local MySQL on 3306 would collide with the ABAC database.
if port_busy "$ABAC_DB_PORT" && ! docker ps --format '{{.Ports}}' | grep -q "$ABAC_DB_PORT->"; then
	warn "port $ABAC_DB_PORT is already used by something that is not a docker container"
	warn "the ABAC MySQL container will fail to bind — stop that service first"
fi

# ================================================================== 1. ABAC_NII

step "1/2 — ABAC_NII (authorization server)"

# inheritance_service/.env is required and deliberately not committed.
ABAC_ENV="$ABAC_DIR/inheritance_service/.env"
if [ -f "$ABAC_ENV" ]; then
	ok ".env present"
else
	info "creating inheritance_service/.env"
	cat >"$ABAC_ENV" <<EOF
# Created by start-local.sh — local development only.
ENVIRONMENT=local

# Docker service hostnames: 'mysql' and 'opa' resolve inside the compose network.
SQLALCHEMY_DATABASE_URI=mysql+aiomysql://root:123456@mysql:3306/abac_nii
OPA_URL=http://opa:8181/v1/data/policy/allow

# Must match ABAC_SECRET in the annotator's .env.local.
SECRET_KEY=$SHARED_ABAC_SECRET
ALGORITHM=HS256
EOF
	ok "created $ABAC_ENV"
fi

# Only build when we have to. Skipping it on a relaunch is not just faster: it also
# avoids the whole buildx path, which breaks with a stale bind mount after the docker
# daemon (or WSL) restarts under Docker Desktop.
abac_images_exist() {
	docker image inspect abac-inheritance >/dev/null 2>&1 &&
		docker image inspect abac_nii-opa >/dev/null 2>&1
}

if [ "$DO_REBUILD" -eq 1 ]; then
	info "rebuilding the ABAC images from scratch (--rebuild)"
	(cd "$ABAC_DIR" && $ABAC_DC build --no-cache)
	BUILD_FLAG=""
elif abac_images_exist; then
	ok "ABAC images already built (use --rebuild to force)"
	BUILD_FLAG=""
else
	info "building the ABAC images (first run, a few minutes)"
	BUILD_FLAG="--build"
fi

info "starting mysql, opa and inheritance_service"
if ! (cd "$ABAC_DIR" && $ABAC_DC up -d $BUILD_FLAG); then
	warn "compose up failed; if the error mentions buildkit or an invalid bind mount,"
	warn "a stale builder is at fault. Repair it with:"
	warn "  docker rm -f buildx_buildkit_container-builder0"
	die "could not start the ABAC stack"
fi

# MySQL 8 takes over a minute on a cold volume before it accepts connections.
abac_mysql_ready() { (cd "$ABAC_DIR" && $ABAC_DC exec -T mysql mysql -uroot -p123456 -e 'SELECT 1'); }
wait_for "ABAC MySQL" 240 abac_mysql_ready ||
	die "ABAC MySQL never became reachable — check: (cd $ABAC_DIR && $ABAC_DC logs mysql)"

info "ensuring the abac_nii database exists"
(cd "$ABAC_DIR" && $ABAC_DC exec -T mysql \
	mysql -uroot -p123456 -e 'CREATE DATABASE IF NOT EXISTS abac_nii;') 2>/dev/null
ok "database abac_nii ready"

info "applying alembic migrations"
if (cd "$ABAC_DIR" && $ABAC_DC exec -T inheritance_service poetry run alembic upgrade head) >/dev/null 2>&1; then
	ok "migrations applied"
else
	warn "alembic failed — retrying once (the service may still have been booting)"
	sleep 5
	(cd "$ABAC_DIR" && $ABAC_DC exec -T inheritance_service poetry run alembic upgrade head) ||
		die "alembic migrations failed — check: (cd $ABAC_DIR && $ABAC_DC logs inheritance_service)"
	ok "migrations applied"
fi

wait_for "OPA" 60 http_ok "http://localhost:$OPA_PORT/health" ||
	die "OPA is not answering on :$OPA_PORT"
wait_for "inheritance_service" 90 http_ok "http://localhost:$ABAC_PORT/docs" ||
	die "the ABAC service is not answering on :$ABAC_PORT"

# OPA loads its policy once at startup and does not watch the file, so a policy
# edited since the last run is only picked up because we just (re)started it.
ok "ABAC stack up — OPA :$OPA_PORT, service :$ABAC_PORT"

# ============================================================ 2. OntoLearn

step "2/2 — OntoLearn Annotator"

cd "$ANNOTATOR_DIR"

# The committed .env is stale: it declares postgresql://...@db:5432 while the Prisma
# provider is mysql and compose publishes MariaDB on 3307. .env.local overrides it.
if [ -f .env.local ]; then
	ok ".env.local present"
else
	info "creating .env.local"
	cat >.env.local <<EOF
# Created by start-local.sh — local development only.
GITHUB_CLIENT_ID=CLIENT_ID
GITHUB_CLIENT_SECRET=CLIENT_SECRET
NEXTAUTH_URL="http://localhost:$ANNOTATOR_PORT"

# MariaDB from docker-compose.dev.yml, published on $ANNOTATOR_DB_PORT.
# The committed .env still says postgresql://...@db:5432 — that is wrong.
DATABASE_URL="mysql://app:ChangeMe@localhost:$ANNOTATOR_DB_PORT/app"

AUTH_SECRET="local-dev-secret-not-for-production"
EMAIL_SERVER=smtp://localhost:1025
EMAIL_FROM=noreply@example.com

# inheritance_service listens on $ABAC_PORT (the committed .env says 4000).
ABAC_SERVER_URL="http://localhost:$ABAC_PORT"
ABAC_SECRET="$SHARED_ABAC_SECRET"
ABAC_CACHE_TTL=3600
ABAC_CACHE_SIZE_LIMIT=10000

# MinIO from docker-compose.yml, published on $MINIO_PORT.
S3_ENDPOINT="http://localhost:$MINIO_PORT"
S3_BUCKET=ontolearn-storage
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_REGION=us-east-1
S3_FORCE_PATH_STYLE=true
EOF
	ok "created .env.local"
fi

# Load it so the Prisma CLI sees DATABASE_URL (Prisma reads .env, not .env.local).
set -a
# shellcheck disable=SC1091
. ./.env.local
set +a

# A mismatched JWT secret makes every permission check fail with a 403 that looks
# exactly like a policy denial, so check it explicitly.
abac_secret_file=$(sed -n 's/^SECRET_KEY=//p' "$ABAC_ENV" | tail -1)
if [ -n "$abac_secret_file" ] && [ "$abac_secret_file" != "${ABAC_SECRET:-}" ]; then
	warn "ABAC_SECRET (.env.local) != SECRET_KEY ($ABAC_ENV)"
	warn "every authorization call will 403 until these match"
fi

# The annotator's ABAC_SERVER_URL must point at the port the service actually uses.
case "${ABAC_SERVER_URL:-}" in
*":$ABAC_PORT"*) : ;;
*) warn "ABAC_SERVER_URL is ${ABAC_SERVER_URL:-unset} but the service listens on :$ABAC_PORT" ;;
esac

if [ -d node_modules ]; then
	ok "node_modules present"
else
	info "installing npm dependencies (first run, takes a minute)"
	npm install --no-audit --no-fund
	ok "dependencies installed"
fi

# Only 'db' and 'maildev' — a bare 'up -d' would also build the app image from the
# Dockerfile, which is redundant when running the dev server.
info "starting MariaDB,maildev adn MinIO"
$ANNOTATOR_DC up -d db maildev minio

annotator_db_ready() { $ANNOTATOR_DC exec -T db mariadb -uapp -pChangeMe -e 'SELECT 1' app; }
wait_for "MariaDB" 180 annotator_db_ready ||
	die "MariaDB never became reachable — check: $ANNOTATOR_DC logs db"

wait_for "Min_IO" 60 http_ok "http://localhost:$MINIO_PORT/minio/health/live" || 
	die "MinIO never became reachable - check: $ANNOTATOR_DC logs minio"

info "ensuring the ontolearn-storage bucket exists"
docker run --rm --network host \
	-e MC_HOST_local="http://minioadmin:minioadmin@localhost:$MINIO_PORT" \
	"$MINIO_MC_IMAGE" mb --ignore-existing local/ontolearn-storage ||
	die "could not create the MinIO bucket — check MinIO is reachable at :$MINIO_PORT"
ok "bucket ontolearn-storage ready"

info "applying prisma migrations"
npx prisma migrate deploy
npx prisma generate >/dev/null
ok "database schema up to date"

if [ "$DO_SEED" -eq 1 ]; then
	info "seeding the database (--seed)"
	npx prisma db seed
	ok "seeded"
fi

# ------------------------------------------------------------------- summary

step "Stack ready"
printf '    %-22s %s\n' "annotator" "http://localhost:$ANNOTATOR_PORT"
printf '    %-22s %s\n' "ABAC service (docs)" "http://localhost:$ABAC_PORT/docs"
printf '    %-22s %s\n' "OPA" "http://localhost:$OPA_PORT/health"
printf '    %-22s %s\n' "maildev (magic links)" "http://localhost:$MAILDEV_PORT"
printf '    %-22s %s\n' "MinIO console" "http://localhost:$MINIO_CONSOLE_PORT (minioadmin/minioadmin)"
printf '    %-22s %s\n' "annotator DB" "mysql://app:ChangeMe@localhost:$ANNOTATOR_DB_PORT/app"
printf '    %-22s %s\n' "ABAC DB" "mysql://root:123456@localhost:$ABAC_DB_PORT/abac_nii"

if [ "$DO_DEV" -eq 0 ]; then
	printf '\n    backing services only (--no-dev). Start the app with: cd %s && npm run dev\n' "$ANNOTATOR_DIR"
	exit 0
fi

if port_busy "$ANNOTATOR_PORT"; then
	warn "port $ANNOTATOR_PORT is already in use — not starting a second dev server"
	warn "if the running one predates a change to .env.local, restart it: it caches"
	warn "ABAC_SERVER_URL and permission decisions in memory for ABAC_CACHE_TTL seconds"
	exit 0
fi

step "Starting the dev server (Ctrl+C to stop)"
info "Next reads .env.local on its own; the backing services stay up after Ctrl+C."
info "Stop everything with: $0 --down"
exec npm run dev
