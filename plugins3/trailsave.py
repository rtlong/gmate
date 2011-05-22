# Copyright (C) 2006-2008 Osmo Salomaa
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

"""Automatically strip all trailing whitespace before saving."""
from gi.repository import GObject, Gedit
from smart_indent import get_crop_spaces_eol, get_insert_newline_eof, get_remove_blanklines_eof
import os

class SaveWithoutTrailingSpacePlugin(GObject.Object, Gedit.ViewActivatable):
    __gtype_name__ = "SaveWithoutTrailingSpacePluginViewActivatable"
    view = GObject.property(type=Gedit.View)
    #Automatically strip all trailing whitespace before saving.

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        document = self.view.get_buffer()
        self.connect_document(document)


    def connect_document(self, doc):
        #Connect to document's 'saving' signal.
        handler_id = doc.connect("saving", self.on_document_saving)
        doc.set_data(self.__class__.__name__, handler_id)

    def do_deactivate(self):
        doc.disconnect(doc.get_data(self.__class__.__name__))

    def on_document_saving(self, doc, *args):
        #Strip trailing spaces in document.
        self.strip_trailing_spaces_on_lines(doc)
        self.strip_trailing_blank_lines(doc)
        return

    def get_language_id(self, doc):
        language = doc.get_language()
        if language is None:
            return 'plain_text'
        return language.get_id()


    def strip_trailing_blank_lines(self, doc):
        #Delete trailing space at the end of the document but let the line
        lng = doc.get_language().get_id()

        if get_remove_blanklines_eof(lng):
            buffer_end = doc.get_end_iter()
            if buffer_end.starts_line():
                itr = buffer_end.copy()
                while itr.backward_line():
                    if not itr.ends_line():
                        itr.forward_to_line_end()
                        break
                doc.delete(itr, buffer_end)

        if get_insert_newline_eof(lng):
            buffer_end = doc.get_end_iter()
            itr = buffer_end.copy()
            if itr.backward_char():
                if not itr.get_text(buffer_end) == "\n":
                    doc.insert(buffer_end, "\n")


    def strip_trailing_spaces_on_lines(self, doc):
        """Delete trailing space at the end of each line."""
        lng = doc.get_language().get_id()
        if get_crop_spaces_eol(lng):
            buffer_end = doc.get_end_iter()
            for line in range(buffer_end.get_line() + 1):
                line_end = doc.get_iter_at_line(line)
                line_end.forward_to_line_end()
                itr = line_end.copy()
                while itr.backward_char():
                    if not itr.get_char() in (" ", "\t"):
                        itr.forward_char()
                        break
                doc.delete(itr, line_end)

