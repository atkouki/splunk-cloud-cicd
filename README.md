# Splunk Cloud CI/CD

Package, vet and deploy Splunk apps to Splunk Cloud Platform from a Git pipeline, using AppInspect and the Admin Config Service (ACS). The unit of deployment is an immutable app package: built once, vetted, then promoted from `dev` to `staging` to `prod`.

```
package  →  AppInspect CLI (cloud + private_*)  →  docker test (optional)
         →  AppInspect API vetting  →  ACS install / upgrade  →  verify  →  next environment
```

## Repository layout

| Path | Role |
|---|---|
| `apps/testing_app/` | The Splunk app under source control (one directory per app, directory name = `[package] id`) |
| `fixtures/access_combined.sample.log` | Sample events used by the docker integration test |
| `cicd/` | `splunk-cicd` Python package (CLI + unit tests) and `scripts/docker_test.sh` |
| `envs/*.yml` | One file per target environment: stack, experience, indexes, options |
| `.github/workflows/` | `ci.yml` (PR + main), `release.yml` (tags `v*`), `deploy.yml` (reusable + manual) |
| `.gitlab-ci.yml` | GitLab mirror of the same flow |

## Prerequisites

1. **A splunk.com account** (username, not e-mail, no SSO) for the AppInspect API. Secrets `SPLUNKCOM_USER` and `SPLUNKCOM_PASSWORD`.
2. **An ACS token per stack**: Splunk Web, Settings, Tokens, or `POST /{stack}/adminconfig/v2/tokens` with basic auth. Secret `ACS_TOKEN`, scoped per environment (GitHub Environments or GitLab environment-scoped variables). The token user needs the `sc_admin` role.
3. **Environment files** in `envs/`: set `stack` to the stack prefix (`mystack`, `mystack.stg` for staging stacks, which switches ACS to `staging.admin.splunk.com`). Override the ACS host with `acs_server` or the `ACS_SERVER` variable (FedRAMP: `https://admin.splunkcloudgc.com`).
4. GitHub: create the `dev`, `staging` and `prod` Environments and add required reviewers on `staging` and `prod`. Set the repository variable `ENABLE_DOCKER_TEST=true` to run the docker job.

`envs/<name>.yml` reference:

| Key | Default | Meaning |
|---|---|---|
| `stack` | required | Stack prefix, `.stg` suffix marks a staging stack |
| `app` | required | App id expected on the stack |
| `experience` | `auto` | `auto` asks ACS `/status`, else `victoria` or `classic` |
| `acs_server` | derived | ACS base URL override |
| `search_head` | empty | Search head prefix used for Victoria exports (`sh-i-xxx`) |
| `indexes` | `[]` | Indexes to create or update through ACS before install (`name`, `datatype`, `searchableDays`, `maxDataSizeMB`, `splunkArchivalRetentionDays`, `selfStorageBucketPath`) |
| `inspect_tags` | `private_<experience>` | AppInspect API tags |
| `allow_manual_checks` | `false` | Accept manual checks in the vetting report |
| `install_timeout` | `900` | Seconds to wait for the app to reach `installed` |
| `backup_before_install` | `true` | Export the current app before upgrading (Victoria only) |
| `require_backup` | `false` | Fail the deployment when the export fails |

## Local usage

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e "cicd[dev]" splunk-appinspect
pytest cicd/tests
splunk-cicd package --app apps/testing_app --out dist --list
splunk-cicd inspect-local --package 'dist/*.tar.gz'
```

Against a real stack:

```bash
export ACS_TOKEN=... SPLUNKCOM_USER=... SPLUNKCOM_PASSWORD=...
splunk-cicd acs status --env envs/dev.yml
splunk-cicd acs indexes --env envs/dev.yml
splunk-cicd deploy --env envs/dev.yml --package 'dist/*.tar.gz' --report reports/deploy-dev.json
splunk-cicd verify --env envs/dev.yml --version 1.0.0
```

`deploy` runs, in order: stack status and experience detection, index reconciliation, export of the installed version to `backups/` (Victoria), AppInspect API vetting with `private_victoria` or `private_classic`, ACS install (bounded retries on 424/429/503), polling until `installed`, version verification. The JSON report lists every step.

Other commands: `splunk-cicd acs apps|install|uninstall|export|deployment`, `splunk-cicd inspect-api`, `splunk-cicd rollback --env ... --package backups/<previous>.tar.gz`.

## Releasing

1. Bump `version` in `apps/testing_app/default/app.conf` (`[launcher]` and `[id]`).
2. Merge to `main`, then tag `vX.Y.Z`. The tag must equal the app version or the package step fails.
3. The Release workflow builds and vets once, deploys to `dev`, then waits for the `staging` and `prod` approvals.

Rollback: re-run the Deploy workflow (`workflow_dispatch`) with the previous release run id, or locally `splunk-cicd rollback` with the package saved under `backups/` or `dist/` of the previous release.

## Docker integration test

`cicd/scripts/docker_test.sh <package> <sample log> [sourcetype]` starts `splunk/splunk:9.4` with the package as `SPLUNK_APPS_URL`, runs `btool check`, ingests the sample with `add oneshot` and asserts that every event carries the fields extracted by `props.conf`. It needs a runner with docker.

## What is not covered

- Apps with Python in `bin/` or other manual-review checks are not self-service on Splunk Cloud: expect a Splunk review, or set `allow_manual_checks` knowingly.
- Splunkbase apps: use `acs apps` or the ACS CLI, this pipeline only handles private apps.
- Upgrading a private app on Victoria re-posts the package; confirm on your stack that ACS treats it as an upgrade rather than requiring an uninstall first.
