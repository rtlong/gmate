from gi.repository import GObject, Gedit

class GeminiViewActivatable (GObject.Object, Gedit.ViewActivatable):
    __gtype_name__ = "GeminiPluginViewActivatable"
    view = GObject.property(type=Gedit.View)
    handler_id = 0

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        self.setup_gemini()

    def do_deactivate(self):
        self.view.disconnect(self.view.get_data('GeminiHandlers'))
        self.view.set_data('gemini_instance', None)

    def do_update_state(self):
        self.setup_gemini()

    def setup_gemini(self):
        if self.view.get_data('gemini_instance') is None:
            self.view.set_data('gemini_instance', Gemini())
            handler_id = self.view.connect('key-press-event', self.view.get_data('gemini_instance').key_press_handler)
            self.view.set_data('GeminiHandlers', handler_id)


class Gemini:
    start_keyvals = [34, 39, 96, 40, 91, 123]
    end_keyvals   = [34, 39, 96, 41, 93, 125]
    twin_start    = ['"',"'",'`','(','[','{']
    twin_end      = ['"',"'",'`',')',']','}']
    # 65288 => Backspace 65535 => Del
    special_keyvals = [65288, 65535]
    toggle        = False

    def __init__(self):
        return

    def key_press_handler(self, view, event):
        self.toggle = True
        # Get the document from the view
        document = view.get_buffer()
        # Get the current cursor position and preserves
        cursor_mark = document.get_insert()
        # Get the iterator at the mark
        cursor_iter = document.get_iter_at_mark(cursor_mark)

        if event.keyval in self.start_keyvals or event.keyval in self.end_keyvals or event.keyval in self.special_keyvals:
            back_iter = cursor_iter.copy()
            back_iter.backward_char()
            forward_iter = cursor_iter.copy()
            forward_iter.forward_char()
            back_char = document.get_text(back_iter, cursor_iter, 1)
            forward_char = document.get_text(cursor_iter, forward_iter, 1)

            # get the pair for insertion
            index, start_str, end_str = self.get_pairs(event.keyval)

            # Here is the meat of the logic
            if document.get_has_selection() and event.keyval not in self.special_keyvals:
                # pad the selected text with twins
                start_iter, end_iter = document.get_selection_bounds()
                selected_text = start_iter.get_text(end_iter)
                document.delete(start_iter, end_iter)
                document.insert_at_cursor(start_str + selected_text + end_str)
                return True
            elif index >= 0 and start_str == self.twin_start[index]:
                # insert the twin that matches your typed twin
                document.insert(cursor_iter, end_str)
                if cursor_iter.backward_char():
                    document.place_cursor(cursor_iter)
            elif event.keyval == 65288 and back_char in self.twin_start and forward_char in self.twin_end:
                # delete twins when backspacing starting char next to ending char
                if self.twin_start.index(back_char) == self.twin_end.index(forward_char):
                    document.delete(cursor_iter, forward_iter)
            elif event.keyval in self.end_keyvals:
                # stop people from closing an already closed pair
                index = self.end_keyvals.index(event.keyval)
                if self.twin_end[index] == forward_char:
                    document.delete(cursor_iter, forward_iter)
            elif event.keyval == 65293 and forward_char == '}':
                # add proper indentation when hitting before a closing bracket
                # MEREGHOST: Does this work at all?
                cursor_iter = document.get_iter_at_mark(document.get_insert ())
                line_start_iter = cursor_iter.copy()
                view.backward_display_line_start(line_start_iter)

                line = document.get_text(line_start_iter, cursor_iter)
                preceding_white_space_pattern = re.compile(r'^(\s*)')
                groups = preceding_white_space_pattern.search(line).groups()
                preceding_white_space = groups[0]
                plen = len(preceding_white_space)

                document.insert_at_cursor('\n')
                document.insert_at_cursor(preceding_white_space)
                document.insert_at_cursor('\n')

                cursor_mark = document.get_insert()
                cursor_iter = document.get_iter_at_mark(cursor_mark)

                document.insert_at_cursor(preceding_white_space)
                cursor_mark = document.get_insert()
                cursor_iter = document.get_iter_at_mark(cursor_mark)

                for i in range(plen + 1):
                    if cursor_iter.backward_char():
                        document.place_cursor(cursor_iter)
                if view.get_insert_spaces_instead_of_tabs():
                    document.insert_at_cursor(' ' * view.get_tab_width())
                else:
                    document.insert_at_cursor('\t')
                return True

    def get_pairs(self, keyval):
        if keyval in self.start_keyvals:
            index = self.start_keyvals.index(keyval)
            start_str = self.twin_start[index]
            end_str = self.twin_end[index]
        else:
            index = -1
            start_str, end_str = None, None
        return [index, start_str, end_str]

