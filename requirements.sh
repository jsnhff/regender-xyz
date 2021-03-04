#!/bin/bash/
#######################################
# Bash script to install GIT (Ubuntu/Mac)
# tutorials on how to install for Windows, Linux & Mac - https://www.atlassian.com/git/tutorials/install-git
#######################################


## Detect the folder in which this file, requirements.sh, is located
SCRIPT=$(cd "$(dirname "$0")"; pwd) # Absolute path to this script's folder

## Detect Operating System
## TODO: only works for Linux and Mac
OS=$(uname -s)

## a. Detected a linux system
if [ $OS = "Linux" ]
then
  echo 'I detected a Linux system 🤖 Using apt to update your packages and install git...'

  read -p "Ready to start the package updates and git install? [y/n] " -n 1 -r
  echo '====='  # Move to a new line

  if [[ $REPLY =~ ^[Yy]$ ]]
  then
    ## Update packages and Upgrade system
    echo 'Updating packages...'
    sudo apt-get update -y
    sudo apt autoremove

    ## Git ##
    echo 'Installing Git...'
    sudo apt-get install git -y

    git --version

  fi
fi

## b. Detected a mac system
if [ $OS = "Darwin" ]
then
  echo 'I detected a Mac system 🍎 Using brew to update your system and check for git...'
  
  read -p "Ready to start the package updates and git install? [y/n] " -n 1 -r
  printf "\n=====\n"   # Move to a new line

  if [[ $REPLY =~ ^[Yy]$ ]]
  then
    ## Update packages and Upgrade system
    echo 'Updating packages using brew update && upgrade. This might take a minute...'
    brew update && brew upgrade

    echo 'Installing Git using brew install git. If you already have it it will know...'
    brew install git

    git --version

  fi
fi
printf "\n=====\n"   # Move to a new line

## Create the output folder in which we will write the files with regendered texts
echo 'Creating an output folder for your regendering experiments...'
echo 'This is the output folder location: '"$SCRIPT"
read -p "Ready to create the folder? [y/n] " -n 1 -r
printf "\n=====\n"   # Move to a new line

if [[ $REPLY =~ ^[Yy]$ ]]
then
  mkdir $SCRIPT/output
fi

printf "\n=====\n"   # Move to a new line

echo 'All set. Thanks.'