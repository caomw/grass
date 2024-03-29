MODULE_TOPDIR = ../..

SUBDIRS = docs animation mapswipe gmodeler rlisetup psmap dbmgr vdigit iclass gcp timeline tplot
EXTRA_CLEAN_FILES = menustrings.py build_ext.pyc xml/menudata.xml xml/module_tree_menudata.xml

include $(MODULE_TOPDIR)/include/Make/Dir.make
include $(MODULE_TOPDIR)/include/Make/Python.make

DSTDIR = $(GUIDIR)/wxpython

SRCFILES := $(wildcard icons/*.py scripts/*.py xml/*) \
	$(wildcard animation/* core/*.py dbmgr/* gcp/*.py gmodeler/* \
	gui_core/*.py iclass/* lmgr/*.py location_wizard/*.py mapwin/*.py mapdisp/*.py \
	mapswipe/* modules/*.py nviz/*.py psmap/* rlisetup/* timeline/* vdigit/* \
	vnet/*.py web_services/*.py wxplot/*.py iscatt/*.py tplot/*) \
	gis_set.py gis_set_error.py wxgui.py README

DSTFILES := $(patsubst %,$(DSTDIR)/%,$(SRCFILES)) \
	$(patsubst %.py,$(DSTDIR)/%.pyc,$(filter %.py,$(SRCFILES)))

PYDSTDIRS := $(patsubst %,$(DSTDIR)/%,animation core dbmgr gcp gmodeler \
	gui_core iclass lmgr location_wizard mapwin mapdisp modules nviz psmap \
	mapswipe vdigit wxplot web_services rlisetup vnet timeline iscatt tplot)


DSTDIRS := $(patsubst %,$(DSTDIR)/%,icons scripts xml)

default: $(DSTFILES)
	-$(MAKE) $(DSTDIR)/xml/module_items.xml
	-$(MAKE) xml/menudata.xml
	-$(MAKE) xml/module_tree_menudata.xml
	-$(MAKE) menustrings.py
	$(MAKE) parsubdirs


$(DSTDIR)/%: % | $(PYDSTDIRS) $(DSTDIRS)
	$(INSTALL_DATA) $< $@

xml/menudata.xml: core/toolboxes.py
	$(call run_grass,$(PYTHON) $< > $@)

xml/module_tree_menudata.xml: core/toolboxes.py
	$(call run_grass,$(PYTHON) $< "module_tree" > $@)

menustrings.py: core/menutree.py $(DSTDIR)/xml/menudata.xml $(DSTDIR)/xml/module_tree_menudata.xml $(DSTDIR)/xml/menudata_modeler.xml $(DSTDIR)/xml/menudata_psmap.xml
	@echo "# This is a generated file.\n" > $@
	$(call run_grass,$(PYTHON) $< "manager" >> $@)
	$(call run_grass,$(PYTHON) $< "module_tree" >> $@)
	$(call run_grass,$(PYTHON) $< "modeler" >> $@)
	$(call run_grass,$(PYTHON) $< "psmap" >> $@)

$(DSTDIR)/xml/module_items.xml: tools/build_modules_xml.py
	@echo "Generating interface description for all modules..."
	$(call run_grass,$(PYTHON) $< > $@)

$(PYDSTDIRS): %: | $(DSTDIR)
	$(MKDIR) $@

$(DSTDIRS): %: | $(DSTDIR)
	$(MKDIR) $@

$(DSTDIR):
	$(MKDIR) $@
