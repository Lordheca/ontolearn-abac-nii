#!/usr/bin/env bash
#
# Fetch both halves of the OntoLearn Annotator stack into an empty working directory,
# then hand off to start-local.sh.
#
#   - the annotator itself: cloned from GitHub
#   - ABAC_NII (the authorization server it delegates to): NOT a git repository —
#     it is distributed as a zip, so it comes from one of three sources, see below.
#
# Usage:
#   ./init-local.sh                          # clone annotator + download ABAC from Zenodo
#   ./init-local.sh --abac-zip ~/dl/abac.zip # ...or take ABAC from a zip you already have
#   ./init-local.sh --abac-git <url>         # ...or from a git remote, if it ever gets one
#   ./init-local.sh --branch some-branch     # annotator branch (default: main)
#   ./init-local.sh --dir ~/work             # target directory (default: this script's directory)
#   ./init-local.sh --no-start               # fetch only, don't launch the stack
#   ./init-local.sh --force                  # re-fetch over existing directories (destructive)
#
# Existing directories are left alone unless --force is passed.

set -euo pipefail

# ----------------------------------------------------------------- configuration

TARGET_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ANNOTATOR_REPO="${ANNOTATOR_REPO:-https://github.com/mboultoureau/ontolearn-annotator.git}"
ANNOTATOR_BRANCH="main"
ANNOTATOR_NAME="ontolearn-annotator"
ABAC_NAME="ABAC_NII"

# The annotator's README points at this Zenodo record for the ABAC server. The token is
# part of the published link (it is a restricted-record share token, not a credential of
# ours) and is only ever sent to zenodo.org.
ZENODO_RECORD="${ZENODO_RECORD:-18412324}"
ZENODO_TOKEN="${ZENODO_TOKEN:-eyJhbGciOiJIUzUxMiJ9.eyJpZCI6IjgwYWRiYmFjLTgwZTUtNDNmZS1hMjMzLWZhZWUxYTU0ODU3YSIsImRhdGEiOnt9LCJyYW5kb20iOiI3YzFiOTFiNjlkOWU2Yjc1MTY5OTU4YzFlMWI2N2RmZiJ9.J4-qW_ubrfn151UU3CsbwmrAmygVePr0sDYZcoUkkbnSKHqUwHH6N3bk2WXq-ZaL58Ws2fYodGJz_tnSI3IV6A}"

ABAC_ZIP=""
ABAC_GIT=""
DO_START=1
FORCE=0

while [ $# -gt 0 ]; do
	case "$1" in
	--dir)
		TARGET_DIR="$2"
		shift 2
		;;
	--branch)
		ANNOTATOR_BRANCH="$2"
		shift 2
		;;
	--abac-zip)
		ABAC_ZIP="$2"
		shift 2
		;;
	--abac-git)
		ABAC_GIT="$2"
		shift 2
		;;
	--zenodo-record)
		ZENODO_RECORD="$2"
		shift 2
		;;
	--zenodo-token)
		ZENODO_TOKEN="$2"
		shift 2
		;;
	--no-start)
		DO_START=0
		shift
		;;
	--force)
		FORCE=1
		shift
		;;
	-h | --help)
		sed -n '3,22p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
		exit 0
		;;
	*)
		echo "Unknown option: $1 (try --help)" >&2
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

# Refuse to touch a directory that already has content, unless --force.
claim_dir() {
	local dir="$1" label="$2"
	if [ -e "$dir" ]; then
		if [ "$FORCE" -eq 1 ]; then
			warn "removing existing $label ($dir) — --force"
			rm -rf "$dir"
		else
			ok "$label already present, leaving it alone ($dir)"
			return 1
		fi
	fi
	return 0
}

# ------------------------------------------------------------------- preflight

step "Preflight"

command -v git >/dev/null || die "git is not installed"
command -v curl >/dev/null || die "curl is not installed"
command -v unzip >/dev/null || die "unzip is not installed (apt install unzip)"
ok "git, curl, unzip available"

mkdir -p "$TARGET_DIR"
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
info "target directory: $TARGET_DIR"

ANNOTATOR_DIR="$TARGET_DIR/$ANNOTATOR_NAME"
ABAC_DIR="$TARGET_DIR/$ABAC_NAME"

