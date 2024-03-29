"""!Unit test to register raster maps with absolute and relative
   time using tgis.register_maps_in_space_time_dataset()

(C) 2013 by the GRASS Development Team
This program is free software under the GNU General Public
License (>=v2). Read the file COPYING that comes with GRASS
for details.

@author Soeren Gebbert
"""

import grass.temporal as tgis
import grass.gunittest
import datetime
import os


class TestRegisterFunctions(grass.gunittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """!Initiate the temporal GIS and set the region
        """
        os.putenv("GRASS_OVERWRITE", "1")
        # Use always the current mapset as temporal database
        cls.runModule("g.gisenv", set="TGIS_USE_CURRENT_MAPSET=1")
        tgis.init()
        cls.use_temp_region()
        cls.runModule('g.region', n=80.0, s=0.0, e=120.0, w=0.0,
                      t=1.0, b=0.0, res=10.0)

    @classmethod
    def tearDownClass(cls):
        """!Remove the temporary region
        """
        cls.del_temp_region()

    def setUp(self):
        """!Create the test maps and the space time raster datasets
        """
        self.runModule("r.mapcalc", overwrite=True, quiet=True,
                       expression="register_map_1 = 1")
        self.runModule("r.mapcalc", overwrite=True, quiet=True,
                       expression="register_map_2 = 2")

        self.strds_abs = tgis.open_new_stds(name="register_test_abs", type="strds", temporaltype="absolute",
                                            title="Test strds", descr="Test strds", semantic="field")
        self.strds_rel = tgis.open_new_stds(name="register_test_rel", type="strds", temporaltype="relative",
                                            title="Test strds", descr="Test strds", semantic="field")

    def tearDown(self):
        """!Remove maps from temporal database
        """
        self.runModule("t.unregister", maps="register_map_1,register_map_2", quiet=True)
        self.runModule("g.remove", flags='f', type="rast", pattern="register_map_1,register_map_2", quiet=True)
        self.strds_abs.delete()
        self.strds_rel.delete()

    def test_absolute_time_strds_1(self):
        """!Test the registration of maps with absolute time in a
           space time raster dataset
        """
        tgis.register_maps_in_space_time_dataset(type="rast", name=self.strds_abs.get_name(),
                 maps="register_map_1,register_map_2",
                 start="2001-01-01", increment="1 day", interval=True)

        map = tgis.RasterDataset("register_map_1@" + tgis.get_current_mapset())
        map.select()
        start, end = map.get_absolute_time()
        self.assertEqual(start, datetime.datetime(2001, 1, 1))
        self.assertEqual(end, datetime.datetime(2001, 1, 2))

        map = tgis.RasterDataset("register_map_2@" + tgis.get_current_mapset())
        map.select()
        start, end = map.get_absolute_time()
        self.assertEqual(start, datetime.datetime(2001, 1, 2))
        self.assertEqual(end, datetime.datetime(2001, 1, 3))

        self.strds_abs.select()
        start, end = self.strds_abs.get_absolute_time()
        self.assertEqual(start, datetime.datetime(2001, 1, 1))
        self.assertEqual(end, datetime.datetime(2001, 1, 3))

    def test_absolute_time_strds_2(self):
        """!Test the registration of maps with absolute time in a
           space time raster dataset.
           The timestamps are set using the C-Interface beforehand, so that the register function needs
           to read the timetsamp from the map metadata.
        """

        ciface = tgis.get_tgis_c_library_interface()
        ciface.write_raster_timestamp("register_map_1", tgis.get_current_mapset(), "1 Jan 2001/2 Jan 2001")
        ciface.write_raster_timestamp("register_map_2", tgis.get_current_mapset(), "2 Jan 2001/3 Jan 2001")

        tgis.register_maps_in_space_time_dataset(type="rast", name=self.strds_abs.get_name(),
                                                 maps="register_map_1,register_map_2")

        map = tgis.RasterDataset("register_map_1@" + tgis.get_current_mapset())
        map.select()
        start, end = map.get_absolute_time()
        self.assertEqual(start, datetime.datetime(2001, 1, 1))
        self.assertEqual(end, datetime.datetime(2001, 1, 2))

        map = tgis.RasterDataset("register_map_2@" + tgis.get_current_mapset())
        map.select()
        start, end = map.get_absolute_time()
        self.assertEqual(start, datetime.datetime(2001, 1, 2))
        self.assertEqual(end, datetime.datetime(2001, 1, 3))

        self.strds_abs.select()
        start, end = self.strds_abs.get_absolute_time()
        self.assertEqual(start, datetime.datetime(2001, 1, 1))
        self.assertEqual(end, datetime.datetime(2001, 1, 3))

    def test_absolute_time_1(self):
        """!Test the registration of maps with absolute time
        """
        tgis.register_maps_in_space_time_dataset(type="rast", name=None,
                 maps="register_map_1,register_map_2",
                 start="2001-01-01", increment="1 day", interval=True)

        map = tgis.RasterDataset("register_map_1@" + tgis.get_current_mapset())
        map.select()
        start, end = map.get_absolute_time()
        self.assertEqual(start, datetime.datetime(2001, 1, 1))
        self.assertEqual(end, datetime.datetime(2001, 1, 2))

        map = tgis.RasterDataset("register_map_2@" + tgis.get_current_mapset())
        map.select()
        start, end = map.get_absolute_time()
        self.assertEqual(start, datetime.datetime(2001, 1, 2))
        self.assertEqual(end, datetime.datetime(2001, 1, 3))

    def test_absolute_time_2(self):
        """!Test the registration of maps with absolute time
        """
        tgis.register_maps_in_space_time_dataset(type="rast", name=None,
                 maps="register_map_1,register_map_2",
                 start="2001-01-01 10:30:01", increment="8 hours", interval=False)

        map = tgis.RasterDataset("register_map_1@" + tgis.get_current_mapset())
        map.select()
        start, end = map.get_absolute_time()
        self.assertEqual(start, datetime.datetime(2001, 1, 1, 10, 30, 1))

        map = tgis.RasterDataset("register_map_2@" + tgis.get_current_mapset())
        map.select()
        start, end = map.get_absolute_time()
        self.assertEqual(start, datetime.datetime(2001, 1, 1, 18, 30, 1))

    def test_absolute_time_3(self):
        """!Test the registration of maps with absolute time.
           The timestamps are set using the C-Interface beforehand, so that the register function needs
           to read the timetsamp from the map metadata.
        """

        ciface = tgis.get_tgis_c_library_interface()
        ciface.write_raster_timestamp("register_map_1", tgis.get_current_mapset(), "1 Jan 2001 10:30:01")
        ciface.write_raster_timestamp("register_map_2", tgis.get_current_mapset(), "1 Jan 2001 18:30:01")

        tgis.register_maps_in_space_time_dataset(type="rast", name=None,
                 maps="register_map_1,register_map_2")

        map = tgis.RasterDataset("register_map_1@" + tgis.get_current_mapset())
        map.select()
        start, end = map.get_absolute_time()
        self.assertEqual(start, datetime.datetime(2001, 1, 1, 10, 30, 1))

        map = tgis.RasterDataset("register_map_2@" + tgis.get_current_mapset())
        map.select()
        start, end = map.get_absolute_time()
        self.assertEqual(start, datetime.datetime(2001, 1, 1, 18, 30, 1))

    def test_relative_time_strds_1(self):
        """!Test the registration of maps with relative time in a
           space time raster dataset
        """

        tgis.register_maps_in_space_time_dataset(type="rast", name=self.strds_rel.get_name(),
                                                 maps="register_map_1,register_map_2", start=0,
                                                 increment=1, unit="day", interval=True)

        map = tgis.RasterDataset("register_map_1@" + tgis.get_current_mapset())
        map.select()
        start, end, unit = map.get_relative_time()
        self.assertEqual(start, 0)
        self.assertEqual(end, 1)
        self.assertEqual(unit, "day")

        map = tgis.RasterDataset("register_map_2@" + tgis.get_current_mapset())
        map.select()
        start, end, unit = map.get_relative_time()
        self.assertEqual(start, 1)
        self.assertEqual(end, 2)
        self.assertEqual(unit, "day")

        self.strds_rel.select()
        start, end, unit = self.strds_rel.get_relative_time()
        self.assertEqual(start, 0)
        self.assertEqual(end, 2)
        self.assertEqual(unit, "day")

    def test_relative_time_strds_2(self):
        """!Test the registration of maps with relative time in a
           space time raster dataset. The timetsamps are set for the maps using the
           C-interface before registration.
        """
        ciface = tgis.get_tgis_c_library_interface()
        ciface.write_raster_timestamp("register_map_1", tgis.get_current_mapset(), "1000000 seconds/1500000 seconds")
        ciface.write_raster_timestamp("register_map_2", tgis.get_current_mapset(), "1500000 seconds/2000000 seconds")

        tgis.register_maps_in_space_time_dataset(type="rast", name=self.strds_rel.get_name(),
                                                 maps="register_map_1,register_map_2")

        map = tgis.RasterDataset("register_map_1@" + tgis.get_current_mapset())
        map.select()
        start, end, unit = map.get_relative_time()
        self.assertEqual(start, 1000000)
        self.assertEqual(end, 1500000)
        self.assertEqual(unit, "seconds")

        map = tgis.RasterDataset("register_map_2@" + tgis.get_current_mapset())
        map.select()
        start, end, unit = map.get_relative_time()
        self.assertEqual(start, 1500000)
        self.assertEqual(end, 2000000)
        self.assertEqual(unit, "seconds")

        self.strds_rel.select()
        start, end, unit = self.strds_rel.get_relative_time()
        self.assertEqual(start, 1000000)
        self.assertEqual(end, 2000000)
        self.assertEqual(unit, "seconds")

    def test_relative_time_1(self):
        """!Test the registration of maps with relative time
        """
        tgis.register_maps_in_space_time_dataset(type="rast", name=None,
                 maps="register_map_1,register_map_2",
                 start=0, increment=1, unit="day", interval=True)

        map = tgis.RasterDataset("register_map_1@" + tgis.get_current_mapset())
        map.select()
        start, end, unit = map.get_relative_time()
        self.assertEqual(start, 0)
        self.assertEqual(end, 1)
        self.assertEqual(unit, "day")

        map = tgis.RasterDataset("register_map_2@" + tgis.get_current_mapset())
        map.select()
        start, end, unit = map.get_relative_time()
        self.assertEqual(start, 1)
        self.assertEqual(end, 2)
        self.assertEqual(unit, "day")

    def test_relative_time_2(self):
        """!Test the registration of maps with relative time
        """
        tgis.register_maps_in_space_time_dataset(type="rast", name=None,
                 maps="register_map_1,register_map_2",
                 start=1000000, increment=500000, unit="seconds", interval=True)

        map = tgis.RasterDataset("register_map_1@" + tgis.get_current_mapset())
        map.select()
        start, end, unit = map.get_relative_time()
        self.assertEqual(start, 1000000)
        self.assertEqual(end, 1500000)
        self.assertEqual(unit, "seconds")

        map = tgis.RasterDataset("register_map_2@" + tgis.get_current_mapset())
        map.select()
        start, end, unit = map.get_relative_time()
        self.assertEqual(start, 1500000)
        self.assertEqual(end, 2000000)
        self.assertEqual(unit, "seconds")

    def test_relative_time_3(self):
        """!Test the registration of maps with relative time. The timetsamps are set beforhand using
           the C-interface.
        """
        ciface = tgis.get_tgis_c_library_interface()
        ciface.write_raster_timestamp("register_map_1", tgis.get_current_mapset(), "1000000 seconds/1500000 seconds")
        ciface.write_raster_timestamp("register_map_2", tgis.get_current_mapset(), "1500000 seconds/2000000 seconds")

        tgis.register_maps_in_space_time_dataset(type="rast", name=None,
                 maps="register_map_1,register_map_2")

        map = tgis.RasterDataset("register_map_1@" + tgis.get_current_mapset())
        map.select()
        start, end, unit = map.get_relative_time()
        self.assertEqual(start, 1000000)
        self.assertEqual(end, 1500000)
        self.assertEqual(unit, "seconds")

        map = tgis.RasterDataset("register_map_2@" + tgis.get_current_mapset())
        map.select()
        start, end, unit = map.get_relative_time()
        self.assertEqual(start, 1500000)
        self.assertEqual(end, 2000000)
        self.assertEqual(unit, "seconds")

if __name__ == '__main__':
    grass.gunittest.test()
