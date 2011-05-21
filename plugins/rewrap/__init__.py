#!/usr/bin/env python
# -*- coding: utf8 -*-
#
#  Rewrap plugin for Gedit
#
#  Copyright (C) 2010 Derek Veit
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Rewrap plugin package

2010-06-18  Version 1.0.0
2010-07-11  Version 1.1.0

Description:
This gedit plugin will re-wrap selected lines of text, e.g. comments,
based on the right margin set in gedit Preferences.  It will maintain
the indentation and any leading comment characters based on the first
line in the selection.

To use it, select the lines of text to be reformatted and then either
select the menu item (Edit > Rewrap > Rewrap) or press its accelerator
keys.

The selection can be made from anywhere on the first and last lines and
will automatically expand to include the full lines.  If no text
selected, the current line will be selected and re-wrapped.

The indentation (if any) of the first line will be used for all lines,
and all other spaces and tabs will be ignored.

If you reformat multiple paragraphs, i.e. blocks of text separated by
blank lines, one blank line will be maintained between them.

If a word (any string of non-whitespace characters) is longer than the
maximum line length, it will not be broken, and it will extend beyond
the maximum line length.  In those cases, you can manually break the
word where you want and then re-wrap as needed.

Two spaces will be placed between a period and a capitalized word to
separate sentences, but this may also put extra spaces where they don't
belong, e.g. between an abbreviation's period and a proper noun's
capital.  You will just have to manually remove those.

When re-wrapping text indented with hard tabs, the tab width set in
gedit Preferences is taken into account.

For a comment that occurs at the end of a line of code, you can use the
"Rewrap trailing comment" feature.  To use this feature, start your
selection just left of the comment marker, e.g. '#' or '//'.

There are a few options that can be set in rewrap.py.


Typical location:
~/.gnome2/gedit/plugins     (for one user)
    or
/usr/lib/gedit-2/plugins    (for all users)

Files:
rewrap.gedit-plugin      -- Gedit reads this to know about the plugin.
rewrap/                  -- Package directory
    __init__.py          -- Package module loaded by Gedit.
    rewrap.py            -- Plugin and plugin helper classes.
    logger.py            -- Module providing simple logging.
    gpl.txt              -- GNU General Public License.

How it loads:
1. Gedit finds rewrap.gedit-plugin in its plugins directory.
2. That file tells Gedit to use Python to load the rewrap module.
3. Python identifies the rewrap directory as the rewrap module.
4. Python loads __init__.py (this file) from the rewrap directory.
5. This file imports the RewrapPlugin class from rewrap.py.
6. Gedit identifies RewrapPlugin as the gedit.Plugin object.
7. Gedit calls methods of RewrapPlugin.

"""
from .rewrap import RewrapPlugin

