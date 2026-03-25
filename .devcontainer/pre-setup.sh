#!/bin/bash
set -e

# workaround for devimage
sudo find /etc/apt/sources.list.d -maxdepth 1 -type f -exec \
	sh -c 'grep -q "dl.yarnpkg.com/debian" "$1" && rm -f "$1" || true' _ {} \;
sudo sed -i '/dl.yarnpkg.com\/debian/d' /etc/apt/sources.list || true

sudo apt update -y
sudo apt install -y curl
sudo apt-get install -y docker.io

curl -sSL https://install.python-poetry.org | python3 -
curl -fsSL https://deb.nodesource.com/setup_20.x -o /tmp/nodesource_setup.sh
sudo bash /tmp/nodesource_setup.sh
sudo apt-get install -y nodejs
