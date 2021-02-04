#!/bin/bash/
#######################################
# Bash script to install GIT (Ubuntu/Mac)
# tutorials on how to install for Windows, Linux & Mac - https://www.atlassian.com/git/tutorials/install-git
#######################################

## Detect the folder in which this file, requirements.sh, is located
SCRIPT=$(readlink -f "$0") # Absolute path to this script
SCRIPTPATH=$(dirname "$SCRIPT") # Absolute path this script is in
echo "$SCRIPTPATH"

## Detect Operating System
## TODO: only works for Linux and Mac
OS=$(uname -s)

## a. Detected a linux system
if [ $OS = "Linux" ]
then
  echo 'Detected a Linux system.. Following installation instructions for Linux systems.'

  ## Update packages and Upgrade system
  echo 'Updating packages..'
  sudo apt-get update -y
  sudo apt autoremove

  ## Git ##
  echo 'Installing Git..'
  sudo apt-get install git -y

  git --version
fi


## b. Detected a Mac
if [ $OS = "Darwin" ]
then
  echo 'Detected a Mac..'

  ## Update packages and Upgrade system
  echo 'Updating packages..'
  brew update && brew upgrade

  echo 'Installing Git..'
  brew install git

  git --version
fi

## create the output folder in which we will write the files with regendered texts
mkdir $SCRIPTPATH/output