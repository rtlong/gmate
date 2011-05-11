from gi.repository import Gedit, Gdk, Gtk

class MultiEditViewInstance:

    def __init__(self, view):
        self.view = view
        self.document = view.get_buffer()
        # [insert, selection_bound]
        self.cursor_move_supported = [False, False]
        self.marks = []
        self.mark_total = 0

    def do_activate(self):
        self.event_id = self.view.connect('event', self.doc_events)
        self.change_id = self.document.connect('changed', self.text_changed)
        self.mark_move_id = self.document.connect('mark-set', self.mark_moved)

    def do_deactivate(self):
        self.view.disconnect(self.event_id)
        self.buffer.disconnect(self.change_id)
        self.buffer.disconnect(self.mark_move_id)

    def do_update_state(self):
        pass

    def text_changed(self, arg1):
        pass

    """
    Wrapper for all TextView events.
    Used instead of more specific signals, to gain priority over other plugins.
    Appropriate given that Multi-edit will still pass on events if in single-edit mode.
    """
    def doc_events(self, doc, event):
        if event.type == Gdk.EventType.KEY_PRESS:
            result = self.keyboard_handler(event)
            # Ensure cursor remains visible during text modifications
            # Only scroll if multi-edit is managing the event
            if result:
                self.view.scroll_mark_onscreen(self.document.get_insert())
            return result
        if event.type == Gdk.EventType.BUTTON_PRESS:
            return self.mouse_handler(event, 'press')
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            return self.mouse_handler(event, 'release')
        # Let the event bubble if none of conditions applied
        return False

    def keyboard_handler(self, event):
        pass

    def mouse_handler(self, event, action):
        # Modifier checks
        modifiers = Gtk.accelerator_get_default_mod_mask()
        ctrl_on = (event.state & modifiers) == Gdk.ModifierType.CONTROL_MASK
        shift_on = (event.state & modifiers) == Gdk.ModifierType.SHIFT_MASK
        alt_on = (event.state & modifiers) == Gdk.ModifierType.MOD1_MASK

        # Clear line/offset memory
        self.line_offset_mem = None
        self.vert_mark_mem = None

        # Requirements
        if (action == 'press' and not ctrl_on) or alt_on or event.button not in (1, 3):
            return False

        # Mark actions #
        ################
        # Add marks [cursor movement]
        if action == 'press':
            self.mouse_event = {'current':False}  # to be safe
            # Get pos
            win_type = self.view.get_window_type(event.window)
            pos = self.view.window_to_buffer_coords(win_type, int(event.x), int(event.y))
            pos = self.view.get_iter_at_location(pos[0], pos[1])

            # Multiple mark placement
            if shift_on:
                old_pos = self.document.get_iter_at_mark(self.document.get_insert())
                dif = pos.get_line() - old_pos.get_line()
                down = abs(dif) == dif
                smart_nav = event.button == 3
                for i in range(abs(dif)):
                    self.vertical_cursor_nav(down, smart_nav)
                self.mouse_event = {'current':True, 'followup':False}
                return True
            # Single mark placement
            elif event.button == 1:
                self.cursor_move_supported = [True, True]
                self.document.place_cursor(pos)
                self.add_remove_mark()
                self.mouse_event = {'current':True, 'followup':True}
                return True

        # Finish multi-edit events
        elif self.mouse_event['current']:
            if action == 'release':
                self.mouse_event = {'current':False}
            return True
        return False

    def add_remove_mark(self, dont_remove=False):
        """ Add or remove a mark at the cursors position. """
        position = self.document.get_iter_at_mark(self.document.get_insert())
        position_marks = position.get_marks()
        deleted = 0

        # Deselect the current selection (if there is one)
        self.cursor_move_supported = [False, True]
        self.document.move_mark_by_name('selection_bound', position)

        for mark in position_marks:
            # Note: Marks may be present that are not associated with multi-edit
            if mark in self.marks:
                mark.set_visible(False)
                self.document.delete_mark_by_name(mark.get_name())
                self.marks.remove(mark)
                deleted += 1

        # Check included to watch for "mark leaking"
        if deleted > 1:
            print 'Multi-edit plugin: Mark leak detected'

        if deleted != 0 and not dont_remove:
            return

        # Add the mark
        self.marks.append(self.document.create_mark('multi-edit' + str(self.mark_total), position, False))
        self.marks[len(self.marks) - 1].set_visible(True)
        self.mark_total += 1


    def vertical_cursor_nav(down, smart):
        print "Vertical Cursor!"

    def mark_moved(self, doc, doc_iter, mark):
        if mark.get_name() == 'insert':
            self.set_move_supported(0)
        elif mark.get_name() == 'selection_bound':
            self.set_move_supported(1)
        return False

    def set_move_supported(self, index):
        if self.cursor_move_supported[index]:
            self.cursor_move_supported[index] = False
        else:
            self.clear_marks()

    def clear_marks(self):
        for mark in self.marks:
            # Convenient way of redrawing just that mark's area
            mark.set_visible(False)
            self.document.delete_mark(mark)
        self.marks = []
        self.mark_total = 0

