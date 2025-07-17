#!/usr/bin/env bash
set -o errexit

# Instruction 1: Use 'pip' to install all the Python packages.
pip install -r requirements.txt

# Instruction 2: Now, use 'apt-get' to install the system program.
apt-get update && apt-get install -y libreoffice