# ========================================================== 1. annotator (git)

step "1/3 — OntoLearn Annotator"

if claim_dir "$ANNOTATOR_DIR" "annotator"; then
	info "cloning $ANNOTATOR_REPO (branch $ANNOTATOR_BRANCH)"
	if ! git clone --branch "$ANNOTATOR_BRANCH" "$ANNOTATOR_REPO" "$ANNOTATOR_DIR"; then
		warn "clone of branch '$ANNOTATOR_BRANCH' failed — retrying with the default branch"
		git clone "$ANNOTATOR_REPO" "$ANNOTATOR_DIR" ||
			die "could not clone $ANNOTATOR_REPO"
	fi
	ok "cloned into $ANNOTATOR_DIR"
	info "branch: $(git -C "$ANNOTATOR_DIR" rev-parse --abbrev-ref HEAD)"
fi

# =============================================================== 2. ABAC_NII

step "2/3 — ABAC_NII (authorization server)"

extract_abac_zip() {
	local zip="$1" tmp
	[ -f "$zip" ] || die "zip not found: $zip"
	tmp="$(mktemp -d)"
	# shellcheck disable=SC2064
	trap "rm -rf '$tmp'" RETURN

	info "extracting $(basename "$zip")"
	unzip -q "$zip" -d "$tmp" || die "could not unzip $zip"

	# The archive may wrap everything in a single top-level directory; flatten it.
	local entries count src
	# shellcheck disable=SC2012
	count=$(ls -A "$tmp" | wc -l)
	if [ "$count" -eq 1 ] && [ -d "$tmp/$(ls -A "$tmp")" ]; then
		entries=$(ls -A "$tmp")
		src="$tmp/$entries"
	else
		src="$tmp"
	fi

	mkdir -p "$ABAC_DIR"
	# shellcheck disable=SC2086
	(cd "$src" && tar cf - .) | (cd "$ABAC_DIR" && tar xf -)
	ok "extracted into $ABAC_DIR"
}

if claim_dir "$ABAC_DIR" "ABAC_NII"; then
	if [ -n "$ABAC_GIT" ]; then
		info "cloning $ABAC_GIT"
		git clone "$ABAC_GIT" "$ABAC_DIR" || die "could not clone $ABAC_GIT"
		ok "cloned into $ABAC_DIR"

	elif [ -n "$ABAC_ZIP" ]; then
		extract_abac_zip "$ABAC_ZIP"

	else
		info "downloading from Zenodo record $ZENODO_RECORD"
		tmpzip="$(mktemp -d)/abac.zip"
		api="https://zenodo.org/api/records/$ZENODO_RECORD?token=$ZENODO_TOKEN"

		# Ask the API which file to take, so we do not hardcode a version-specific name.
		filename="$(curl -sf -m 120 "$api" |
			tr ',' '\n' | grep -o '"key"[[:space:]]*:[[:space:]]*"[^"]*\.zip"' |
			head -1 | sed 's/.*"\([^"]*\.zip\)"/\1/')" || true

		if [ -z "$filename" ]; then
			warn "could not read the file list from the Zenodo API"
			warn "the record may need a fresh share token, or the API shape changed"
			die "fetch ABAC_NII manually and re-run with: $0 --abac-zip /path/to/abac.zip"
		fi
		info "record file: $filename"

		url="https://zenodo.org/records/$ZENODO_RECORD/files/$filename?download=1&token=$ZENODO_TOKEN"
		curl -fL -m 900 --retry 2 -o "$tmpzip" "$url" ||
			die "download failed — re-run with: $0 --abac-zip /path/to/abac.zip"
		ok "downloaded $(du -h "$tmpzip" | cut -f1)"
		extract_abac_zip "$tmpzip"
	fi
fi

# The zip is produced on Windows, so it carries a ':Zone.Identifier' sidecar next to
# every file. They are inert but they clutter every listing and grep.
zone_count=$(find "$ABAC_DIR" -name '*:Zone.Identifier' 2>/dev/null | wc -l)
if [ "$zone_count" -gt 0 ]; then
	find "$ABAC_DIR" -name '*:Zone.Identifier' -delete
	ok "removed $zone_count Windows ':Zone.Identifier' sidecar files"
