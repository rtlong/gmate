# Copyright (C) 2009 Alexandre da Silva
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

"""Automatically detects if file resides in a ruby on rails application and set the properly language."""

from gi.repository import GObject, Gedit, GtkSource
import os

class RubyOnRailsLoaderView(GObject.Object, Gedit.ViewActivatable):
    __gtype_name__ = "RubyOnRailsPluginViewActivatable"
    view = GObject.property(type=Gedit.View)

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        self.connect_document()

    def do_deactivate(self):
        document = self.view.get_buffer()
        document.disconnect(document.get_data(self.__class__.__name__))
        document.set_data(self.__class__.__name__, None)

    def connect_document(self):
        document = self.view.get_buffer()
        handler_id = document.connect("loaded", self.on_document_load)
        document.set_data(self.__class__.__name__, handler_id)

    def on_document_load(self, doc, *args):
        language = doc.get_language()
        if language:
            lang = language.get_id()
            if lang == 'ruby':
                uri = doc.get_uri_for_display()
                if self.get_in_rails(uri):
                    lang = GtkSource.LanguageManager.get_default().get_language('rubyonrails')
                    doc.set_language(lang)
                    self.view.get_toplevel().get_ui_manager().ensure_update()

    def get_in_rails(self, uri):
        rails_root = self.view.get_data('RailsLoaderRoot')
        if rails_root:
            return rails_root
        base_dir = os.path.dirname(uri)
        depth = 10
        while depth > 0:
            depth -= 1
            app_dir = os.path.join(base_dir, 'app')
            config_dir = os.path.join(base_dir, 'config')
            environment_file = os.path.join(base_dir, 'config', 'environment.rb')
            if os.path.isdir(app_dir) and os.path.isdir(config_dir) and os.path.isfile(environment_file):
                rails_root = base_dir
                break
            else:
                base_dir = os.path.abspath(os.path.join(base_dir, '..'))
        if rails_root:
            self.view.set_data('RailsLoaderRoot', rails_root)
            return True
        return False

