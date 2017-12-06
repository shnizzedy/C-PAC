#!/usr/bin/env python

import sys
from os import path

def check_inputs(*pathstrs):
    for pathstr in pathstrs:
        if not path.exists(pathstr):
            print "ERROR: input '%s' doesn't exist" % pathstr
            raise SystemExit(2)
        _,ext = path.splitext(pathstr)
        if ext not in [".yml",".yaml"]:
            print "ERROR: input '%s' is not a yaml file (*.yml or *.yaml)" % pathstr
            raise SystemExit(2)
    return

if len(sys.argv) != 2:
    print "Usage: %s /path/to/data_config.yml" % path.basename(sys.argv[0])
    print "Will output three files needed by C-PAC into the current directory"
    raise SystemExit(1)

data_config_file = sys.argv[1]

import CPAC
CPAC.utils.extract_data.run(data_config_file)
