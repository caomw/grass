#!/usr/bin/env python

############################################################################
#
# MODULE:       v.db.droprow
# AUTHOR(S):    Markus Neteler
#               Pythonized by Martin Landa
# PURPOSE:      Interface to v.extract -r to drop ...
# COPYRIGHT:    (C) 2009 by the GRASS Development Team
#
#               This program is free software under the GNU General Public
#               License (>=v2). Read the file COPYING that comes with GRASS
#               for details.
#
#############################################################################


#%module
#% description: Removes a vector feature from a vector map through attribute selection.
#% keywords: vector
#% keywords: attribute table
#% keywords: database
#%end

#%option G_OPT_V_INPUT
#%end

#%option G_OPT_V_FIELD
#%end

#%option G_OPT_DB_WHERE
#% required :yes
#%end

#%option G_OPT_V_OUTPUT
#%end

import sys
import grass.script as grass

def main():
    # delete vectors via reverse selection
    ret = grass.run_command('v.extract',
                            flags = 'r',
                            input = options['input'], layer = options['layer'],
                            output = options['output'], where = options['where'])
    if ret != 0:
        return 1

    # write cmd history:
    grass.vector_history(map = options['output'])

    return 0

if __name__ == "__main__":
    options, flags = grass.parser()
    sys.exit(main())
