#!/bin/bash

source $FREESURFER_HOME/SetUpFreeSurfer.sh
memray run --native --follow-fork /code/run.py "$@"
mv memray*.bin $2/log/
