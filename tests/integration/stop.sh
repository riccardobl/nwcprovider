#!/bin/bash
docker stop lnbits_nwcprovider_ext_nostr_test || true
docker stop lnbits_nwcprovider_ext_lnbits_test || true

# Remove lnbits_nwcprovider_ext_test_network network
docker network rm lnbits_nwcprovider_ext_test_network || true