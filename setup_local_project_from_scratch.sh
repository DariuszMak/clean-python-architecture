#!/bin/bash

rm -r -f ./venv

python -m pip install --upgrade pip
python -m pip install virtualenv
python -m virtualenv venv

source ./venv/bin/activate

python -m pip install -r requirements.txt
