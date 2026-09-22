#!/usr/bin/env bash
set -euo pipefail

PACKAGE=${1:?usage: docker_test.sh <app package .tar.gz> <sample log> [sourcetype]}
FIXTURE=${2:?usage: docker_test.sh <app package .tar.gz> <sample log> [sourcetype]}
SOURCETYPE=${3:-custom_access_combined}
IMAGE=${SPLUNK_IMAGE:-splunk/splunk:9.4}
PASSWORD=${SPLUNK_PASSWORD:-Cicd-Test-Passw0rd}
NAME=${CONTAINER_NAME:-splunk-cicd-test}
FIELDS=${REQUIRED_FIELDS:-clientip ident user req_time method uri_path bytes referer useragent coockie}
TIMEOUT=${STARTUP_TIMEOUT:-600}

PACKAGE=$(realpath "$PACKAGE")
FIXTURE=$(realpath "$FIXTURE")
cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

echo "==> starting $IMAGE with $(basename "$PACKAGE")"
docker run -d --name "$NAME" \
  -e SPLUNK_START_ARGS=--accept-license \
  -e SPLUNK_PASSWORD="$PASSWORD" \
  -e SPLUNK_APPS_URL="/tmp/pkg/$(basename "$PACKAGE")" \
  -v "$PACKAGE:/tmp/pkg/$(basename "$PACKAGE"):ro" \
  -v "$FIXTURE:/tmp/fixtures/sample.log:ro" \
  "$IMAGE" >/dev/null

echo "==> waiting for the container to be healthy"
elapsed=0
until [ "$(docker inspect -f '{{.State.Health.Status}}' "$NAME")" = "healthy" ]; do
  if [ "$(docker inspect -f '{{.State.Status}}' "$NAME")" != "running" ] || [ "$elapsed" -ge "$TIMEOUT" ]; then
    docker logs "$NAME" | tail -50
    echo "Splunk container did not become healthy"
    exit 1
  fi
  sleep 10; elapsed=$((elapsed + 10))
done

splunk() { docker exec "$NAME" sudo -u splunk /opt/splunk/bin/splunk "$@"; }

echo "==> btool check"
splunk btool check --debug 2>&1 | grep -v '^$' | tail -20

echo "==> ingesting sample"
splunk add oneshot /tmp/fixtures/sample.log -sourcetype "$SOURCETYPE" -index main -auth "admin:$PASSWORD"

search_count() {
  splunk search "$1 | stats count" -auth "admin:$PASSWORD" -output csv 2>/dev/null | tail -1 | tr -dc '0-9'
}

echo "==> waiting for events"
count=0
for _ in $(seq 1 30); do
  count=$(search_count "index=main sourcetype=$SOURCETYPE earliest=0")
  [ "${count:-0}" -gt 0 ] && break
  sleep 5
done
[ "${count:-0}" -gt 0 ] || { echo "no events indexed"; exit 1; }
echo "indexed events: $count"

filter=""
for f in $FIELDS; do filter="$filter $f=*"; done
extracted=$(search_count "index=main sourcetype=$SOURCETYPE earliest=0 $filter")
echo "events with all required fields: ${extracted:-0}/$count"
[ "${extracted:-0}" -eq "$count" ] || { echo "field extraction check failed"; exit 1; }
echo "==> OK"
