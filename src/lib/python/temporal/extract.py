"""
Extract functions for space time raster, 3d raster and vector datasets

(C) 2012-2013 by the GRASS Development Team
This program is free software under the GNU General Public
License (>=v2). Read the file COPYING that comes with GRASS
for details.

:authors: Soeren Gebbert
"""

from grass.script.utils import get_num_suffix
from space_time_datasets import *
from open_stds import *
from multiprocessing import Process
import grass.script as gscript

############################################################################


def extract_dataset(input, output, type, where, expression, base, nprocs=1,
                    register_null=False, layer=1,
                    vtype="point,line,boundary,centroid,area,face"):
    """Extract a subset of a space time raster, raster3d or vector dataset

       A mapcalc expression can be provided to process the temporal extracted
       maps.
       Mapcalc expressions are supported for raster and raster3d maps.

       :param input: The name of the input space time raster/raster3d dataset
       :param output: The name of the extracted new space time raster/raster3d
                     dataset
       :param type: The type of the dataset: "raster", "raster3d" or vector
       :param where: The temporal SQL WHERE statement for subset extraction
       :param expression: The r(3).mapcalc expression or the v.extract where
                         statement
       :param base: The base name of the new created maps in case a mapclac
                   expression is provided
       :param nprocs: The number of parallel processes to be used for mapcalc
                     processing
       :param register_null: Set this number True to register empty maps
                            (only raster and raster3d maps)
       :param layer: The vector layer number to be used when no timestamped
              layer is present, default is 1
       :param vtype: The feature type to be extracted for vector maps, default
              is point,line,boundary,centroid,area and face
    """

    # Check the parameters
    msgr = get_tgis_message_interface()

    if expression and not base:
        msgr.fatal(_("You need to specify the base name of new created maps"))

    mapset = get_current_mapset()

    dbif = SQLDatabaseInterfaceConnection()
    dbif.connect()

    sp = open_old_stds(input, type, dbif)
    # Check the new stds
    new_sp = check_new_stds(output, type, dbif, gscript.overwrite())
    if type == "vector":
        rows = sp.get_registered_maps(
            "id,name,mapset,layer", where, "start_time", dbif)
    else:
        rows = sp.get_registered_maps("id", where, "start_time", dbif)

    new_maps = {}
    if rows:
        num_rows = len(rows)

        msgr.percent(0, num_rows, 1)

        # Run the mapcalc expression
        if expression:
            count = 0
            proc_count = 0
            proc_list = []

            for row in rows:
                count += 1

                if count % 10 == 0:
                    msgr.percent(count, num_rows, 1)

                map_name = "{base}_{suffix}".format(base=base,
                                                    suffix=get_num_suffix(count,
                                                                          num_rows))

                # We need to modify the r(3).mapcalc expression
                if type != "vector":
                    expr = "%s = %s" % (map_name, expression)

                    expr = expr.replace(sp.base.get_map_id(), row["id"])
                    expr = expr.replace(sp.base.get_name(), row["id"])

                    # We need to build the id
                    map_id = AbstractMapDataset.build_id(map_name, mapset)
                else:
                    map_id = AbstractMapDataset.build_id(map_name, mapset,
                                                         row["layer"])

                new_map = sp.get_new_map_instance(map_id)

                # Check if new map is in the temporal database
                if new_map.is_in_db(dbif):
                    if gscript.overwrite():
                        # Remove the existing temporal database entry
                        new_map.delete(dbif)
                        new_map = sp.get_new_map_instance(map_id)
                    else:
                        msgr.error(_("Map <%s> is already in temporal database"
                                     ", use overwrite flag to overwrite") %
                                    (new_map.get_map_id()))
                        continue

                # Add process to the process list
                if type == "raster":
                    msgr.verbose(_("Applying r.mapcalc expression: \"%s\"")
                                 % expr)
                    proc_list.append(Process(target=run_mapcalc2d,
                                             args=(expr,)))
                elif type == "raster3d":
                    msgr.verbose(_("Applying r3.mapcalc expression: \"%s\"")
                                 % expr)
                    proc_list.append(Process(target=run_mapcalc3d,
                                             args=(expr,)))
                elif type == "vector":
                    msgr.verbose(_("Applying v.extract where statement: \"%s\"")
                                 % expression)
                    if row["layer"]:
                        proc_list.append(Process(target=run_vector_extraction,
                                                 args=(row["name"] + "@" +
                                                       row["mapset"], map_name,
                                                       row["layer"], vtype,
                                                       expression)))
                    else:
                        proc_list.append(Process(target=run_vector_extraction,
                                                 args=(row["name"] + "@" +
                                                       row["mapset"], map_name,
                                                       layer, vtype,
                                                       expression)))

                proc_list[proc_count].start()
                proc_count += 1

                # Join processes if the maximum number of processes are
                # reached or the end of the loop is reached
                if proc_count == nprocs or count == num_rows:
                    proc_count = 0
                    exitcodes = 0
                    for proc in proc_list:
                        proc.join()
                        exitcodes += proc.exitcode
                    if exitcodes != 0:
                        dbif.close()
                        msgr.fatal(_("Error in computation process"))

                    # Empty process list
                    proc_list = []

                # Store the new maps
                new_maps[row["id"]] = new_map

        msgr.percent(0, num_rows, 1)

        temporal_type, semantic_type, title, description = sp.get_initial_values()
        new_sp = open_new_stds(output, type, sp.get_temporal_type(), title.
                               description, semantic_type, dbif,
                               gscript.overwrite())

        # collect empty maps to remove them
        empty_maps = []

        # Register the maps in the database
        count = 0
        for row in rows:
            count += 1

            if count % 10 == 0:
                msgr.percent(count, num_rows, 1)

            old_map = sp.get_new_map_instance(row["id"])
            old_map.select(dbif)

            if expression:
                # Register the new maps
                if row["id"] in new_maps:
                    new_map = new_maps[row["id"]]

                    # Read the raster map data
                    new_map.load()

                    # In case of a empty map continue, do not register empty
                    # maps
                    if type == "raster" or type == "raster3d":
                        if new_map.metadata.get_min() is None and \
                            new_map.metadata.get_max() is None:
                            if not register_null:
                                empty_maps.append(new_map)
                                continue
                    elif type == "vector":
                        if new_map.metadata.get_number_of_primitives() == 0 or \
                           new_map.metadata.get_number_of_primitives() is None:
                            if not register_null:
                                empty_maps.append(new_map)
                                continue

                    # Set the time stamp
                    new_map.set_temporal_extent(old_map.get_temporal_extent())

                    # Insert map in temporal database
                    new_map.insert(dbif)

                    new_sp.register_map(new_map, dbif)
            else:
                new_sp.register_map(old_map, dbif)

        # Update the spatio-temporal extent and the metadata table entries
        new_sp.update_from_registered_maps(dbif)

        msgr.percent(num_rows, num_rows, 1)

        # Remove empty maps
        if len(empty_maps) > 0:
            names = ""
            count = 0
            for map in empty_maps:
                if count == 0:
                    names += "%s" % (map.get_name())
                else:
                    names += ",%s" % (map.get_name())
                count += 1
            if type == "raster":
                gscript.run_command("g.remove", flags='f', type='rast',
                                    pattern=names, quiet=True)
            elif type == "raster3d":
                gscript.run_command("g.remove", flags='f', type='rast3d',
                                    pattern=names, quiet=True)
            elif type == "vector":
                gscript.run_command("g.remove", flags='f', type='vect',
                                    pattern=names, quiet=True)

    dbif.close()

###############################################################################


def run_mapcalc2d(expr):
    """Helper function to run r.mapcalc in parallel"""
    exit(gscript.run_command("r.mapcalc", expression=expr,
                             overwrite=gscript.overwrite(), quiet=True))


def run_mapcalc3d(expr):
    """Helper function to run r3.mapcalc in parallel"""
    exit(gscript.run_command("r3.mapcalc", expression=expr,
                             overwrite=gscript.overwrite(), quiet=True))


def run_vector_extraction(input, output, layer, type, where):
    """Helper function to run r.mapcalc in parallel"""
    exit(gscript.run_command("v.extract", input=input, output=output,
                             layer=layer, type=type, where=where,
                             overwrite=gscript.overwrite(), quiet=True))
