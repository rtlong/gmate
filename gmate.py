#!/usr/bin/env python
# This program is part of GMATE package
# Gmate script
# Author: Alexandre da Silva
# 
# This is a revised version of the above named script. It was revised 9/02/2011
# by Ryan Long [ryan@rtlong.com]. 
#
# While the original script expected an argument for the working directory, this
# script assumes the filebrowser root to be the current directory upon invocation.

import gconf
import sys
import urllib
import os
#from optparse import OptionParser

# GConf directory for filebrowser
base = '/apps/gedit-2/plugins/filebrowser/on_load'
config = gconf.client_get_default()
config.add_dir(base, gconf.CLIENT_PRELOAD_NONE)

# Set the filebrowser/on_load/virtual_root key to the current working directory.
url = "file://%s" % urllib.quote(os.environ['PWD'])
print url
config.set_string(os.path.join(base,'virtual_root'), url)

if len(sys.argv) > 0:
    parameters = ' '.join(sys.argv[1:])
    os.system('nohup gedit ' + parameters + ' > /dev/null 2>&1 &')
else:
    os.system('nohup gedit > /dev/null 2>&1 &')

