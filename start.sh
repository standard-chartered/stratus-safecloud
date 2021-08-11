#!/bin/bash

os=$1

if [[ ! -n "$os" ]];
then
  os="linux"
  SSC_HOME=/home/$USER/Workspace/ssc
else
  SSC_HOME=/Users/$USER/Workspace/ssc
fi

source "$SSC_HOME/venv/bin/activate"
set -x

if [[ x$PORT == x ]]; then {
    PORT=5000
} fi

echo using port: $PORT
export PYTHONPATH=$SSC_HOME
nohup $SSC_HOME/venv/bin/python $SSC_HOME/app.py > ssc.nohup & echo $! > ssc.pid

