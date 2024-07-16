#!/bin/bash
if [ ! -f ".devcontainer/.env" ]; then
  cp .devcontainer/.env.example .devcontainer/.env
fi
ln -s $PWD/.devcontainer/.env ../lnbits/.env
cd ../lnbits
poetry run lnbits
