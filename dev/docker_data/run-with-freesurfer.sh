#!/bin/bash

source $FREESURFER_HOME/SetUpFreeSurfer.sh
python3 -m memray run -o $2/log/memray-output.bin --native --follow-fork /code/run.py "$@"
