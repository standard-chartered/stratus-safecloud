#!/bin/bash

if [ -f ./vamp.pid ]; then
    PID=$(cat ./vamp.pid)
else
    PID=$(ps -ef | awk '/venv\/bin\/python/{ print $2 }')
fi

echo "Killing $PID"
kill $PID

if [ -f ./vamp.pid ]; then
    rm ./vamp.pid
fi

if [ -f ./vamp.nohup ]; then
    rm ./vamp.nohup
fi
