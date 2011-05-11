from gi.repository import GObject, Gedit
import me_view

class MultiEditViewActivatable (GObject.Object, Gedit.ViewActivatable):
    __gtype_name__ = "MultiEditViewActivatable"

    view = GObject.property(type=Gedit.View)

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        self.view.set_data('me_instance', me_view.MultiEditViewInstance(self.view))
        self.view.get_data('me_instance').do_activate()

    def do_deactivate(self):
        self.view.get_data('me_instance').do_activate()
        self.view.set_data('me_instance', None)

    def do_update_state(self):
        pass

