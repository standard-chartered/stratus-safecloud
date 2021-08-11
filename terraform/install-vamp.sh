#!/bin/bash

echo "Running install-vamp.sh now..."

echo "Run apt-get update"
sudo apt-get -y update
echo "Install python3 and pip3"
sudo apt-get install -y python3-venv
sudo apt-get install -y python3-pip
echo "Install authbind"
sudo apt-get install -y authbind

# Update ssh-agent
echo "Update ssh-agent"
chmod 400 $HOME/.ssh/aws-bb
eval $(ssh-agent -s)
ssh-add ~/.ssh/aws-bb

cd $HOME

# Create required directory
if [ ! -d "$HOME/Workspace" ]
then    
    mkdir Workspace
fi

cd Workspace

# Git commands
git config --global core.sshCommand 'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no'
if [ ! -d "$HOME/Workspace/ssc" ]
then    
    echo "Cloning git repo"
    git clone git@github.com:SCVenturesCore/ssc.git
    cd ssc
else
    echo "Doing git pull from master branch"
    cd ssc
    git pull origin main
fi

# Install the Vamp application

# Create a virtual environment if it doesn't already exist and activate it
if [ ! -d "$HOME/Workspace/ssc/venv" ]
then
    echo "Create virtual environment"    
    python3 -m venv venv
    echo "Activate new virtual environment"
    source venv/bin/activate
    echo "Installing the required python modules  "
    pip3 install wheel
    pip3 install -r requirements.txt
else
    echo "Activate existing virtual environment"
    source venv/bin/activate
fi

# Run the data collection script update.sh
echo "Collecting security and resource data for AWS accounts"
./update.sh

# Run the application if it's not already running
if [ ! -f "$HOME/Workspace/ssc/vamp.pid" ]; then
    echo "Starting application"
    ./start.sh
else
    echo "Stopping running instance of Vamp"
    ./stop.sh
    echo "Restarting Vamp"
    ./start.sh
fi



