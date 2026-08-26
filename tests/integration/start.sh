#!/bin/bash
set -e
# cd in the script folder
cd "$(dirname "$0")"

# Check if we are in the right folder
if [ ! -f ".v039fk_lnbits_integration_test_folder" ]; then
    echo "Please run this script from the tests/integration folder"
    exit 1
fi

# Double check if we are in the right folder
if [ "`cat .v039fk_lnbits_integration_test_folder`" != "yes v039fk_lnbits_integration_test_folder" ]; then
    echo "Please run this script from the tests/integration folder!"
    exit 1
fi

# Start nostr Relay. The image defaults to the `strfry` user (UID 1000),
# which is not necessarily the user running the CI job. Create the bind mount
# first and run the relay as the current user so LMDB can initialize its files.
id=$(id -u)
gid=$(id -g)
mkdir -p strfry-data
docker run --name=lnbits_nwcprovider_ext_nostr_test \
-d \
--rm \
--user $id:$gid \
-v $PWD/strfry.conf:/etc/strfry.conf:Z \
-v $PWD/strfry-data:/app/strfry-db:Z \
-p 7777:7777 \
ghcr.io/hoytech/strfry:latest

# Start lnbits with the nwcprovider extension
rm -Rf lnbits_itest_data
unzip data.zip

# The fixture was created with the standalone tpos extension installed. tpos
# is no longer part of the LNbits dev tree, so leaving its database metadata in
# the fixture makes current LNbits attempt to import a module that is absent.
# The integration suite only exercises nwcprovider.
python3 - <<'PY'
import sqlite3

with sqlite3.connect("lnbits_itest_data/database.sqlite3") as conn:
    conn.execute("DELETE FROM installed_extensions WHERE id = 'tpos'")
    conn.execute("DELETE FROM dbversions WHERE db = 'tpos'")
PY
rm -f lnbits_itest_data/ext_tpos.sqlite3 lnbits_itest_data/zips/tpos.zip

docker run --name=lnbits_nwcprovider_ext_lnbits_test \
-d \
--rm \
--user $id:$gid \
-p 5002:5000 \
-v ${PWD}/.env:/app/.env \
-v ${PWD}/lnbits_itest_data/:/data \
-v ${PWD}/../../:/nwcprovider \
-v ${PWD}/../../.devcontainer/start.sh:/start-lnbits.sh:ro \
-v ${PWD}/../../.devcontainer/setup.sh:/setup.sh:ro \
-v ${PWD}/../../.devcontainer/pre-setup.sh:/pre-setup.sh:ro \
mcr.microsoft.com/devcontainers/python:1-3.12 bash -c "while true; do sleep 1000; done"

if ! docker network inspect lnbits_nwcprovider_ext_test_network >/dev/null 2>&1; then
    docker network create lnbits_nwcprovider_ext_test_network
fi
docker network connect lnbits_nwcprovider_ext_test_network lnbits_nwcprovider_ext_nostr_test --alias nostr
docker network connect lnbits_nwcprovider_ext_test_network lnbits_nwcprovider_ext_lnbits_test --alias lnbits

docker exec -u root lnbits_nwcprovider_ext_lnbits_test bash -c "id -u $id &>/dev/null || useradd -m -u $id tester"
docker exec -u root lnbits_nwcprovider_ext_lnbits_test bash -c "bash /pre-setup.sh"
docker exec --user $id:$gid lnbits_nwcprovider_ext_lnbits_test  bash -c "curl -sSL https://install.python-poetry.org | python3 -"

docker exec --user $id:$gid lnbits_nwcprovider_ext_lnbits_test bash -c "export PATH=\"\$HOME/.local/bin:\$PATH\" && bash /setup.sh /nwcprovider"
docker exec --user $id:$gid lnbits_nwcprovider_ext_lnbits_test bash -c "ln -s /app/.env \$HOME/lnbits/.env"


if [ "$HEADLESS" != "" ];
then
    # Keep the server log inside the container so a failed health check can
    # show the actual startup error instead of silently swallowing it.
    docker exec --user $id:$gid -d lnbits_nwcprovider_ext_lnbits_test bash -c "export PATH=\"\$HOME/.local/bin:\$PATH\" && cd \$HOME/lnbits && poetry run lnbits > /tmp/lnbits.log 2>&1"

    wait_for_http() {
        local service="$1"
        local url="$2"
        local timeout_seconds="$3"
        local deadline=$((SECONDS + timeout_seconds))

        until curl --fail --silent --show-error --max-time 2 "$url" >/dev/null 2>&1; do
            if [ "$SECONDS" -ge "$deadline" ]; then
                echo "Timed out waiting for $service at $url" >&2
                docker ps -a >&2
                if [ "$service" = "LNbits" ]; then
                    docker exec lnbits_nwcprovider_ext_lnbits_test tail -n 100 /tmp/lnbits.log >&2 || true
                else
                    docker logs --tail 100 lnbits_nwcprovider_ext_nostr_test >&2 || true
                fi
                return 1
            fi
            sleep 1
        done
    }

    # LNbits may need a few minutes for a fresh database migration.
    wait_for_http "nostr relay" "http://localhost:7777" 180
    wait_for_http "LNbits" "http://localhost:5002" 180
else
    docker exec --user $id:$gid lnbits_nwcprovider_ext_lnbits_test bash -c "export PATH=\"\$HOME/.local/bin:\$PATH\" && cd \$HOME/lnbits && poetry run lnbits"
fi
