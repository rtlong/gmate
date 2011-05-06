from gi.repository import Gedit, Gtk, Gio, Gdk, GdkPixbuf
#import gconf
#import pygtk
#pygtk.require('2.0')
import os, os.path
from urllib import pathname2url, url2pathname
from suggestion import FuzzySuggestion
from util import debug
import util

app_string = "Fuzzy open"

ui_str="""<ui>
<menubar name="MenuBar">
  <menu name="FileMenu" action="File">
    <placeholder name="FileOps_2">
      <menuitem name="FuzzyOpen" action="FuzzyOpenAction"/>
    </placeholder>
  </menu>
</menubar>
</ui>
"""

# essential interface
class FuzzyOpenPluginInstance:
    def __init__(self, plugin):
        self._window = plugin.window
        self._plugin = plugin
        self._encoding = Gedit.encoding_get_current()
        self._rootpath = os.getcwd()
        self._rootdir = "file://" + self._rootpath
        self._show_hidden = False
        self._suggestion = None
        self._git = False
        self._liststore = None
        self._last_pattern = ""
        self._init_glade()
        self._insert_menu()
        self.connect_to_fb_bus()

    def deactivate( self ):
        self._remove_menu()
        self._action_group = None
        self._window = None
        self._plugin = None
        self._liststore = None;
        self._window.get_message_bus().disconnect(self._file_handler_id)

    def update_ui( self ):
        self._window.get_ui_manager().ensure_update()

    # MENU STUFF
    def _insert_menu( self ):
        manager = self._window.get_ui_manager()
        self._action_group = Gtk.ActionGroup( "FuzzyOpenPluginActions" )
        fuzzyopen_menu_action = Gtk.Action( name="FuzzyOpenMenuAction", label="Fuzzy", tooltip="Fuzzy tools", stock_id=None )
        self._action_group.add_action( fuzzyopen_menu_action )
        fuzzyopen_action = Gtk.Action( name="FuzzyOpenAction", label="Fuzzy Open...\t", tooltip="Open file by autocomplete...", stock_id=Gtk.STOCK_JUMP_TO )
        fuzzyopen_action.connect( "activate", lambda a: self.on_fuzzyopen_action() )
        self._action_group.add_action_with_accel( fuzzyopen_action, "<Ctrl><Shift>o" )
        manager.insert_action_group( self._action_group, 0 )
        self._ui_id = manager.new_merge_id()
        manager.add_ui_from_string( ui_str )
        manager.ensure_update()

    def _remove_menu( self ):
        manager = self._window.get_ui_manager()
        manager.remove_ui( self._ui_id )
        manager.remove_action_group( self._action_group )

    # UI DIALOGUES
    def _init_glade( self ):
        self._fuzzyopen_glade = Gtk.Builder()
        self._fuzzyopen_glade.add_from_file(os.path.join(os.path.dirname( __file__ ), "window.glade"))
        #setup window
        self._fuzzyopen_window = self._fuzzyopen_glade.get_object( "FuzzyOpenWindow" )
        self._fuzzyopen_window.connect("key-release-event", self.on_window_key)
        self._fuzzyopen_window.connect("delete_event", self._fuzzyopen_window.hide_on_delete)
        self._fuzzyopen_window.set_transient_for(self._window)
        #setup buttons
        self._fuzzyopen_glade.get_object( "ok_button" ).connect( "clicked", self.open_selected_item )
        self._fuzzyopen_glade.get_object( "cancel_button" ).connect( "clicked", lambda a: self._fuzzyopen_window.hide())
        #setup entry field
        self._glade_entry_name = self._fuzzyopen_glade.get_object( "entry_name" )
        self._glade_entry_name.connect("key-release-event", self.on_pattern_entry)
        #setup list field
        self._hit_list = self._fuzzyopen_glade.get_object( "hit_list" )
        self._hit_list.connect("select-cursor-row", self.on_select_from_list)
        self._hit_list.connect("button_press_event", self.on_list_mouse)
        self._liststore = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str)
        self._hit_list.set_model(self._liststore)
        column0 = Gtk.TreeViewColumn("Icon", Gtk.CellRendererPixbuf(), pixbuf=0)
        column0.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column1 = Gtk.TreeViewColumn("File", Gtk.CellRendererText(), markup=1)
        column1.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self._hit_list.append_column(column0)
        self._hit_list.append_column(column1)
        self._hit_list.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)

    #mouse event on list
    def on_list_mouse( self, widget, event ):
        if event.type == Gdk.EventType._2BUTTON_PRESS:
            self.open_selected_item( event )

    #key selects from list (passthrough 3 args)
    def on_select_from_list(self, widget, event):
        self.open_selected_item(event)

    #keyboard event on entry field
    def on_pattern_entry( self, widget, event ):
        oldtitle = self._fuzzyopen_window.get_title().replace(" * too many hits", "")
        if event.keyval == Gdk.KEY_Return:
            self.open_selected_item( event )
            return
        pattern = self._glade_entry_name.get_text()
        if pattern == self._last_pattern:
            return
        self._last_pattern = pattern
        suggestions = self._suggestion.suggest(pattern)
        self._liststore.clear()
        for suggestion in suggestions:
            self._liststore.append(suggestion)
            self._fuzzyopen_window.set_title(oldtitle)
            selected = []
            self._hit_list.get_selection().selected_foreach(self.foreach, selected)
            if len(selected) == 0:
                iter = self._liststore.get_iter_first()
            if iter != None:
                self._hit_list.get_selection().select_iter(iter)

    #on menuitem activation (incl. shortcut)
    def on_fuzzyopen_action(self):
        if self._file_handler_id is not None:
            # Until I learn how to access GSettings this is moot.
            # self._show_hidden =
            self._fuzzyopen_window.set_title(app_string + " (File Browser root)")
        else:
            self._fuzzyopen_window.set_title(app_string + " (Working dir): " + self._rootdir)
        self._git = self.check_git(self._rootpath)
        self._suggestion = FuzzySuggestion( self._rootpath, self._show_hidden, self._git )
        self._fuzzyopen_window.show()
        self._glade_entry_name.select_region(0,-1)
        self._glade_entry_name.grab_focus()

    def connect_to_fb_bus(self):
        bus = self._window.get_message_bus()
        self._file_handler_id = bus.connect('/plugins/filebrowser', 'root_changed', self.set_rootdir, None)

    def set_rootdir(self, bus, location, user_data):
        self._rootdir = location.props.location.get_uri()
        self._rootpath = location.props.location.get_path()

    #check if it is a git repository
    def check_git( self, path ):
        block = os.path.join(path, '').split('/')
        for i in range(0, len(block)):
            current_path = '/'.join(block[:i])
            if os.path.exists(os.path.join(current_path, '.git')):
                return True
            return False

    #on any keyboard event in main window
    def on_window_key( self, widget, event ):
        if event.keyval == Gdk.KEY_Escape:
            self._fuzzyopen_window.hide()

    def foreach(self, model, path, iter, selected):
        selected.append(model.get_value(iter, 2))

    #open file in selection and hide window
    def open_selected_item( self, event ):
        selected = []
        self._hit_list.get_selection().selected_foreach(self.foreach, selected)
        for selected_file in  selected:
            self._open_file ( selected_file )
            self._fuzzyopen_window.hide()

    #opens (or switches to) the given file
    def _open_file( self, filename ):
        uri = self._rootdir + "/" + pathname2url(filename)
        Gedit.commands_load_location(self._window, uri, self._encoding)

