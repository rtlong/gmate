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
2010-06-18  Version 1.0.0
2010-06-21  Version 1.0.1
            Added globals for options.
            Improved text selection for special cases.
            Separated 3 functions from the RewrapWindowHelper class.
2010-07-11  Version 1.1.0
            Added "Rewrap trailing comment" action.
            Added "Unwrap" and "Unwrap trailing comment" actions.
            Put the Edit menu items into a submenu.
            Added a configuration dialog.

This module provides the plugin object that Gedit interacts with.

See __init__.py for the description of the plugin.

Classes:
RewrapPlugin       -- object is loaded once by an instance of Gedit
RewrapWindowHelper -- object is constructed for each Gedit window

Each time the same Gedit instance makes a new window, Gedit calls the
plugin's activate method.  Each time RewrapPlugin is so activated, it
constructs a RewrapWindowHelper object to handle the new window.

Settings common to all Gedit windows are attributes of RewrapPlugin.
Settings specific to one window are attributes of RewrapWindowHelper.

"""


ACCELERATOR = '<Shift><Control><Alt>w'
ACCELERATOR_TRAILING = '<Shift><Control>w'
ACCELERATOR_UNWRAP = None
ACCELERATOR_UNWRAP_TRAILING = None
ACCELERATOR_CONFIGURE = None

import json
import os
import re

import gconf
import gedit
import gtk

from .logger import Logger
LOGGER = Logger(level=('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')[2])

from .simpleconfigwindow import SimpleConfigWindow

class RewrapPlugin(gedit.Plugin):
    
    """
    An object of this class is loaded once by a Gedit instance.
    
    It creates a RewrapWindowHelper object for each Gedit main window.
    
    Public methods:
    activate        -- Gedit calls this to start the plugin.
    deactivate      -- Gedit calls this to stop the plugin.
    update_ui       -- Gedit calls this at certain times when the ui
                       changes.
    is_configurable -- Gedit calls this to check if the plugin is
                       configurable.
    
    """
    
    def __init__(self):
        """Initialize attributes for the Rewrap plugin."""
        LOGGER.log()
        
        gedit.Plugin.__init__(self)
        
        self.config = None
        """Preferences settings."""
        
        self.config_window = None
        """The configuration window."""
        
        self.config_file = None
        """The path and filename of the configuration file."""
        
        self._instances = {}
        """Each Gedit window will get a RewrapWindowHelper instance."""
    
    def activate(self, window):
        """Start a RewrapWindowHelper instance for this Gedit window."""
        LOGGER.log()
        self._initialize_configuration()
        self._instances[window] = RewrapWindowHelper(self, window)
        self._instances[window].activate()
    
    def deactivate(self, window):
        """End the RewrapWindowHelper instance for this Gedit window."""
        LOGGER.log()
        self._instances[window].deactivate()
        del self._instances[window]
    
    def update_ui(self, window):
        """Forward Gedit's update_ui command for this window."""
        LOGGER.log()
        self._instances[window].update_ui(window)
    
    def create_configure_dialog(self):
        """Produce the configuration window and provide it to Gedit."""
        LOGGER.log()
        if self.config_window:
            self.config_window.window.present()
        else:
            self.config_window = SimpleConfigWindow(
                config=self.config,
                close_callback=self.on_config_closed,
                title='Rewrap plugin settings')
        return self.config_window.window
    
    def is_configurable(self):
        """Identify for Gedit that Rewrap is not configurable."""
        LOGGER.log()
        return True
    
    def on_config_closed(self):
        """Remove reference to closed configuration window."""
        LOGGER.log()
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, sort_keys=True, indent=4)
        except IOError as detail:
            LOGGER.log('Could not save the configuration file.')
            LOGGER.log(detail)
        else:
            LOGGER.log('Saved the configuration file: %s' % self.config_file)
        self.config_window = None
    
    def _initialize_configuration(self):
        """Load the configuration settings."""
        LOGGER.log()
        
        self.config = {
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
            u'Sentence spacing': {
                u'order': 3,
                u'widget': u'checkbox',
                u'value': True,
                u'tooltip': u'If checked, two spaces are used between a period '
                           u'and a capital letter.',
                },
            }
        
        plugin_path = os.path.dirname(os.path.realpath(__file__))
        self.config_file = os.path.join(plugin_path, 'rewrap.conf')
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        except IOError as detail:
            LOGGER.log('Could not load a configuration file.')
            LOGGER.log(detail)
        else:
            LOGGER.log('Loaded the configuration file: %s' % self.config_file)
    
