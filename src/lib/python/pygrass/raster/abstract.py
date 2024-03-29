# -*- coding: utf-8 -*-
"""
Created on Fri Aug 17 16:05:25 2012

@author: pietro
"""
from __future__ import (nested_scopes, generators, division, absolute_import,
                        with_statement, print_function, unicode_literals)
import ctypes

#
# import GRASS modules
#
from grass.script import fatal, gisenv
import grass.lib.gis as libgis
import grass.lib.raster as libraster

#
# import pygrass modules
#
from grass.pygrass import functions
from grass.pygrass.gis.region import Region
from grass.pygrass.errors import must_be_open
from grass.pygrass.shell.conversion import dict2html
from grass.pygrass.shell.show import raw_figure

#
# import raster classes
#
from grass.pygrass.raster.raster_type import TYPE as RTYPE, RTYPE_STR
from grass.pygrass.raster.category import Category
from grass.pygrass.raster.history import History


## Define global variables to not exceed the 80 columns
WARN_OVERWRITE = "Raster map <{0}> already exists and will be overwritten"
INDXOUTRANGE = "The index (%d) is out of range, have you open the map?."
INFO = """{name}@{mapset}
rows: {rows}
cols: {cols}
north: {north} south: {south} nsres:{nsres}
east:  {east} west: {west} ewres:{ewres}
range: {min}, {max}
proj: {proj}
"""


class Info(object):
    def __init__(self, name, mapset=''):
        """Read the information for a raster map. ::

            >>> info = Info('elevation')
            >>> info.read()
            >>> info
            elevation@
            rows: 1350
            cols: 1500
            north: 228500.0 south: 215000.0 nsres:10.0
            east:  645000.0 west: 630000.0 ewres:10.0
            range: 56, 156
            proj: 99
            <BLANKLINE>

        """
        self.name = name
        self.mapset = mapset
        self.c_region = ctypes.pointer(libgis.Cell_head())
        self.c_range = None

    def _get_range(self):
        if self.mtype == 'CELL':
            self.c_range = ctypes.pointer(libraster.Range())
            libraster.Rast_read_range(self.name, self.mapset, self.c_range)
        else:
            self.c_range = ctypes.pointer(libraster.FPRange())
            libraster.Rast_read_fp_range(self.name, self.mapset, self.c_range)

    def _get_raster_region(self):
        libraster.Rast_get_cellhd(self.name, self.mapset, self.c_region)

    def read(self):
        self._get_range()
        self._get_raster_region()

    @property
    def north(self):
        return self.c_region.contents.north

    @property
    def south(self):
        return self.c_region.contents.south

    @property
    def east(self):
        return self.c_region.contents.east

    @property
    def west(self):
        return self.c_region.contents.west

    @property
    def top(self):
        return self.c_region.contents.top

    @property
    def bottom(self):
        return self.c_region.contents.bottom

    @property
    def rows(self):
        return self.c_region.contents.rows

    @property
    def cols(self):
        return self.c_region.contents.cols

    @property
    def nsres(self):
        return self.c_region.contents.ns_res

    @property
    def ewres(self):
        return self.c_region.contents.ew_res

    @property
    def tbres(self):
        return self.c_region.contents.tb_res

    @property
    def zone(self):
        return self.c_region.contents.zone

    @property
    def proj(self):
        return self.c_region.contents.proj

    @property
    def min(self):
        if self.c_range is None:
            return None
        return self.c_range.contents.min

    @property
    def max(self):
        if self.c_range is None:
            return None
        return self.c_range.contents.max

    @property
    def range(self):
        if self.c_range is None:
            return None, None
        return self.c_range.contents.min, self.c_range.contents.max

    @property
    def mtype(self):
        return RTYPE_STR[libraster.Rast_map_type(self.name, self.mapset)]

    def _get_units(self):
        return libraster.Rast_read_units(self.name, self.mapset)

    def _set_units(self, units):
        libraster.Rast_write_units(self.name, units)

    units = property(_get_units, _set_units)

    def _get_vdatum(self):
        return libraster.Rast_read_vdatum(self.name, self.mapset)

    def _set_vdatum(self, vdatum):
        libraster.Rast_write_vdatum(self.name, vdatum)

    vdatum = property(_get_vdatum, _set_vdatum)

    def __repr__(self):
        return INFO.format(name=self.name, mapset=self.mapset,
                           rows=self.rows, cols=self.cols,
                           north=self.north, south=self.south,
                           east=self.east, west=self.west,
                           top=self.top, bottom=self.bottom,
                           nsres=self.nsres, ewres=self.ewres,
                           tbres=self.tbres, zone=self.zone,
                           proj=self.proj, min=self.min, max=self.max)

    def keys(self):
        return ['name', 'mapset', 'rows', 'cols', 'north', 'south',
                'east', 'west', 'top', 'bottom', 'nsres', 'ewres', 'tbres',
                'zone', 'proj', 'min', 'max']

    def items(self):
        return [(k, self.__getattribute__(k)) for k in self.keys()]

    def _repr_html_(self):
        return dict2html(dict(self.items()), keys=self.keys(),
                         border='1', kdec='b')


