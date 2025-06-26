#!/usr/bin/env bash

# Step 1: Ensure build tools are installed
pip install --upgrade pip
pip install setuptools wheel build

# Step 2: Install dependencies
pip install -r requirements.txt
