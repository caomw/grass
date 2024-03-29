/*!
  \file lib/display/r_raster.c

  \brief Display Library - Raster graphics subroutines

  (C) 2001-2009, 2011 by the GRASS Development Team

  This program is free software under the GNU General Public License
  (>=v2). Read the file COPYING that comes with GRASS for details.

  \author Original author CERL
  \author Monitors support by Martin Landa <landa.martin gmail.com>
*/

#include <grass/config.h>

#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <grass/gis.h>
#include <grass/glocale.h>
#include <grass/display.h>

#include "driver.h"

extern const struct driver *PNG_Driver(void);
extern const struct driver *PS_Driver(void);
extern const struct driver *HTML_Driver(void);
#ifdef USE_CAIRO
extern const struct driver *Cairo_Driver(void);
#endif

static int read_env_file(const char *);

static struct {
    double t, b, l, r;
} screen;

static void init(void)
{
    const char *fenc = getenv("GRASS_ENCODING");
    const char *font = getenv("GRASS_FONT");
    const char *line_width = getenv("GRASS_LINE_WIDTH");
    const char *text_size = getenv("GRASS_TEXT_SIZE");
    const char *frame = getenv("GRASS_FRAME");

    D_font(font ? font : "romans");

    if (fenc)
	D_encoding(fenc);

    if (line_width)
	COM_Line_width(atof(line_width));

    if (text_size) {
	double s = atof(text_size);
	D_text_size(s, s);
    }

    D_text_rotation(0);

    if (frame) {
	sscanf(frame, "%lf,%lf,%lf,%lf", &screen.t, &screen.b, &screen.l, &screen.r);
	COM_Set_window(screen.t, screen.b, screen.l, screen.r);
    }
    else
	COM_Get_window(&screen.t, &screen.b, &screen.l, &screen.r);
}

int read_env_file(const char *path)
{
    FILE *fd;
    char buf[1024];
    char **token;
    
    fd = fopen(path, "r");
    if (!fd)
	return -1;

    token = NULL;
    while (G_getl2(buf, sizeof(buf) - 1, fd) != 0) {
	token = G_tokenize(buf, "=");
	if (G_number_of_tokens(token) != 2)
	    continue;
	G_debug(3, "\tread_env_file(): %s=%s", token[0], token[1]);
	G_putenv(token[0], token[1]);
	G_free_tokens(token);
	token = NULL;
    }

    return 0;
}

/*!
  \brief Open display driver

  Default display driver is Cairo, if not available PNG is used.

  \return 0 on success
  \return 1 no monitor defined
*/
int D_open_driver(void)
{
    const char *p, *m;
    
    G_debug(1, "D_open_driver():");
    p = getenv("GRASS_RENDER_IMMEDIATE");
    m = G__getenv("MONITOR");
    
    if (m && G_strncasecmp(m, "wx", 2) == 0) {
	/* wx monitors always use GRASS_RENDER_IMMEDIATE. */
	p = NULL; /* use default display driver */
    } else if (m) {
	char *env;
	const char *v;
	char *u_m;
	
	if (p)
	    G_warning(_("%s variable defined, %s ignored"),
		      "MONITOR", "GRASS_RENDER_IMMEDIATE");
	/* GRASS variable names should be upper case. */
	u_m = G_store_upper(m);

	env = NULL;
	G_asprintf(&env, "MONITOR_%s_MAPFILE", u_m);
	v = G__getenv(env);
	p = m;

	if (v) {
	    if (G_strcasecmp(p, "ps") == 0)
		G_putenv("GRASS_PSFILE", v);
	    else
		G_putenv("GRASS_PNGFILE", v);
	}
	
	G_asprintf(&env, "MONITOR_%s_ENVFILE", u_m);
	v = G__getenv(env);
	if (v) 
	    read_env_file(v);
    }
    
    const struct driver *drv =
	(p && G_strcasecmp(p, "PNG")   == 0) ? PNG_Driver() :
	(p && G_strcasecmp(p, "PS")    == 0) ? PS_Driver() :
	(p && G_strcasecmp(p, "HTML")  == 0) ? HTML_Driver() :
#ifdef USE_CAIRO
	(p && G_strcasecmp(p, "cairo") == 0) ? Cairo_Driver() :
	Cairo_Driver();
#else
	PNG_Driver();
#endif
	
    if (p && G_strcasecmp(drv->name, p) != 0)
	G_warning(_("Unknown display driver <%s>"), p);
    G_verbose_message(_("Using display driver <%s>..."), drv->name);
    LIB_init(drv);

    init();

    if (!getenv("GRASS_RENDER_IMMEDIATE") && !m)
	return 1;

    return 0;
}

/*!
  \brief Close display driver

  If GRASS_NOTIFY is defined, run notifier.
*/
void D_close_driver(void)
{
    const char *cmd = getenv("GRASS_NOTIFY");

    COM_Graph_close();

    if (cmd)
	system(cmd);
}

