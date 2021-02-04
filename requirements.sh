#!/bin/bash/
#######################################
# Bash script to install GIT (Ubuntu/Mac)
# tutorials on how to install for Windows, Linux & Mac - https://www.atlassian.com/git/tutorials/install-git
#######################################

## Detect Operating System
## TODO: only works for Linux and Mac
OS=$(uname -s)

## a. Detected a linux system
if [ $OS = "Linux" ]
then
  echo '###Detected a Linux system..'

  ## Update packages and Upgrade system
  echo '###Updating packages..'
  sudo apt-get update -y
  sudo apt autoremove

  ## Git ##
  echo '###Installing Git..'
  sudo apt-get install git -y

  git --version
fi


## b. Detected a Mac
if [ $OS = "Darwin" ]
then
  echo '###Detected a Mac..'

  ## Update packages and Upgrade system
  echo '###Updating packages..'
  brew update && brew upgrade

  echo '###Installing Git..'
  brew install git

  git --version
fi