class RasterAbstractBase(object):
    """Raster_abstract_base: The base class from which all sub-classes
    inherit. It does not implement any row or map access methods:

    * Implements raster metadata information access (Type, ...)
    * Implements an open method that will be overwritten by the sub-classes
    * Implements the close method that might be overwritten by sub-classes
      (should work for simple row access)
    * Implements get and set region methods
    * Implements color, history and category handling
    * Renaming, deletion, ...

    """
    def __init__(self, name, mapset="", *aopen, **kwopen):
        """The constructor need at least the name of the map
        *optional* field is the `mapset`.

        >>> ele = RasterAbstractBase('elevation')
        >>> ele.name
        u'elevation'
        >>> ele.exist()
        True
        >>> ele.mapset
        'PERMANENT'

        ..
        """
        self.mapset = mapset
        self._name = name
        ## Private attribute `_fd` that return the file descriptor of the map
        self._fd = None
        ## Private attribute `_rows` that return the number of rows
        # in active window, When the class is instanced is empty and it is set
        # when you open the file, using Rast_window_rows()
        self._rows = None
        ## Private attribute `_cols` that return the number of rows
        # in active window, When the class is instanced is empty and it is set
        # when you open the file, using Rast_window_cols()
        self._cols = None
        #self.region = Region()
        self.hist = History(self.name, self.mapset)
        self.cats = Category(self.name, self.mapset)
        self.info = Info(self.name, self.mapset)
        self._aopen = aopen
        self._kwopen = kwopen
        self._mtype = 'CELL'
        self._mode = 'r'
        self._overwrite = False

    def __enter__(self):
        self.open(*self._aopen, **self._kwopen)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _get_mtype(self):
        """Private method to get the Raster type"""
        return self._mtype

    def _set_mtype(self, mtype):
        """Private method to change the Raster type"""
        if mtype.upper() not in ('CELL', 'FCELL', 'DCELL'):
            #fatal(_("Raser type: {0} not supported".format(mtype) ) )
            str_err = "Raster type: {0} not supported ('CELL','FCELL','DCELL')"
            raise ValueError(_(str_err).format(mtype))
        self._mtype = mtype
        self._gtype = RTYPE[self.mtype]['grass type']

    mtype = property(fget=_get_mtype, fset=_set_mtype)

    def _get_mode(self):
        return self._mode

    def _set_mode(self, mode):
        if mode.upper() not in ('R', 'W'):
            str_err = _("Mode type: {0} not supported ('r', 'w')")
            raise ValueError(str_err.format(mode))
        self._mode = mode

    mode = property(fget=_get_mode, fset=_set_mode)

    def _get_overwrite(self):
        return self._overwrite

    def _set_overwrite(self, overwrite):
        if overwrite not in (True, False):
            str_err = _("Overwrite type: {0} not supported (True/False)")
            raise ValueError(str_err.format(overwrite))
        self._overwrite = overwrite

    overwrite = property(fget=_get_overwrite, fset=_set_overwrite)

    def _get_name(self):
        """Private method to return the Raster name"""
        return self._name

    def _set_name(self, newname):
        """Private method to change the Raster name"""
        if not functions.is_clean_name(newname):
            str_err = _("Map name {0} not valid")
            raise ValueError(str_err.format(newname))
        if self.exist():
            self.rename(newname)
        self._name = newname

    name = property(fget=_get_name, fset=_set_name)

    @must_be_open
    def _get_cats_title(self):
        return self.cats.title

    @must_be_open
    def _set_cats_title(self, newtitle):
        self.cats.title = newtitle

    cats_title = property(fget=_get_cats_title, fset=_set_cats_title)

    def __unicode__(self):
        return self.name_mapset()

    def __str__(self):
        """Return the string of the object"""
        return self.__unicode__()

    def __len__(self):
        return self._rows

    def __getitem__(self, key):
        """Return the row of Raster object, slice allowed."""
        if isinstance(key, slice):
            #import pdb; pdb.set_trace()
            #Get the start, stop, and step from the slice
            return (self.get_row(ii) for ii in range(*key.indices(len(self))))
        elif isinstance(key, tuple):
            x, y = key
            return self.get(x, y)
        elif isinstance(key, int):
            if key < 0:  # Handle negative indices
                key += self._rows
            if key >= self._rows:
                fatal(INDXOUTRANGE.format(key))
                raise IndexError
            return self.get_row(key)
        else:
            fatal("Invalid argument type.")

    def __iter__(self):
        """Return a constructor of the class"""
        return (self.__getitem__(irow) for irow in range(self._rows))

    def _repr_png_(self):
        return raw_figure(functions.r_export(self))

    def exist(self):
        """Return True if the map already exist, and
        set the mapset if were not set.

        call the C function `G_find_raster`.

        >>> ele = RasterAbstractBase('elevation')
        >>> ele.exist()
        True
        """
        if self.name:
            if self.mapset == '':
                mapset = functions.get_mapset_raster(self.name, self.mapset)
                self.mapset = mapset if mapset else ''
                return True if mapset else False
            return bool(functions.get_mapset_raster(self.name, self.mapset))
        else:
            return False

    def is_open(self):
        """Return True if the map is open False otherwise.

        >>> ele = RasterAbstractBase('elevation')
        >>> ele.is_open()
        False

        """
        return True if self._fd is not None and self._fd >= 0 else False

    @must_be_open
    def close(self):
        """Close the map"""
        libraster.Rast_close(self._fd)
        # update rows and cols attributes
        self._rows = None
        self._cols = None
        self._fd = None

    def remove(self):
        """Remove the map"""
        if self.is_open():
            self.close()
        functions.remove(self.name, 'rast')

    def fullname(self):
        """Return the full name of a raster map: name@mapset"""
        return "{name}@{mapset}".format(name=self.name, mapset=self.mapset)

    def name_mapset(self, name=None, mapset=None):
        """Return the full name of the Raster.

        >>> ele = RasterAbstractBase('elevation')
        >>> ele.name_mapset()
        u'elevation@PERMANENT'

        """
        if name is None:
            name = self.name
        if mapset is None:
            self.exist()
            mapset = self.mapset

        gis_env = gisenv()

        if mapset and mapset != gis_env['MAPSET']:
            return "{name}@{mapset}".format(name=name, mapset=mapset)
        else:
            return name

    def rename(self, newname):
        """Rename the map"""
        if self.exist():
            functions.rename(self.name, newname, 'rast')
        self._name = newname

    def set_from_rast(self, rastname='', mapset=''):
        """Set the region that will use from a map, if rastername and mapset
        is not specify, use itself.

        call C function `Rast_get_cellhd`"""
        if self.is_open():
            fatal("You cannot change the region if map is open")
            raise
        region = Region()
        if rastname == '':
            rastname = self.name
        if mapset == '':
            mapset = self.mapset

        libraster.Rast_get_cellhd(rastname, mapset,
                                  ctypes.byref(region._region))
        # update rows and cols attributes
        self._rows = libraster.Rast_window_rows()
        self._cols = libraster.Rast_window_cols()

    @must_be_open
    def get_value(self, point, region=None):
        """This method returns the pixel value of a given pair of coordinates:

        :param point: pair of coordinates in tuple object
        """
        if not region:
            region = Region()
        row, col = functions.coor2pixel(point.coords(), region)
        if col < 0 or col > region.cols or row < 0 or row > region.rows:
            return None
        line = self.get_row(int(row))
        return line[int(col)]

    @must_be_open
    def has_cats(self):
        """Return True if the raster map has categories"""
        if self.exist():
            self.cats.read()
            if len(self.cats) != 0:
                return True
        return False

    @must_be_open
    def num_cats(self):
        """Return the number of categories"""
        return len(self.cats)

    @must_be_open
    def copy_cats(self, raster):
        """Copy categories from another raster map object"""
        self.cats.copy(raster.cats)

    @must_be_open
    def sort_cats(self):
        """Sort categories order by range"""
        self.cats.sort()

    @must_be_open
    def read_cats(self):
        """Read category from the raster map file"""
        self.cats.read(self)

    @must_be_open
    def write_cats(self):
        """Write category to the raster map file"""
        self.cats.write(self)

    @must_be_open
    def read_cats_rules(self, filename, sep=':'):
        """Read category from the raster map file"""
        self.cats.read_rules(filename, sep)

    @must_be_open
    def write_cats_rules(self, filename, sep=':'):
        """Write category to the raster map file"""
        self.cats.write_rules(filename, sep)

    @must_be_open
    def get_cats(self):
        """Return a category object"""
        cat = Category()
        cat.read(self)
        return cat

    @must_be_open
    def set_cats(self, category):
        """The internal categories are copied from this object."""
        self.cats.copy(category)

    @must_be_open
    def get_cat(self, label):
        """Return a category given an index or a label"""
        return self.cats[label]

    @must_be_open
    def set_cat(self, label, min_cat, max_cat=None, index=None):
        """Set or update a category"""
        self.cats.set_cat(index, (label, min_cat, max_cat))
