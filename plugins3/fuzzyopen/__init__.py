from gi.repository import GObject, Gedit

from fuzzyopen import FuzzyOpenPluginInstance
from config import FuzzyOpenConfigWindow

# STANDARD PLUMBING
class FuzzyOpenPlugin(GObject.Object, Gedit.WindowActivatable):
    __gname_type__ = "FuzzyOpenPluginWindowActivatable"
    window = GObject.property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        self.instance = FuzzyOpenPluginInstance(self)

    def do_deactivate(self):
        self.instance.deactivate()

    def do_update_state(self):
        pass