/*!
  \brief Append command to the cmd file

  Cmd file is created by d.mon by defining GRASS variable
  \c MONITOR_<name>_CMDFILE, where \c \<name\> is the upper case name of
  the monitor.

  Command string is usually generated by G_recreate_command(), NULL is
  used to clean up list of commands (see d.erase command).

  \param cmd string buffer with command or NULL

  \return 0 no monitor selected
  \return -1 on error
  \return 1 on success
*/
int D_save_command(const char *cmd)
{
    const char *mon_name, *mon_cmd;
    char *env, *flag, *u_mon_name;
    FILE *fd;

    G_debug(1, "D_save_command(): %s", cmd);

    mon_name = G__getenv("MONITOR");
    if (!mon_name || /* if no monitor selected */
	/* or wx monitor selected and display commands called by the monitor */
	(G_strncasecmp(mon_name, "wx", 2) == 0 &&
	 getenv("GRASS_RENDER_IMMEDIATE")))
	return 0;

    /* GRASS variable names should be upper case. */
    u_mon_name = G_store_upper(mon_name);

    env = NULL;
    G_asprintf(&env, "MONITOR_%s_CMDFILE", u_mon_name);
    mon_cmd = G__getenv(env);
    if (!mon_cmd)
	return 0;

    if (cmd)
	flag = "a";
    else
	flag = "w";

    fd = fopen(mon_cmd, flag);
    if (!fd) {
	G_warning(_("Unable to open file '%s'"), mon_cmd);
	return -1;
    }

    if (cmd)
	fprintf(fd, "%s\n", cmd);
    
    fclose(fd);

    return 1;
}

/*!
  \brief Erase display (internal use only)
*/
void D__erase(void)
{
    COM_Erase();
}

/*!
  \brief Set text size (width and height)
 
  \param width text pixel width
  \param height text pixel height
*/
void D_text_size(double width, double height)
{
    COM_Text_size(width, height);
}

/*!
  \brief Set text rotation

  \param rotation value
*/
void D_text_rotation(double rotation)
{
    COM_Text_rotation(rotation);
}

/*!
  \brief Draw text
  
  Writes <em>text</em> in the current color and font, at the current text
  width and height, starting at the current screen location.
  
  \param text text to be drawn
*/
void D_text(const char *text)
{
    COM_Text(text);
}

/*!
  \brief Choose font
 
  Set current font to <em>font name</em>.
  
  \param name font name
*/
void D_font(const char *name)
{
    COM_Set_font(name);
}

/*!
  \brief Set encoding

  \param name encoding name
*/
void D_encoding(const char *name)
{
    COM_Set_encoding(name);
}

/*!
  \brief Get font list

  \param[out] list list of font names
  \param[out] number of items in the list
*/
void D_font_list(char ***list, int *count)
{
    COM_Font_list(list, count);
}

/*!
  \brief Get font info

  \param[out] list list of font info
  \param[out] number of items in the list
*/
void D_font_info(char ***list, int *count)
{
    COM_Font_info(list, count);
}

/*!
 * \brief get graphical clipping window
 *
 * Queries the graphical clipping window (origin is top right)
 *
 *  \param[out] t top edge of clip window
 *  \param[out] b bottom edge of clip window
 *  \param[out] l left edge of clip window
 *  \param[out] r right edge of clip window
 *  \return ~
 */

void D_get_clip_window(double *t, double *b, double *l, double *r)
{
    COM_Get_window(t, b, l, r);
}

/*!
 * \brief set graphical clipping window
 *
 * Sets the graphical clipping window to the specified rectangle
 *  (origin is top right)
 *
 *  \param t top edge of clip window
 *  \param b bottom edge of clip window
 *  \param l left edge of clip window
 *  \param r right edge of clip window
 *  \return ~
 */

void D_set_clip_window(double t, double b, double l, double r)
{
    if (t < screen.t) t = screen.t;
    if (b > screen.b) b = screen.b;
    if (l < screen.l) l = screen.l;
    if (r > screen.r) r = screen.r;

    COM_Set_window(t, b, l, r);
}

/*!
 * \brief get graphical window (frame)
 *
 * Queries the graphical frame (origin is top right)
 *
 *  \param[out] t top edge of frame
 *  \param[out] b bottom edge of frame
 *  \param[out] l left edge of frame
 *  \param[out] r right edge of frame
 *  \return ~
 */

void D_get_frame(double *t, double *b, double *l, double *r)
{
    *t = screen.t;
    *b = screen.b;
    *l = screen.l;
    *r = screen.r;
}

/*!
 * \brief set graphical clipping window to map window
 *
 * Sets the graphical clipping window to the pixel window that corresponds
 * to the current database region.
 *
 *  \param ~
 *  \return ~
 */

void D_set_clip_window_to_map_window(void)
{
    D_set_clip_window(
	D_get_d_north(), D_get_d_south(),
	D_get_d_west(), D_get_d_east());
}

/*!
 * \brief set clipping window to screen window
 *
 * Sets the clipping window to the pixel window that corresponds to the
 * full screen window. Off screen rendering is still clipped.
 *
 *  \param ~
 *  \return ~
 */

void D_set_clip_window_to_screen_window(void)
{
    COM_Set_window(screen.t, screen.b, screen.l, screen.r);
}

