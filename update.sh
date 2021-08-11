#!/bin/bash

profile=$1
user=$2

if [[ ! -n "$profile" ]];
then
  profile="all"
fi

if [[ ! -n "$user" ]];
then
  user="ubuntu"
fi

echo "Running data collection scripts as user $user"

VAMP=/home/$user/Workspace/ssc

echo $VAMP

source "$VAMP/venv/bin/activate"
set -x

export PYTHONPATH=$VAMP
export SKEW_CONFIG=$VAMP/.skew
cd $VAMP
$VAMP/venv/bin/python $VAMP/update.py --profile $profile
$VAMP/venv/bin/python $VAMP/batch/cache_ec2_instance_data.py --profile $profile