class RewrapWindowHelper(object):
    
    """
    RewrapPlugin creates a RewrapWindowHelper object for each Gedit
    window.
    
    Public methods:
    deactivate -- RewrapPlugin calls this when Gedit calls deactivate
                  for this window.
    update_ui  -- RewrapPlugin calls this when Gedit calls update_ui for
                  this window.  It activates the menu for the Gedit
                  window and connects the mouse event handler to the
                  current View.  Also, RewrapWindowHelper.__init__ calls
                  this.
    
    """
    
    def __init__(self, plugin, window):
        """Initialize attributes for this Rewrap instance."""
        LOGGER.log()
        
        self._plugin = plugin
        """The RewrapPlugin instance."""
        
        self._window = window
        """The window this RewrapWindowHelper runs on."""
        
        self._menu_ui_id = None
        """The menu's UI identity, saved for removal."""
        self._action_group = None
        """The menu's action group, saved for removal."""
        
        self._start_iter = None
        """The start the text selection."""
        self._end_iter = None
        """The end of the text selection."""
    
    # Public methods
    
    def activate(self):
        """Start this instance of Rewrap."""
        LOGGER.log()
        self._insert_menu()
        self.update_ui(self._window)
        LOGGER.log('Rewrap started for %s' % self._window)
    
    def deactivate(self):
        """End this instance of Rewrap."""
        LOGGER.log()
        self._remove_menu()
        LOGGER.log('Rewrap stopped for %s' % self._window)
        self._window = None
    
    def update_ui(self, window):
        """Make sure the menu is set sensitive."""
        LOGGER.log()
        document = window.get_active_document()
        view = window.get_active_view()
        if document and view and view.get_editable():
            self._action_group.set_sensitive(True)
    
    # Menu
    
    def _insert_menu(self):
        """Create the custom menu item under the Edit menu."""
        LOGGER.log()
        
        manager = self._window.get_ui_manager()
        
        actions = []
        
        name = 'RewrapMenu'
        stock_id = None
        label = 'Rewrap'
        actions.append((name, stock_id, label))
        
        name = 'Rewrap'
        stock_id = None
        label = 'Rewrap'
        accelerator = ACCELERATOR
        tooltip = 'Re-wrap selected lines.'
        callback = lambda action: self._rewrap_selection()
        actions.append((name, stock_id, label, accelerator, tooltip, callback))
        
        name = 'RewrapTrailingComment'
        stock_id = None
        label = 'Rewrap trailing comment'
        accelerator = ACCELERATOR_TRAILING
        tooltip = 'Re-wrap a comment occurring at the end of a line of code.'
        callback = lambda action: self._rewrap_selection(trailing=True)
        actions.append((name, stock_id, label, accelerator, tooltip, callback))
        
        name = 'Unwrap'
        stock_id = None
        label = 'Unwrap'
        accelerator = ACCELERATOR_UNWRAP
        tooltip = 'Un-wrap selected lines.'
        callback = lambda action: self._rewrap_selection(wrap=False)
        actions.append((name, stock_id, label, accelerator, tooltip, callback))
        
        name = 'UnwrapTrailingComment'
        stock_id = None
        label = 'Unwrap trailing comment'
        accelerator = ACCELERATOR_UNWRAP_TRAILING
        tooltip = 'Un-wrap a comment occurring at the end of a line of code.'
        callback = lambda action: self._rewrap_selection(trailing=True,
                                                          wrap=False)
        actions.append((name, stock_id, label, accelerator, tooltip, callback))
        
        name = 'ConfigureRewrap'
        stock_id = None
        label = 'Configure'
        accelerator = ACCELERATOR_CONFIGURE
        tooltip = 'Open the configuration window.'
        callback = lambda action: self._plugin.create_configure_dialog()
        actions.append((name, stock_id, label, accelerator, tooltip, callback))
        
        self._action_group = gtk.ActionGroup("RewrapPluginActions")
        self._action_group.add_actions(actions)
        manager.insert_action_group(self._action_group, -1)
        
        ui_str = """
            <ui>
              <menubar name="MenuBar">
                <menu name="EditMenu" action="Edit">
                  <placeholder name="EditOps_6">
                    <placeholder name="Rewrap">
                      <menu action="RewrapMenu">
                        <menuitem action="Rewrap"/>
                        <menuitem action="RewrapTrailingComment"/>
                        <menuitem action="Unwrap"/>
                        <menuitem action="UnwrapTrailingComment"/>
                        <separator/>
                        <menuitem action="ConfigureRewrap"/>
                      </menu>
                    </placeholder>
                  </placeholder>
                </menu>
              </menubar>
            </ui>
            """
        self._menu_ui_id = manager.add_ui_from_string(ui_str)
        LOGGER.log('Menu added for %s' % self._window)
    
    def _remove_menu(self):
        """Remove the custom menu item."""
        LOGGER.log()
        manager = self._window.get_ui_manager()
        manager.remove_ui(self._menu_ui_id)
        manager.remove_action_group(self._action_group)
        self._action_group = None
        manager.ensure_update()
        LOGGER.log('Menu removed for %s' % self._window)
    
    # Text functions
    
    def _rewrap_selection(self, trailing=False, wrap=True):
        """Re-wrap the currently selected text."""
        LOGGER.log()
        
        indent_chars = self._plugin.config['Indentation characters']['value']
        
        # Get the text
        preceding_text, text = self._get_text_selection(trailing)
        if not text:
            return
        text += '\n\n'
        
        # Get the wrapping parameters
        max_line_length = get_gedit_margin() if wrap else None
        tab_width = get_gedit_tab_width()
        
        indent = re.match('[%s]*' % indent_chars, text).group(0)
        
        offset = (len(preceding_text) +
                  preceding_text.count('\t') * (tab_width - 1))
        if get_gedit_using_hard_tabs():
            trailing_indent = ('\t' * (offset // tab_width) +
                               ' ' * (offset % tab_width))
        else:
            trailing_indent = ' ' * offset
        
        # Remove any pre-existing indentation
        text = '\n'.join(
                line.lstrip(indent_chars) for line in text.splitlines())
        
        paragraphs = get_paragraphs(text)
        if not paragraphs:
            return
        
        # Re-wrap the paragraphs
        sentence_spacing = self._plugin.config['Sentence spacing']['value']
        new_paragraphs = (
            [format_paragraph(paragraphs[0], indent, trailing_indent, offset,
                              max_line_length, tab_width, sentence_spacing)] +
            [format_paragraph(paragraph, trailing_indent + indent, '', 0,
                              max_line_length, tab_width, sentence_spacing) for
                              paragraph in paragraphs[1:]])
        
        # Combine the paragraphs
        if self._plugin.config['Indent empty lines']['value']:
            blank_line = trailing_indent + indent + '\n'
        else:
            blank_line = '\n'
        output = blank_line.join(new_paragraphs)
        
        # Replace the selected text with the reformatted text
        self._replace_text_selection(output)
    
    def _get_text_selection(self, trailing):
        """Expand the selection as appropriate and return the selected text."""
        LOGGER.log()
        
        document = self._window.get_active_document()
        
        # Get the start and end and whether any text is selected.
        if document.get_has_selection():
            self._start_iter, self._end_iter = \
                document.get_selection_bounds()
            has_selection = True
        else:
            # With no selection, the current line will become the selection
            insert_mark = document.get_insert()
            self._start_iter = document.get_iter_at_mark(insert_mark)
            self._end_iter = self._start_iter.copy()
            has_selection = False
        
        # Capture start
        if trailing:
            line_start_iter = self._start_iter.copy()
            line_start_iter.set_line_offset(0)
            preceding_text = document.get_text(line_start_iter,
                                               self._start_iter)
        else:
            preceding_text = ''
            self._start_iter.set_line_offset(0)
        # Capture end
        starts_line = self._end_iter.starts_line()
        if (not starts_line or (starts_line and not has_selection)):
            last_line = document.get_line_count() - 1
            if self._end_iter.get_line() == last_line:
                self._end_iter.forward_to_line_end()
            else:
                self._end_iter.forward_line()
        
        selected_text = document.get_text(self._start_iter,
                                          self._end_iter)
        return preceding_text, selected_text
    
    def _replace_text_selection(self, text):
        """Replace the currently selected text."""
        LOGGER.log()
        document = self._window.get_active_document()
        
        document.begin_user_action()
        
        # Delete the old text
        document.delete(self._start_iter, self._end_iter)
        
        # Mark where the selection starts
        start_mark = document.create_mark(
            mark_name=None,
            where=self._start_iter,
            left_gravity=True)
        
        # Insert the new text
        document.insert(self._start_iter, text)
        
        # Move the selection bound to the start location
        # (The insert is already at the new end.)
        new_start_iter = document.get_iter_at_mark(start_mark)
        document.move_mark_by_name("selection_bound", new_start_iter)
        
        document.end_user_action()

def get_gedit_margin():
    """Return the the preference setting for the right margin, e.g. 80."""
    LOGGER.log()
    gconf_client = gconf.client_get_default()
    margin = gconf_client.get_int('/apps/gedit-2/preferences/editor/'
                                  'right_margin/right_margin_position')
    return margin

def get_gedit_tab_width():
    """Return the the preference setting for the tab width, e.g. 4."""
    LOGGER.log()
    gconf_client = gconf.client_get_default()
    tab_width = gconf_client.get_int('/apps/gedit-2/preferences/editor/'
                                  'tabs/tabs_size')
    return tab_width

def get_gedit_using_hard_tabs():
    """Return the the preference setting for indentation characters."""
    LOGGER.log()
    gconf_client = gconf.client_get_default()
    using_spaces = gconf_client.get_bool('/apps/gedit-2/preferences/editor/'
                                  'tabs/insert_spaces')
    using_hard_tabs = not using_spaces
    return using_hard_tabs

def get_paragraphs(text):
    """Return a list of the paragraphs in the text."""
    LOGGER.log()
    word_re = r'[ \t]*\S+'
    line_re = r'^(?:' + word_re + r')+[ \t]*\n'
    paragraph_re = r'(?:' + line_re + ')+'
    paragraphs = re.findall(paragraph_re, text, re.MULTILINE)
    return paragraphs

def format_paragraph(paragraph, indent, trailing_indent, offset,
                     max_line_length, tab_width, sentence_spacing):
    """Re-wrap the text of one paragraph."""
    LOGGER.log()
    
    indent_width = len(indent) + indent.count('\t') * (tab_width - 1)
    
    new_paragraph = ''
    
    # Get a list of the words in the paragraph
    words = re.findall('\S+', paragraph)
    
    # For trailing comments, start the first line and add the extra indentation
    if offset:
        word = words[0]
        words = words[1:]
        new_paragraph = indent + word
        offset += indent_width + len(word)
        trailing_indent_width = (len(trailing_indent) +
                             trailing_indent.count('\t') * (tab_width - 1))
        indent = trailing_indent + indent
        indent_width = trailing_indent_width + indent_width
    
    for word in words:
        # Add a successive word in a line
        if offset != 0:
            # Determine space between words or sentences
            if sentence_spacing:
                is_after_period = new_paragraph[-1] == '.'
                is_before_capital = word[0] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                is_between_sentences = is_after_period and is_before_capital
                space = '  ' if is_between_sentences else ' '
            else:
                space = ' '
            # Add the word or start a new line
            potential_offset = offset + len(space) + len(word)
            if potential_offset <= max_line_length or not max_line_length:
                new_paragraph = space.join([new_paragraph, word])
                offset = potential_offset
            else:
                new_paragraph += '\n'
                offset = 0
        # Indent and add the first word in a line
        if offset == 0:
            new_paragraph = indent.join([new_paragraph, word])
            offset = indent_width + len(word)
    new_paragraph += '\n'
    return new_paragraph

