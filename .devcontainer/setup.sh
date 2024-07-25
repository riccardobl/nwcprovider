#!/bin/bash
CONTAINER_WORKSPACE_FOLDER=$1
sudo apt update -y
sudo apt install -y python3.9-distutils curl
sudo apt-get install -y docker.io

curl -fsSL https://deb.nodesource.com/setup_20.x -o /tmp/nodesource_setup.sh
sudo bash /tmp/nodesource_setup.sh
sudo apt-get install -y nodejs
if [ ! -d lnbits ] ; then 
    sudo git clone https://github.com/lnbits/lnbits.git; 
fi 
sudo chown 1000:1000 -Rvf lnbits 
cd lnbits
git checkout 0.12.8 
poetry env use python3.9
VENV_PATH=$(poetry env info -p)
sudo ln -s $VENV_PATH /opt/python
make bundle
poetry install --no-interaction 
mkdir -p lnbits/extensions/ 
if [ ! -d lnbits/extensions/nwcprovider ] ; then 
    ln -s $CONTAINER_WORKSPACE_FOLDER lnbits/extensions/nwcprovider
fi


