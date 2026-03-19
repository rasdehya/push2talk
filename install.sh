#!/bin/bash

sudo apt install \
python3-pip \
xdotool \
alsa-utils \
libnotify-bin \
librsvg2-bin \
-y

uv init
uv venv
uv pip install -r requirements.txt


# Replace with the correct nvidia-cublas PATH
#export LD_LIBRARY_PATH=/home/remi/scripts/push2talk/.venv/lib/python3.12/site-packages/nvidia/cublas/lib:/home/remi/scripts/push2talk/.venv/lib/python3.12/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH
