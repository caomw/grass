/*!
  \file lib/temporal/lib/connect.c
  
  \brief Temporal GIS Library - connect to TGIS DB
  
  (C) 2012 by the GRASS Development Team
  
  This program is free software under the GNU General Public License
  (>=v2). Read the file COPYING that comes with GRASS for details.
  
  \author Soeren Gebbert 
          Code is based on the dbmi library written by 
          Joel Jones (CERL/UIUC) and Radim Blazek
*/
#include <grass/temporal.h>
#include <grass/glocale.h>

/*!
 * \brief Get TGIS driver name
 * 
 * \return pointer to TGIS driver name
 * \return NULL if not set
 */
char *tgis_get_driver_name(void)
{
    const char *drv;
    
    if ((drv = G__getenv2("TGISDB_DRIVER", G_VAR_MAPSET)))
        return G_store(drv);
    
    return NULL;
}

/*!
 * \brief Get TGIS database name
 * 
 * \return pointer to TGIS database name
 * \return NULL if not set
 */
char *tgis_get_database_name(void)
{
    const char *drv;
    
    if ((drv = G__getenv2("TGISDB_DATABASE", G_VAR_MAPSET)))
        return G_store(drv);
    
    return NULL;
}

/*!
  \brief Set Temporal GIS DB connection settings

  This function sets environmental variables as TGISDB_DRIVER, TGISDB_DATABASE.

  \param connection pointer to dbConnection with default settings
  
  \return DB_OK
 */
int tgis_set_connection(dbConnection * connection)
{
    if (connection->driverName)
	G_setenv2("TGISDB_DRIVER", connection->driverName, G_VAR_MAPSET);

    if (connection->databaseName)
	G_setenv2("TGISDB_DATABASE", connection->databaseName, G_VAR_MAPSET);

    return DB_OK;
}

/*!
  \brief Get Temporal GIS DB connection settings
  
  \param[out] connection pointer to dbConnection to be modified

  \return DB_OK
 */
int tgis_get_connection(dbConnection * connection)
{
    G_zero(connection, sizeof(dbConnection));
    
    connection->driverName = (char *)G__getenv2("TGISDB_DRIVER", G_VAR_MAPSET);
    connection->databaseName = (char *)G__getenv2("TGISDB_DATABASE", G_VAR_MAPSET);

    return DB_OK;
}

#define DRIVER_NAME 0
#define DATABASE_NAME 1

static char *get_mapset_connection_name(const char *mapset, int contype)
{
    const char *val = NULL;
    char *ret_val = NULL;;
    const char *gisdbase = G__getenv("GISDBASE");
    const char *location = G__getenv("LOCATION_NAME");
    int ret;

    ret = G__mapset_permissions2(gisdbase, location, mapset);
    switch (ret) {
    case 0:
        G_warning(_("You don't have permission to access the mapset <%s>"),
                      mapset);
        break;
    case -1:
        G_warning(_("Mapset <%s> does not exist."),
	              mapset);
        break;
    default:
        break;
    }    

    G_create_alt_env();
    G__setenv("GISDBASE", gisdbase);
    G__setenv("LOCATION_NAME", location);
    G__setenv("MAPSET", mapset);
    G__read_mapset_env();
 
    if(contype == DATABASE_NAME) {
        if ((val = G__getenv2("TGISDB_DATABASE", G_VAR_MAPSET)))
            ret_val = G_store(val);
    } else if(contype == DRIVER_NAME) {
        if ((val = G__getenv2("TGISDB_DRIVER", G_VAR_MAPSET)))
            ret_val = G_store(val);
    }

    G_switch_env();
    
    return ret_val;
}


/*!
 * \brief Get TGIS driver name from a specific mapset
 *
 * This function give a warning in case the mapset does not exists
 * or it is not allowed to access the mapset. NULL is returned in this case.
 * 
 * \param mapset The name of the mapset to receive the driver name from
 *
 * \return pointer to TGIS driver name
 * \return NULL if not set 
 */
char *tgis_get_mapset_driver_name(const char *mapset)
{
    return get_mapset_connection_name(mapset, DRIVER_NAME);
}

/*!
 * \brief Get TGIS database name
 * 
 * This function give a warning in case the mapset does not exists
 * or it is not allowed to access the mapset. NULL is returned in this case..
 * 
 * \param mapset The name of the mapset to receive the driver name from
 
 * \return pointer to TGIS database name
 * \return NULL if not set
 */
char *tgis_get_mapset_database_name(const char *mapset)
{
    return get_mapset_connection_name(mapset, DATABASE_NAME);
}

