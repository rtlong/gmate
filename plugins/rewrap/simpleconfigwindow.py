#!/usr/bin/env python
# -*- coding: utf8 -*-
#
#  simpleconfigwindow module
#
#  Copyright (C) 2010 Derek Veit
#
#  This program is free software: you can redistribute it and/or modify it under
#  the terms of the GNU General Public License as published by he Free Software
#  Foundation, either version 3 of the License, or (at your option) any later
#  version.
#  
#  This program is distributed in the hope that it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
#  FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
#  details.
#  
#  You should have received a copy of the GNU General Public License along with
#  this program.  If not, see <http://www.gnu.org/licenses/>.

"""
2010-06-26

This module provides a class for creating a simple configuration window.
"""

import gtk

if __name__ == '__main__':
    from logger import Logger
else:
    from .logger import Logger

LOGGER = Logger(level=('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')[2])

class SimpleConfigWindow(object):
    
    """An easy to set up configuration window."""
    
    def __init__(self, config, close_callback=None, title=None):
        """Initialize the SimpleConfigWindow attributes."""
        LOGGER.log()
        
        self.config = config
        """
        The configuration dictionary in this format:
        {
            u'Indentation characters': {
                u'order': 1,
                u'widget': u'entry',
                u'value': u' \t#/;*!-',
                u'tooltip': u'At the beginnings of lines, these characters '
                            u'will be treated as part of indentation or '
                            u'comment markers.',
                },
            u'Indent empty lines': {
                u'order': 2,
                u'widget': u'checkbox',
                u'value': True,
                u'tooltip': u'If checked, indentation and comment markers are '
                            u'maintained on blank lines between paragraphs.',
                },
        }
        """
        
        self.close_callback = close_callback
        """Function to call when the window is closed."""
        
        self.title = title
        """The window title."""
        
        self.window = None
        """The top-level window."""
        
        self.vbox = None
        """Container of the settings widgets."""
        
        self.on_configure_event_handler_id = None
        """ID of the handler that constrains the window height."""
        
        self.widgets = {}
        """The settings widgets keyed by their setting strings."""
        
        self._create()
    
    def _create(self):
        """Create the window and outer containers."""
        
        self.window = gtk.Window()
        
        if self.title:
            self.window.set_title(self.title)
        
        hbox = gtk.HBox()
        self.window.add(hbox)
        hbox.show()
        
        self.vbox = gtk.VBox()
        hbox.pack_start(self.vbox, padding=5)
        self.vbox.show()
        
        for setting, params in sorted(self.config.iteritems(),
                                      key=lambda pair: pair[1]['order']):
            if params['widget'] == 'checkbox':
                self.add_checkbox(setting)
            elif params['widget'] == 'entry':
                self.add_entry(setting)
        self.window.show_all()
        
        self.on_configure_event_handler_id = \
            self.window.connect('configure-event', self.on_configure_event)
        
        if self.close_callback:
            self.window.connect('delete-event', self.on_delete_event)
    
    # Public methods
    
    def add_checkbox(self, setting):
        """Add a checkbox setting to the window."""
        LOGGER.log()
        checkbutton = gtk.CheckButton(setting)
        self.widgets[setting] = checkbutton
        checkbutton.set_name(setting)
        checkbutton.set_tooltip_text(self.config[setting]['tooltip'])
        checkbutton.set_active(self.config[setting]['value'])
        checkbutton.connect('toggled', self.on_toggled, setting)
        self.vbox.pack_start(checkbutton, expand=False, padding=5)
        checkbutton.show()
        return checkbutton
    
    def add_entry(self, setting):
        """Add a text entry setting to the window."""
        LOGGER.log()
        hbox = gtk.HBox(spacing=5)
        label = gtk.Label(str=setting)
        hbox.pack_start(label, expand=False)
        entry = gtk.Entry()
        self.widgets[setting] = entry
        entry.set_name(setting)
        entry.set_text(self.config[setting]['value'].encode('unicode_escape'))
        entry.set_tooltip_text(self.config[setting]['tooltip'])
        entry.connect('changed', self.on_changed, setting)
        hbox.pack_start(entry)
        self.vbox.pack_start(hbox, expand=False, padding=5)
        hbox.show_all()
        return entry
    
    def update(self):
        """Update the GUI for values that have otherwise changed."""
        LOGGER.log()
        for setting, params in self.config.iteritems():
            if setting in self.widgets:
                widget = self.widgets[setting]
                if params['widget'] == 'checkbox':
                    widget.set_active(params['value'])
                elif params['widget'] == 'entry':
                    widget.set_text(params['value'].encode('unicode_escape'))

    # Event handlers
    
    def on_configure_event(self, widget, event):
        """Set configuration window sizing constraint."""
        LOGGER.log()
        window = widget
        window.disconnect(self.on_configure_event_handler_id)
        width, height = window.get_size()
        unlikely_height_inc = height * 1000
        window.set_geometry_hints(height_inc=unlikely_height_inc)
    
    def on_delete_event(self, widget, event):
        """Go away when window is closed."""
        LOGGER.log()
        self.close_callback()
    
    def on_toggled(self, widget, setting):
        """Update configuration per UI input."""
        LOGGER.log()
        LOGGER.log("self.config['%s']['value']: %r" % (
                    setting, self.config[setting]['value']))
        self.config[setting]['value'] = widget.get_active()
        LOGGER.log("self.config['%s']['value']: %r" % (
                    setting, self.config[setting]['value']))
    
    def on_changed(self, widget, setting):
        """Update configuration per UI input."""
        LOGGER.log()
        LOGGER.log("self.config['%s']['value']: %r" % (
                    setting, self.config[setting]['value']))
        escaped_text = widget.get_text()
        # Prevent a trailing backslash prior to decoding escapes
        if (len(escaped_text) - len(escaped_text.rstrip('\\'))) % 2:
            escaped_text = escaped_text[:-1]
        self.config[setting]['value'] = escaped_text.decode('string_escape')
        LOGGER.log("self.config['%s']['value']: %r" % (
                    setting, self.config[setting]['value']))
    

