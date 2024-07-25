#!/bin/bash
ln -s $PWD/.devcontainer/.env ./lnbits/.env
cd ./lnbits
poetry run lnbits
