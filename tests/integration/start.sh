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

# Start nostr Relay
docker run --name=lnbits_nwcprovider_ext_nostr_test \
-d \
--rm \
-v $PWD/strfry.conf:/etc/strfry.conf \
-v $PWD/strfry-data:/app/strfry-db \
-p 7777:7777 \
ghcr.io/hoytech/strfry:latest

# Start lnbits with the nwcprovider extension
rm -Rf lnbits_itest_data
unzip data.zip

docker run --name=lnbits_nwcprovider_ext_lnbits_test \
-d \
--rm \
--user $(id -u):$(id -g) \
-p 5002:5000 \
-v ${PWD}/.env:/app/.env \
-v ${PWD}/lnbits_itest_data/:/data \
-v ${PWD}/../../:/nwcprovider \
-v ${PWD}/../../.devcontainer/start.sh:/start-lnbits.sh:ro \
-v ${PWD}/../../.devcontainer/setup.sh:/setup.sh:ro \
mcr.microsoft.com/devcontainers/python:1-3.12 bash -c "while true; do sleep 1000; done"

docker network create lnbits_nwcprovider_ext_test_network || true
docker network connect lnbits_nwcprovider_ext_test_network lnbits_nwcprovider_ext_nostr_test --alias nostr|| true
docker network connect lnbits_nwcprovider_ext_test_network lnbits_nwcprovider_ext_lnbits_test --alias lnbits|| true

docker exec lnbits_nwcprovider_ext_lnbits_test  bash -c "curl -sSL https://install.python-poetry.org | python3 -"

set +e
docker exec lnbits_nwcprovider_ext_lnbits_test bash -c "export PATH=\"/home/vscode/.local/bin:\$PATH\" && bash /setup.sh /nwcprovider"
docker exec lnbits_nwcprovider_ext_lnbits_test bash -c "ln -s /app/.env \$HOME/lnbits/.env"
docker exec lnbits_nwcprovider_ext_lnbits_test bash -c "export PATH=\"/home/vscode/.local/bin:\$PATH\" && cd \$HOME/lnbits && poetry run lnbits"
 
