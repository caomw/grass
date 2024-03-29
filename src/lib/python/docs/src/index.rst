GRASS GIS Python library documentation
==========================================

Python, a widely used general-purpose, high-level programming language 
provides a powerful scripting interface. Being easy-to-use yet 
powerful, it enables users to efficiently exploit the capabilities of 
the GRASS GIS software. Python scripts for GRASS GIS can be written at 
high level (GRASS GIS modules) as well as at low level (GRASS GIS 
libraries) through a dedicated interface. The graphical user interface 
and the GRASS GIS Temporal Framework are entirely written in Python.

A set of packages is provided to the user in order to provide functionality
at various levels:

* **script package**: Python interface to launch GRASS GIS modules in scripts
* **PyGRASS documentation**: PyGRASS is an object-oriented Python Application 
  Programming Interface (API) for GRASS GIS which uses the GRASS C API as 
  backend but additionally offers a convenient interface to the GRASS GIS 
  modules
* **GRASS GIS Temporal Framework**: implements the temporal GIS functionality
  of GRASS GIS and provides an API to implement spatio-temporal processing modules
* **exceptions package**: FIXME
* **imaging package**: library to create animated images and films
* **Testing GRASS GIS source code and modules**: (gunittest package
* **pydispatch package**: Multiple-producer-multiple-consumer signal-dispatching

Contents:

.. toctree::
   :maxdepth: 3

   script
   pygrass_index
   temporal_framework
   exceptions
   imaging
   gunittest_testing
   pydispatch

