#!/bin/bash

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
-p 5002:5000 \
-v ${PWD}/.env:/app/.env \
-v ${PWD}/lnbits_itest_data/:/app/data \
-v ${PWD}/../../:/app/lnbits/extensions/nwcprovider:ro \
lnbits/lnbits


docker network create lnbits_nwcprovider_ext_test_network || true
docker network connect lnbits_nwcprovider_ext_test_network lnbits_nwcprovider_ext_nostr_test --alias nostr|| true
docker network connect lnbits_nwcprovider_ext_test_network lnbits_nwcprovider_ext_lnbits_test --alias lnbits|| true


