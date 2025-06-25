#!/bin/bash
set -e

sudo apt update -y
sudo apt install -y curl
sudo apt-get install -y docker.io

curl -sSL https://install.python-poetry.org | python3 -
curl -fsSL https://deb.nodesource.com/setup_20.x -o /tmp/nodesource_setup.sh
sudo bash /tmp/nodesource_setup.sh
sudo apt-get install -y nodejs
