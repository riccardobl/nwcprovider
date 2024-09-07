#!/bin/bash
ln -s $PWD/.devcontainer/.env $HOME/lnbits/.env
cd $HOME/lnbits
poetry run lnbits
