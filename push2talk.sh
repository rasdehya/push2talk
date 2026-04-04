#!/bin/bash
# start.sh : lance le venv et le script Python de détection micro

export LD_LIBRARY_PATH=/home/remi/scripts/push2talk/.venv/lib/python3.12/site-packages/nvidia/cublas/lib:/home/remi/scripts/push2talk/.venv/lib/python3.12/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH


cd $HOME/scripts/push2talk/
source .venv/bin/activate
./push2talk.py "$@"