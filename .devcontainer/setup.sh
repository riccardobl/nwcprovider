#!/bin/bash
echo $PYTHONPATH
CONTAINER_WORKSPACE_FOLDER=$1
cd $CONTAINER_WORKSPACE_FOLDER

# workaround for devimage
sudo find /etc/apt/sources.list.d -maxdepth 1 -type f -exec \
    sh -c 'grep -q "dl.yarnpkg.com/debian" "$1" && rm -f "$1" || true' _ {} \;
sudo sed -i '/dl.yarnpkg.com\/debian/d' /etc/apt/sources.list || true

cd $HOME
echo $PWD
if [ ! -d ./lnbits ] ; then
    git clone https://github.com/lnbits/lnbits.git lnbits
fi
cd lnbits
echo $PWD
git checkout dev
poetry env use 3.12
POETRY_PYTHON_PATH=$(poetry env info -p)/bin/python
ln -sf $POETRY_PYTHON_PATH /home/vscode/python
make bundle
poetry install --no-interaction
mkdir -p lnbits/extensions/
if [ ! -d lnbits/extensions/nwcprovider ] ; then
    ln -s $CONTAINER_WORKSPACE_FOLDER lnbits/extensions/nwcprovider
fi

cd $CONTAINER_WORKSPACE_FOLDER
poetry install --no-interaction
npm i prettier
npm i pyright
pip install uv
