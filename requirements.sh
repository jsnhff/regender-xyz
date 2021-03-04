#!/bin/bash/
#######################################
# Bash script to install GIT (Ubuntu/Mac)
# tutorials on how to install for Windows, Linux & Mac - https://www.atlassian.com/git/tutorials/install-git
#######################################


## Detect the folder in which this file, requirements.sh, is located
SCRIPT=$(readlink -f "$0") # Absolute path to this script
SCRIPTPATH=$(dirname "$SCRIPT") # Absolute path this script is in

## Detect Operating System
## TODO: only works for Linux and Mac
OS=$(uname -s)

## a. Detected a linux system
if [ $OS = "Linux" ]
then
  echo 'I detected a Linux system 🤖 Using apt to update your packages and install git...'

  ## Update packages and Upgrade system
  echo 'Updating packages...'
  sudo apt-get update -y
  sudo apt autoremove

  ## Git ##
  echo 'Installing Git...'
  sudo apt-get install git -y

  git --version
fi


## b. Detected a mac system
if [ $OS = "Darwin" ]
then
  echo 'I detected a Mac system 🍎 Using brew to update your system and check for git...'

  ## Update packages and Upgrade system
  echo 'Updating packages using brew update && upgrade. This might take a minute...'
  brew update && brew upgrade

  echo 'Installing Git using brew install git. If you already have it it will know...'
  brew install git

  git --version
fi

## Create the output folder in which we will write the files with regendered texts
echo 'Creating an output folder in this directory for your regendering experiments...'
mkdir $SCRIPTPATH/output