#!/usr/bin/env python
# -*- coding: utf-8 -*-
############################################################################
#
# MODULE:       t.vect.db.select
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:      Prints attributes of vector maps registered in a space time vector dataset.
# COPYRIGHT:	(C) 2011-2014, Soeren Gebbert and the GRASS Development Team
#
#               This program is free software under the GNU General Public
#               License (version 2). Read the file COPYING that comes with GRASS
#               for details.
#
#############################################################################

#%module
#% description: Prints attributes of vector maps registered in a space time vector dataset.
#% keywords: temporal
#% keywords: attribute table
#% keywords: vector
#% keywords: database
#% keywords: select
#%end

#%option G_OPT_STVDS_INPUT
#%end

#%option G_OPT_DB_COLUMNS
#%end

#%option G_OPT_F_SEP
#% description: Field separator character between the output columns
#%end

#%option G_OPT_V_FIELD
#%end

#%option G_OPT_DB_WHERE
#%end

#%option G_OPT_T_WHERE
#% key: t_where
#%end

import grass.script as grass
import grass.temporal as tgis

############################################################################


def main():

    # Get the options
    input = options["input"]
    where = options["where"]
    columns = options["columns"]
    tempwhere = options["t_where"]
    layer = options["layer"]
    separator = grass.separator(options["separator"])

    if where == "" or where == " " or where == "\n":
        where = None

    if columns == "" or columns == " " or columns == "\n":
        columns = None

    # Make sure the temporal database exists
    tgis.init()

    sp = tgis.open_old_stds(input, "stvds")

    rows = sp.get_registered_maps("name,layer,mapset,start_time,end_time",
                                  tempwhere, "start_time", None)

    col_names = ""
    if rows:
        for row in rows:
            vector_name = "%s@%s" % (row["name"], row["mapset"])
            # In case a layer is defined in the vector dataset,
            # we override the option layer
            if row["layer"]:
                layer = row["layer"]

            select = grass.read_command("v.db.select", map=vector_name,
                                        layer=layer, columns=columns,
                                        separator="%s" % (separator), where=where)

            if not select:
                grass.fatal(_("Unable to run v.db.select for vector map <%s> "
                              "with layer %s") % (vector_name, layer))
            # The first line are the column names
            list = select.split("\n")
            count = 0
            for entry in list:
                if entry.strip() != "":
                    # print the column names in case they change
                    if count == 0:
                        col_names_new = "start_time%send_time%s%s" % (
                            separator, separator, entry)
                        if col_names != col_names_new:
                            col_names = col_names_new
                            print col_names
                    else:
                        if row["end_time"]:
                            print "%s%s%s%s%s" % (row["start_time"], separator,
                                                  row["end_time"], separator, entry)
                        else:
                            print "%s%s%s%s" % (row["start_time"],
                                                separator, separator, entry)
                    count += 1

if __name__ == "__main__":
    options, flags = grass.parser()
    main()
