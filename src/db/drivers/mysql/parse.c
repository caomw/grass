
/**********************************************************
 * MODULE:    mysql
 * AUTHOR(S): Radim Blazek (radim.blazek@gmail.com)
 * PURPOSE:   MySQL database driver
 * COPYRIGHT: (C) 2001 by the GRASS Development Team
 *            This program is free software under the 
 *            GNU General Public License (>=v2). 
 *            Read the file COPYING that comes with GRASS
 *            for details.
 **********************************************************/
#include <stdlib.h>
#include <string.h>

#include <grass/gis.h>
#include <grass/dbmi.h>
#include <grass/glocale.h>

#include "globals.h"
#include "proto.h"

/*
 * \brief Parse connection string in form:
 *    1) 'database_name'
 *    2) 'host=xx,port=xx,dbname=xx'
 *  \return DB_OK Success
 *  \return DB_FAILED Failed to parse database
 */
int parse_conn(const char *str, CONNPAR * conn)
{
    int i;
    char **tokens, delm[2];

    G_debug(3, "parse_conn : %s", str);

    /* reset */
    conn->host = NULL;
    conn->port = 0;
    conn->dbname = NULL;
    conn->user = NULL;
    conn->password = NULL;

    if (strchr(str, '=') == NULL) {	/*db name only */
	conn->dbname = G_store(str);
    }
    else {
	delm[0] = ',';
	delm[1] = '\0';
	tokens = G_tokenize(str, delm);
	i = 0;
	while (tokens[i]) {
	    G_debug(3, "token %d : %s", i, tokens[i]);
	    if (strncmp(tokens[i], "host", 4) == 0) {
		conn->host = G_store(tokens[i] + 5);
	    }
	    else if (strncmp(tokens[i], "port", 4) == 0) {
		long port = atol(tokens[i] + 5);

		if (port <= 0) {
		    db_d_append_error("%s %s",
				      _("Wrong port number in MySQL database "
					"definition: "),
				      tokens[i] + 5);
		    return DB_FAILED;
		}
		conn->port = (unsigned int)port;
	    }
	    else if (strncmp(tokens[i], "dbname", 6) == 0) {
		conn->dbname = G_store(tokens[i] + 7);
	    }
	    else if (strncmp(tokens[i], "user", 4) == 0) {
		G_warning(_("'user' in database definition "
			    "is not supported, use db.login"));
	    }
	    else if (strncmp(tokens[i], "password", 8) == 0) {
		G_warning(_("'password' in database definition "
			    "is not supported, use db.login"));
	    }
	    else {
		db_d_append_error("%s %s",
				  _("Unknown option in database definition "
				    "for MySQL: "),
				  tokens[i]);
		return DB_FAILED;
	    }
	    i++;
	}
	G_free_tokens(tokens);
    }

    return DB_OK;
}
