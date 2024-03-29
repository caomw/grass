#include <grass/gis.h>
#include <grass/raster.h>
#include <grass/glocale.h>

int get_item(FILE * fd, int *type, long *cat, double **x, double **y,
	     int *count, struct Categories *labels)
{
    static double *X = NULL;
    static double *Y = NULL;
    static int nalloc = 0;
    char buf[1024];
    char lbl[1024];
    char east[256], north[256];
    double e, n;
    long offset;

    *cat = 0;
    *count = 0;
    *type = 0;

    /* scan until we find the start of a new feature */
    while (G_getl2(buf, sizeof buf, fd)) {
	/* skip comments and blank lines */
	if ((*buf == '#') || (*buf == '\0'))
	    continue;

	G_strip(buf);
	if (*buf == 'A' || *buf == 'a') {
	    *type = 'A';
	    break;
	}
	if (*buf == 'L' || *buf == 'l') {
	    *type = 'L';
	    break;
	}
	if (*buf == 'P' || *buf == 'p') {
	    *type = 'P';
	    break;
	}
    }
    if (*type == 0)
	return 0;

    /* read the feature's data */
    while (1) {
	offset = G_ftell(fd);

	if (!G_getl2(buf, (sizeof buf) - 1, fd))
	    break;

	/* skip comments and blank lines */
	if ((*buf == '#') || (*buf == '\0'))
	    continue;

	G_strip(buf);

	/* if we've found the next feature, rewind to the start of it and complete */
	if (*buf == 'A' || *buf == 'a' ||
	    *buf == 'L' || *buf == 'l' || *buf == 'P' || *buf == 'p') {
	    G_fseek(fd, offset, 0);
	    break;
	}

	/* if we found a cat (and optionally a label), read them and continue to scan */
	if (*buf == '=') {
	    if (sscanf(buf + 1, "%ld", cat) != 1)
		continue;
	    /* probably change this as G_getl2() doesn't store the new line (?) */
	    if (sscanf(buf + 1, "%ld%[^\n]", cat, lbl) == 2) {
		G_strip(lbl);
		Rast_set_c_cat((CELL*) cat, (CELL *) cat, lbl, labels);
	    }
	    continue;
	}
	if (sscanf(buf, "%s %s", east, north) != 2) {
	    G_warning(_("Illegal coordinate <%s, %s>, skipping."), east, north);
	    continue;
	}

	if (!G_scan_northing(north, &n, G_projection())) {
	    G_warning(_("Illegal north coordinate <%s>, skipping."), north);
	    continue;
	}

	if (!G_scan_easting(east, &e, G_projection())) {
	    G_warning(_("Illegal east coordinate <%s>, skipping."), east);
	    continue;
	}

	if (*count >= nalloc) {
	    nalloc += 32;
	    X = (double *)G_realloc(X, nalloc * sizeof(double));
	    Y = (double *)G_realloc(Y, nalloc * sizeof(double));
	}
	X[*count] = e;
	Y[*count] = n;
	(*count)++;
    }
    *x = X;
    *y = Y;
    return 1;
}
