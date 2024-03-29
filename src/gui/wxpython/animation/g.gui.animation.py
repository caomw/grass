#!/usr/bin/env python
############################################################################
#
# MODULE:    Animation
# AUTHOR(S): Anna Kratochvilova
# PURPOSE:   Tool for animating a series of GRASS raster and vector maps
#            or a space time raster dataset
# COPYRIGHT: (C) 2012 by Anna Kratochvilova, and the GRASS Development Team
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
############################################################################

#%module
#% description: Tool for animating a series of raster and vector maps or a space time raster or vector dataset.
#% keywords: general
#% keywords: GUI
#% keywords: display
#%end
#%option G_OPT_R_INPUTS
#% key: rast
#% description: Raster maps to animate
#% required: no
#% guisection: Input
#%end
#%option G_OPT_V_INPUTS
#% key: vect
#% label: Vector maps to animate
#% required: no
#% guisection: Input
#%end
#%option G_OPT_STRDS_INPUT
#% key: strds
#% description: Space time raster dataset to animate
#% required: no
#% guisection: Input
#%end
#%option G_OPT_STVDS_INPUT
#% key: stvds
#% description: Space time vector dataset to animate
#% required: no
#% guisection: Input
#%end

import os

import wx

import grass.script as grass
import grass.temporal as tgis

from core.globalvar import CheckWxVersion
from core.utils import _, GuiModuleMain
from core.giface import StandaloneGrassInterface
from core.layerlist import LayerList
from animation.frame import AnimationFrame, MAX_COUNT
from animation.data import AnimLayer


def main():
    rast = options['rast']
    vect = options['vect']
    strds = options['strds']
    stvds = options['stvds']

    numInputs = 0

    if rast:
        numInputs += 1
    if vect:
        numInputs += 1
    if strds:
        numInputs += 1
    if stvds:
        numInputs += 1
        

    if numInputs > 1:
        grass.fatal(_("%s=, %s=, %s= and %s= are mutually exclusive.") %
                ("rast", "vect", "strds", "stvds"))
        
    if numInputs > 0:
        # We need to initialize the temporal framework in case
        # a space time dataset was set on the command line so that
        # the AnimLayer() class works correctly
        tgis.init()

    layerList = LayerList()
    if rast:
        layer = AnimLayer()
        layer.mapType = 'rast'
        layer.name = rast
        layer.cmd = ['d.rast', 'map={name}'.format(name=rast.split(',')[0])]
        layerList.AddLayer(layer)
    if vect:
        layer = AnimLayer()
        layer.mapType = 'vect'
        layer.name = vect
        layer.cmd = ['d.vect', 'map={name=}'.format(name=vect.split(',')[0])]
        layerList.AddLayer(layer)
    if strds:
        layer = AnimLayer()
        layer.mapType = 'strds'
        layer.name = strds
        layer.cmd = ['d.rast', 'map=']
        layerList.AddLayer(layer)
    if stvds:
        layer = AnimLayer()
        layer.mapType = 'stvds'
        layer.name = stvds
        layer.cmd = ['d.vect', 'map=']
        layerList.AddLayer(layer)

    app = wx.App()
    if not CheckWxVersion([2, 9]):
        wx.InitAllImageHandlers()

    frame = AnimationFrame(parent=None, giface=StandaloneGrassInterface())
    frame.CentreOnScreen()
    frame.Show()
    if len(layerList) >= 1:
        frame.SetAnimations([layerList] + [None] * (MAX_COUNT - 1))
    app.MainLoop()

if __name__ == '__main__':
    options, flags = grass.parser()

    GuiModuleMain(main)