fi

# Sanity-check the tree rather than trusting the archive layout.
for required in docker-compose.yml opa/policy.rego inheritance_service/pyproject.toml; do
	[ -e "$ABAC_DIR/$required" ] ||
		die "ABAC_NII looks incomplete: $required is missing from $ABAC_DIR"
done
ok "ABAC_NII tree looks complete"

if [ ! -d "$ABAC_DIR/.git" ]; then
	warn "ABAC_NII is not under version control — consider 'git init' so local"
	warn "changes to opa/policy.rego are not one 'rm -rf' from being lost"
fi

# ======================================================== 3. working OPA policy

step "3/3 — OPA policy"

POLICY="$ABAC_DIR/opa/policy.rego"

# The distributed archive ships a DEMO policy that requires subject.role == "employee",
# a matching department and a Device_1 attribute. The annotator only ever sends roles
# ADMIN or USER, so that policy denies every single request and the whole UI 404s. A
# fresh install is therefore broken until this is replaced.
if grep -q '"employee"' "$POLICY" 2>/dev/null; then
	info "demo policy detected (denies every annotator request) — installing the role policy"
	cp "$POLICY" "$ABAC_DIR/opa/policy.demo.rego.bak"

	cat >"$POLICY" <<'REGO'
package policy

# Authorization policy for the OntoLearn Annotator.
#
# Input contract (built by inheritance_service/main/libs/access_lib/access_decision_lib.py
# from the annotator's request in ontolearn-annotator/src/lib/abac-client.ts):
#
#   {
#     "subject":      {"id": <userId>, "role": "ADMIN" | "USER", "email": <string>},
#     "resource":     {"id": <projectId>, "type": <resource type, see below>},
#     "action":       {"name": "read" | "write" | "delete" | "list" | "invite" | "edit"},
#     "environments": {<env function name>: [<values>]}
#   }
#
# `subject.role` is the caller's Role in THIS project, read from the annotator's
# ProjectMember table (Prisma enum Role: ADMIN | USER). The annotator already denies
# non-members before calling here, so a request reaching this policy always comes from
# a member of resource.id — this policy decides what that member may do, not whether
# they belong.
#
# Resource types and actions in use (ontolearn-annotator/src/lib/abac-action-categories.ts):
#   settings    read, write
#   data        read, write, delete
#   task        read, write
#   playground  read, write
#   project     read, write, delete
#   statistics  read
#   user        list, invite, delete, edit
#   sourceType  list

# Deny by default: an unknown role, resource type or action is refused.
default allow := false

# A project ADMIN has full control over that project.
allow if {
	input.subject.role == "ADMIN"
}

# A USER may read and list everything in a project they belong to.
allow if {
	input.subject.role == "USER"
	input.action.name in {"read", "list"}
}

# A USER may also do the annotation work itself: complete tasks and use the playground.
allow if {
	input.subject.role == "USER"
	input.resource.type in {"task", "playground"}
	input.action.name == "write"
}
REGO
	ok "installed the ADMIN/USER role policy (demo kept as opa/policy.demo.rego.bak)"
else
	ok "policy is not the shipped demo — leaving it untouched"
fi

# --------------------------------------------------------------------- handoff

step "Ready to launch"
info "annotator: $ANNOTATOR_DIR"
info "ABAC_NII:  $ABAC_DIR"

START_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/start-local.sh"
if [ ! -x "$START_SCRIPT" ]; then
	warn "start-local.sh not found next to this script — start the stack manually"
	exit 0
fi

if [ "$DO_START" -eq 0 ]; then
	info "fetch only (--no-start). Launch with:"
	info "  ABAC_DIR=$ABAC_DIR ANNOTATOR_DIR=$ANNOTATOR_DIR $START_SCRIPT --seed"
	exit 0
fi

# A fresh clone has an empty database, so seed it on the first launch.
info "handing off to start-local.sh (with --seed, this is a fresh install)"
exec env ABAC_DIR="$ABAC_DIR" ANNOTATOR_DIR="$ANNOTATOR_DIR" "$START_SCRIPT" --seed
