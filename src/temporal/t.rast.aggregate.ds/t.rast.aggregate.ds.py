#!/usr/bin/env python
# -*- coding: utf-8 -*-
############################################################################
#
# MODULE:	t.rast.aggregate.ds
# AUTHOR(S):	Soeren Gebbert
#
# PURPOSE:	Aggregates data of an existing space time raster dataset using the time intervals of a second space time dataset
# COPYRIGHT:	(C) 2011 by the gcore Development Team
#
#		This program is free software under the GNU General Public
#		License (version 2). Read the file COPYING that comes with gcore
#		for details.
#
#############################################################################

#%module
#% description: Aggregates data of an existing space time raster dataset using the time intervals of a second space time dataset.
#% keywords: temporal
#% keywords: aggregation
#%end

#%option G_OPT_STRDS_INPUT
#%end

#%option G_OPT_STDS_INPUT
#% key: sample
#% description: Time intervals from this space time dataset (raster, vector or raster3d) are used for aggregation computation
#%end

#%option G_OPT_STDS_TYPE
#% description: Type of the aggregation space time dataset, default is strds
#%end

#%option G_OPT_STRDS_OUTPUT
#%end

#%option
#% key: basename
#% type: string
#% label: Basename of the new generated output maps
#% description: A numerical suffix separated by an underscore will be attached to create a unique identifier
#% required: yes
#% multiple: no
#% gisprompt:
#%end

#%option
#% key: method
#% type: string
#% description: Aggregate operation to be performed on the raster maps
#% required: yes
#% multiple: no
#% options: average,count,median,mode,minimum,min_raster,maximum,max_raster,stddev,range,sum,variance,diversity,slope,offset,detcoeff,quart1,quart3,perc90,quantile,skewness,kurtosis
#% answer: average
#%end

#%option
#% key: offset
#% type: integer
#% description: Offset that is used to create the output map ids, output map id is generated as: basename_ (count + offset)
#% required: no
#% multiple: no
#% answer: 0
#%end

#%option
#% key: nprocs
#% type: integer
#% description: Number of r.mapcalc processes to run in parallel
#% required: no
#% multiple: no
#% answer: 1
#%end

#%option G_OPT_T_SAMPLE
#% options: equal,overlaps,overlapped,starts,started,finishes,finished,during,contains
#% answer: contains
#%end

#%option G_OPT_T_WHERE
#%end

#%flag
#% key: n
#% description: Register Null maps
#%end

#%flag
#% key: s
#% description: Use start time - truncated accoring to granularity - as suffix. This flag overrides the offset option.
#%end

import grass.script as gcore
import grass.temporal as tgis

############################################################################


def main():

    # Get the options
    input = options["input"]
    output = options["output"]
    sampler = options["sample"]
    where = options["where"]
    base = options["basename"]
    register_null = flags["n"]
    method = options["method"]
    sampling = options["sampling"]
    offset = options["offset"]
    nprocs = options["nprocs"]
    time_suffix = flags["s"]
    type = options["type"]
    
    topo_list = sampling.split(",")

    tgis.init()

    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()

    sp = tgis.open_old_stds(input, "strds", dbif)
    sampler_sp = tgis.open_old_stds(sampler, type, dbif)

    if sampler_sp.get_temporal_type() != sp.get_temporal_type():
        dbif.close()
        gcore.fatal(_("Input and aggregation dataset must have "
                      "the same temporal type"))

    # Check if intervals are present
    if sampler_sp.temporal_extent.get_map_time() != "interval":
        dbif.close()
        gcore.fatal(_("All registered maps of the aggregation dataset "
                      "must have time intervals"))

    # We will create the strds later, but need to check here
    tgis.check_new_stds(output, "strds",   dbif,  gcore.overwrite())

    map_list = sp.get_registered_maps_as_objects(where=where, order="start_time", dbif=dbif)

    if not map_list:
        dbif.close()
        gcore.fatal(_("Space time raster dataset <%s> is empty") % input)

    granularity_list = sampler_sp.get_registered_maps_as_objects(where=where, order="start_time", dbif=dbif)

    if not granularity_list:
        dbif.close()
        gcore.fatal(_("Space time raster dataset <%s> is empty") % sampler)

    gran = sampler_sp.get_granularity()

    output_list = tgis.aggregate_by_topology(granularity_list=granularity_list,  granularity=gran,  
                                                                       map_list=map_list,  
                                                                       topo_list=topo_list,  basename=base, time_suffix=time_suffix,
                                                                       offset=offset,  method=method,  nprocs=nprocs,  spatial=None, 
                                                                       overwrite=gcore.overwrite())

    if output_list:
        temporal_type, semantic_type, title, description = sp.get_initial_values()
        output_strds = tgis.open_new_stds(output, "strds", temporal_type,
                                                                 title, description, semantic_type,
                                                                 dbif, gcore.overwrite())
        tgis.register_map_object_list("rast", output_list,  output_strds,  register_null,  
                                                       sp.get_relative_time_unit(),  dbif)

        # Update the raster metadata table entries with aggregation type
        output_strds.set_aggregation_type(method)
        output_strds.metadata.update(dbif)

    dbif.close()

if __name__ == "__main__":
    options, flags = gcore.parser()
    main()
