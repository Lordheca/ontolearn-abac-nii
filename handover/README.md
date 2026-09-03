# OntoLearn Annotator - handover kit

Everything here that belongs in a repository is committed on the annotator's `main`
branch; this archive is a convenience copy plus the two things that live nowhere else.

| Where the real thing lives | |
|---|---|
| Annotator | `https://github.com/mboultoureau/ontolearn-annotator.git`, branch `main` |
| ABAC server | Zenodo record `18412324`, linked from the annotator's README - distributed as a zip, not a git repo |
| `TODO.md`, both workflow YAMLs | committed in the annotator repo |
| `abac/policy.rego` and `scripts/*.sh` | **only here** - ABAC_NII is not under version control and the scripts sit outside both repos |

Put those last two under version control early.

## Start it

```bash
./scripts/init-local.sh      # fresh machine: fetches both halves, then starts everything
./scripts/start-local.sh     # already cloned: just start
```

Then:

| | |
|---|---|
| Annotator | http://localhost:3000 |
| ABAC service (OpenAPI) | http://localhost:5004/docs |
| OPA health | http://localhost:8181/health |
| maildev - sign-in magic links land here | http://localhost:1080 |
| Annotator DB (MariaDB) | `mysql://app:ChangeMe@localhost:3307/app` |
| ABAC DB (MySQL) | `mysql://root:123456@localhost:3306/abac_nii` |

`start-local.sh` also takes `--seed` (first run), `--no-dev` (services only) and `--down`
(stop both stacks, volumes kept).

**ABAC has to be up first.** The annotator fails *closed* on authorization, so an
unreachable ABAC server looks exactly like "permission denied" everywhere in the UI.

Sign in with the email provider and pick up the link in maildev - no SMTP needed.

## Contents

- **`scripts/start-local.sh`** - starts ABAC_NII then the annotator. Tested from cold.
- **`scripts/init-local.sh`** - clones the annotator, fetches ABAC_NII (local zip, git
  remote, or the Zenodo download), then hands off to `start-local.sh`. The clone and the
  Zenodo download are the one path never executed here, so validate them first;
  everything else in the script was tested against a fabricated archive.
- **`abac/policy.rego`** - the real policy: `ADMIN` may do anything in its project,
  `USER` may read and list everything plus write on `task` and `playground`, default deny.
  The Zenodo archive ships a *demo* policy instead (`role == "employee"`, matching
  `department`, a `Device_1` attribute) which the annotator's roles can never satisfy, so
  a fresh install denies everything and every project page 404s. `init-local.sh` detects
  and replaces it.
- **`abac/inheritance_service.env.example`** - copy to
  `ABAC_NII/inheritance_service/.env` (required, not shipped). `SECRET_KEY` must be
  byte-identical to the annotator's `ABAC_SECRET` or every check returns 403 in a way
  that reads as a policy denial.
- **`workflows/water-crystal-annotation.yaml`** - the annotation workflow, 7 states.
- **`workflows/node-coverage-test.yaml`** - exercises all eight node types in one pass;
  useful as a smoke test after touching the engine.

Both workflows are stored per project as a YAML string in
`Configuration.settings.workflow` and edited at `/projects/{slug}/settings/annotations`.

## Secrets in this archive

`scripts/start-local.sh` carries two **local-development** defaults in plain text:
`AUTH_SECRET=local-dev-secret-not-for-production` and
`SHARED_ABAC_SECRET=local-dev-abac-secret`. They are deliberate - the annotator and the
ABAC service must sign and verify the same JWT - and they are not credentials to anything
real, but they must not survive into a deployed environment. Override with
`SHARED_ABAC_SECRET=... ./scripts/start-local.sh` and generate real values
(`openssl rand -base64 32`) for anything beyond a laptop.
