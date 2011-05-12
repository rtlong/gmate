from gi.repository import Gedit, Gdk, Gtk
import me_keybinds
import re
import string

class MultiEditViewInstance:

    def __init__(self, view):
        self.keybinds = me_keybinds.MultiEditKeybinds()
        self.view = view
        self.document = view.get_buffer()
        # [insert, selection_bound]
        self.cursor_move_supported = [False, False]
        self.marks = []
        self.mark_total = 0
        # ([line_x, line_y], smart_navigation)
        self.vertical_mem = None
        # offset for vertical movement
        self.line_offset_mem = None
        self.change_supported = False
        self.mouse_event = {'current':False, 'followup':False}

    def do_activate(self):
        self.event_id = self.view.connect('event', self.doc_events)
        self.change_id = self.document.connect('changed', self.text_changed)
        self.mark_move_id = self.document.connect('mark-set', self.mark_moved)

    def do_deactivate(self):
        self.view.disconnect(self.event_id)
        self.document.disconnect(self.change_id)
        self.document.disconnect(self.mark_move_id)

    def do_update_state(self):
        pass

    # EVENTS #
    ##########
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

    def mark_moved(self, doc, doc_iter, mark):
        if mark.get_name() == 'insert':
            self.set_move_supported(0)
        elif mark.get_name() == 'selection_bound':
            self.set_move_supported(1)
        return False

    def text_changed(self, *arg):
        if self.change_supported:
            self.change_supported = False
        else:
            self.clear_marks()
        return False

    # HANDLERS #
    ############
    def keyboard_handler(self, event):
        ctrl_on, shift_on, alt_on, caps_on = self.get_modifiers(event.state)

        if caps_on and ctrl_on:
            if shift_on:
                event.keyval = Gdk.keyval_to_upper(event.keyval)
            else:
                event.keyval = Gdk.keyval_to_lower(event.keyval)
        safe_keys = (
            Gdk.KEY_Control_L,
            Gdk.KEY_Control_R,
            Gdk.KEY_Alt_L,
            Gdk.KEY_Alt_R,
            Gdk.KEY_Shift_L,
            Gdk.KEY_Shift_R,
        )

        if event.keyval in safe_keys:
            return False

        backup_vert_mem = self.vertical_mem
        backup_line_offset = self.line_offset_mem
        self.vertical_mem = None
        self.line_offset_mem = None

        if ctrl_on:
            # Add mark
            keyval, shift_required = self.keybinds.add_mark
            if event.keyval == keyval and (shift_required is None or shift_required == shift_on):
                self.add_remove_mark()
                return True

            for shortcut in self.keybinds.vertical_mark:
                keyval, shift_required = self.keybinds.vertical_mark[shortcut]
                if event.keyval == keyval and (shift_required is None or shift_required == shift_on) \
                    and (len(self.marks) != 0 or self.keybinds.columns_always_available):
                    # restore vertical positions
                    self.vertical_mem = backup_vert_mem
                    self.line_offset_mem = backup_line_offset
                    # add marks and move the cursor
                    down = shortcut[-2:] != 'up'
                    smart_nav = shortcut[:2] == 'sm'
                    self.vertical_cursor_nav(down, smart_nav)
                    return True

        # EDIT ACTIONS
        # MEREGHOST: Move to a new method/class?
        if len(self.marks) != 0:
            if not ctrl_on:
                if event.keyval == Gdk.KEY_ISO_Left_Tab and not alt_on:
                    self.multi_edit('left_tab')
                    return True
                if event.keyval == Gdk.KEY_Tab:
                    if self.view.get_insert_spaces_instead_of_tabs() and not alt_on:
                        self.multi_edit('space_tab')
                    else:
                        self.multi_edit('insert', '\t')
                    return True

            # Alt support drop.
            # MEREGHOST: Is this necessary?
            if alt_on:
                pass

            # shortcut suport
            # MEREGHOST: Move to new method
            if ctrl_on:
                keyval, shift_required = self.keybinds.temp_incr
                if event.keyval == keyval and (shift_required is None or shift_required == shift_on):
                        self.auto_incr_dialog()
                        return True
                if event.keyval == Gdk.KEY_v:
                    # TODO: Paste the clipboard contents
                    self.multi_edit('insert', None)

                if event.keyval in self.keybinds.auto_incr:
                    entry = self.keybinds.auto_incr[event.keyval]
                    if entry['shift_req'] is None or entry['shift_req'] == shift_on:
                        values = self.auto_increment(entry)
                        self.multi_edit('increment', values)
                        return True

                # Level marks
                keyval, shift_required = self.keybinds.level_marks
                if event.keyval == keyval and (shift_required is None or shift_required == shift_on):
                        self.multi_edit('level')
                        return True

                # Preserve marks
                if event.keyval in (Gdk.KEY_Up, Gdk.KEY_Down):
                    self.line_offset_mem = line_offset_mem_backup  # Recover line offset mem
                    down = event.keyval == Gdk.KEY_Down
                    self.vertical_cursor_nav(down, False, False)
                    return True

                if event.keyval in (Gdk.KEY_Left, Gdk.KEY_Right):
                    position = self.document.get_iter_at_mark(self.document.get_insert())
                    if event.keyval == Gdk.KEY_Left:
                        position.backward_cursor_position()
                    else:
                        position.forward_cursor_position()
                    self.cursor_move_supported = [True, True]
                    self.document.place_cursor(position)
                    return True

            # Regular key values
            if not ctrl_on:
                # Preserve identation (regular newlines handled below, as printable chars)
                if self.view.get_auto_indent() and event.keyval == Gdk.KEY_Return and \
                  not shift_on:
                    self.multi_edit('indent_nl')
                    return True

                if event.keyval == Gdk.KEY_BackSpace:
                    self.multi_edit('delete', -1)
                    return True

                if event.keyval == Gdk.KEY_Delete:
                    if not shift_on:  # to be consistent with gedit
                        self.multi_edit('delete', 1)
                        return True

                if event.keyval == Gdk.KEY_Escape:
                    # Prevent printing the unicode Escape char
                    return False

                # Printable chars
                if event.string != '':
                    self.multi_edit('insert', event.string)
                    return True
        return False

    def multi_edit(self, mode, value=None):
        """ Make mode dependant text modifications at all multi-edit marks.

        "value" is mode dependant.

        Modes:
            insert: normal text insertion
            delete: normal (backward or forward) text deletion
            increment: incrementing text insertion (numerical or alphabetical)
            tab: emulate gedit (indent)
            shift_tab: emulate gedit (preceding indentation deletion for lines)
        """
        self.document.begin_user_action()

        if mode == 'insert':
            # value = string
            for mark in self.marks:
                self.single_edit(mark, True, value)

        elif mode == 'delete':
            # value = length
            for mark in self.marks:
                self.single_edit(mark, False, value)

        elif mode == 'increment' and len(value) != 0:
            # value = list
            i = 0
            for mark in self.marks:
                self.single_edit(mark, True, value[i])
                i += 1
                if not i < len(value):
                    i = 0

        elif mode == 'space_tab':
            # value = not used
            tab_width = self.view.get_tab_width()
            for mark in self.marks:
                offset = self.get_physical_line_offset(mark)
                tab_string = ' ' * (tab_width - (offset % tab_width))
                self.single_edit(mark, True, tab_string)

        elif mode == 'left_tab':
            # value not used
            for mark in self.marks:
                pos = self.document.get_iter_at_mark(mark)
                pos.set_line_offset(0)
                i = 1
                while i < 4:
                    if pos.get_char() == ' ':
                        pass
                    elif pos.get_char() == '\t':
                        break
                    else:
                        i -= 1
                        break
                    pos.forward_char()
                    i += 1
                pos.set_line_offset(0)
                self.single_edit(pos, False, i, True)

        elif mode == 'indent_nl':
            # value not used
            for mark in self.marks:
                i = self.document.get_iter_at_mark(mark)
                offset = i.get_line_offset()
                i.set_line_offset(0)
                indent_str = '\n'
                while i.get_line_offset() < offset:
                    if i.get_char() in (' ', '\t'):
                        indent_str += i.get_char()
                    else:
                        break
                    i.forward_char()
                self.single_edit(mark, True, indent_str)

        elif mode == 'level':
            # value not used
            lines = {}
            max_offsets = {0:0}  # {column:max_offset}
            tabs = not self.view.get_insert_spaces_instead_of_tabs()
            tab_width = self.view.get_tab_width()

            # Sort marks into lines
            for mark in self.marks:
                line = self.document.get_iter_at_mark(mark).get_line()
                new_item = [mark, self.get_physical_line_offset(mark)]
                if line not in lines:
                    lines[line] = [new_item]
                else:
                    for i, item in enumerate(lines[line]):
                        if new_item[1] <= item[1]:
                            lines[line].insert(i, new_item)
                            break
                        elif i == len(lines[line]) - 1:
                            lines[line].append(new_item)
                            break
                    if len(lines[line]) > len(max_offsets):
                        # New column detected
                        max_offsets[len(max_offsets)] = 0

            # Get first column's max offset
            # Note: Succeeding columns' max offsets are detected during their
            # preceding column's process
            for line in lines:
                if lines[line][0][1] > max_offsets[0]:
                    max_offsets[0] = lines[line][0][1]

            # Process
            for column in max_offsets:
                next_column = column + 1

                # Tabs
                if tabs:
                    remainder = max_offsets[column] % tab_width
                    if remainder != 0:
                        max_offsets[column] += tab_width - remainder

                for line in lines:
                    if len(lines[line]) - 1 < column:
                        continue
                    dif = max_offsets[column] - lines[line][column][1]
                    if dif > 0:
                        if tabs:
                            insert = '\t' * (dif / tab_width)
                            if dif % tab_width != 0:
                                insert += '\t'
                        else:
                            insert = ' ' * dif
                        self.single_edit(lines[line][column][0], True, insert)
                        # Update succeeding offets in same line
                        for i in range(len(lines[line]) - next_column):
                            lines[line][next_column + i][1] += dif
                    # Update the succeeding max offset
                    if len(lines[line]) > next_column and \
                      lines[line][next_column][1] > max_offsets[next_column]:
                        max_offsets[next_column] = lines[line][next_column][1]

        self.document.end_user_action()

    def single_edit(self, start, insert, value,  start_is_iter=False):
        """ Insert or delete text at the given position.

        Important: Multi-edit text modifications must never occur anywhere but here.
                   And only "_multi_edit" may call this function.

        Arguments:
            start: A mark or iter (depending on "start_is_iter")
            insert: True for insert, False for delete
            value: String for insert, length for delete (+: forward deletion, -: backward deletion)
        """
        self.change_supported = True
        if not start_is_iter:
            start = self.document.get_iter_at_mark(start)
        if insert:
            self.document.insert_interactive(start, str(value), -1, True)
        else:
            end = start.copy()
            if value > 0:
                end.forward_cursor_positions(value)
            else:
                start.forward_cursor_positions(value)
            self.document.delete_interactive(start, end, True)
            self.cleanup_marks()

    def cleanup_marks(self):
        """ Remove any duplicate marks caused by text deletion. """
        offsets = []
        for mark in self.marks[:]:
            offset = self.document.get_iter_at_mark(mark).get_offset()
            if offset in offsets:
                self.document.delete_mark(mark)
                self.marks.remove(mark)
            else:
                offsets.append(offset)

    def auto_incr_dialog(self):
        pass

    def auto_increment(self, entry):
        """ Parse an auto-incr command and return the list of values. """

        # Number
        if entry['type'] == 'num' and len(entry['args']) == 2:
            i = float(entry['args'][0])
            result = []
            for mark in self.marks:
                str_i = str(i)
                if str_i[-2:] == '.0':
                    str_i = str_i[:-2]
                result.append(str_i)
                i += float(entry['args'][1])
            return result

        # Alphabet
        elif entry['type'] == 'abc' and len(entry['args']) == 1:
            start = entry['args'][0]
            if start not in ('a', 'A', 'z', 'Z'):
                return ()
            if start.islower():
                letters = list(string.ascii_lowercase)
            else:
                letters = list(string.ascii_uppercase)
            if start.lower() == 'z':
                letters.reverse()
            return letters

        # Custom list
        elif entry['type'] == 'list':
            return entry['args']

        # Invalid type
        return ()

    def mouse_handler(self, event, action):
        ctrl_on, shift_on, alt_on, caps_on = self.get_modifiers(event.state)
        # Clear line/offset memory
        self.line_offset_mem = None
        self.vertical_mem = None

        # Requirements
        if (action == 'press' and not ctrl_on) or alt_on or event.button.button not in (1, 3):
            return False

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
                smart_nav = event.button.button == 3
                for i in range(abs(dif)):
                    self.vertical_cursor_nav(down, smart_nav)
                self.mouse_event = {'current':True, 'followup':False}
                return True
            # Single mark placement
            elif event.button.button == 1:
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

    # MARK METHODS #
    ################
    def clear_marks(self):
        for mark in self.marks:
            # Convenient way of redrawing just that mark's area
            mark.set_visible(False)
            self.document.delete_mark(mark)
        self.marks = []
        self.mark_total = 0

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

    # POSITIONING #
    ###############
    def vertical_cursor_nav(self, down, smart_nav=False, edit_marks=True):
        """
        Emulate normal vertical cursor movement.

        Smart Nav: Navigates lines based on words instead of chars,
        but also sticks to end-of-lines when met.
        """
        # iterator position at the caret
        position = self.document.get_iter_at_mark(self.document.get_insert())

        # Vertical marks memory (vertical)
        if edit_marks and (self.vertical_mem is None or self.vertical_mem[1] != smart_nav):
            self.vertical_mem = (position.get_line(), smart_nav)

        # Initial mark edit
        if edit_marks:
            if (down and self.vertical_mem[0] > position.get_line()) or \
            (not down and self.vertical_mem[0] < position.get_line()):
            # removing the marks
                self.add_remove_mark()
            else:
            #adding a mark
                self.add_remove_mark(True)

        if self.line_offset_mem is None or smart_nav != self.line_offset_mem["smart_nav"]:
            if not smart_nav:
                self.line_offset_mem = { 'smart_nav': False,
                    'data': self.get_physical_line_offset(self.document.get_insert()) }
            else:
                # Save values
                self.line_offset_mem = {
                    "smart_nav": True,
                    "data": self.data_for_vertical_nav(position) }

        # Line change
        if down:
            position.forward_line()
        else:
            position.backward_line()

        # Handle positioning for the new line
        if smart_nav:
            data = self.line_offset_mem["data"]
            if not position.ends_line():
                if data["end_of_line"]:
                    position.forward_to_line_end()
                else:
                    # Word offset
                    for i in range(data["word_offset"]):
                        # Forward till end of word
                        while position.get_char() not in separators and not position.ends_line():
                            position.forward_char()
                        # Stop at the word end if end_gravity and the last word offset
                        if data["end_gravity"] and i == data["word_offset"] - 1:
                            break
                        # Forward till next word
                        while position.get_char() in separators and not position.ends_line():
                            position.forward_char()
                    # Char offset
                    for i in range(data["char_offset"]):
                        # Stop if EOL or end of seperators if mid_seperators
                        if position.ends_line() or (data["mid_separators"] and \
                          position.get_char() not in separators):
                            break
                        position.forward_char()
        else:
            logical_offset = self.get_logical_line_offset(position, self.line_offset_mem["data"])
            if position.get_chars_in_line() <= logical_offset:
                if not position.ends_line():
                    position.forward_to_line_end()
            else:
                position.set_visible_line_offset(logical_offset)

        # Place the cursor/mark
        self.cursor_move_supported = [True, True]
        self.document.place_cursor(position)
        if edit_marks:
            self.add_remove_mark(True)
        else:
            # Reset the vertical_mem since it will now be invalid
            self.vertical_mem = None

    def get_logical_line_offset(self, position, offset):
        position = position.copy()
        position.set_line_offset(0)
        phy_inc = 0
        tab_width = self.view.get_tab_width()
        phy_amount = 0
        while phy_inc < offset and not position.ends_line():
            if position.get_char() == '\t':
                phy_amount = tab_width - (phy_inc % tab_width)
            else:
                phy_amount = 1
            phy_inc += phy_amount
            position.forward_char()
        # Round mid-tab offset
        if phy_inc != offset and phy_inc - offset > phy_amount / 2:
            position.backward_char()
        return position.get_line_offset()

    def get_physical_line_offset(self, cursor):
        position = self.document.get_iter_at_mark(cursor)
        iterator = position.copy()
        iterator.set_line_offset(0)
        offset = 0
        tab_width = self.view.get_tab_width()
        while not iterator.equal(position):
            if iterator.get_char() == '\t':
                offset += tab_width - (offset % tab_width)
            else:
                offset += 1
            iterator.forward_char()
        return offset

    # SUPPORT #
    ###########
    def set_move_supported(self, index):
        if self.cursor_move_supported[index]:
            self.cursor_move_supported[index] = False
        else:
            self.clear_marks()

    def data_for_vertical_navigation(self, position):
        # string separators for bounds
        separators = string.whitespace + string.punctuation.replace('_', '')

        if position.starts_line() or position.ends_line():
            word_offset, char_offset = 0, 0
            end_gravity, mid_separators = None, None
        else:
            start_iter = position.copy()
            start_iter.set_line_offset(0)
            text = start_iter.get_text(position)

            end_gravity = text[-1:] not in separators and position.get_char() in separators
            mid_separators = text[-1:] in separators and position.get_char() in separators
            end_gravity = mid_separators or end_gravity
            mid_word = text[-1:] not in separators and position.get_char() not in separators

            # Convert seperators to spaces (to use split())
            # MEREGHOST: Shouldn't I just use a regex?
            words_re = re.sub('\s', ' ', text)
            words_re = re.sub('['+ string.punctuation.replace('_','') +']', ' ', words_re)
            words = ''
            for i, char in enumerate(text):
                if char in seperators:
                    words += ' '
                else:
                    words += char
            words = words.split()
            word_offset = len(words)

            print "DEBUG[words]: %s" % words
            print "DEBUG[words_re]: %s" % words_re.split()
            print "DEBUG[len(words)]: %s" % len(words)
            print "DEBUG[len(words_re)]: %s" % len(words_re.split())

            if text[0] in separators and not (mid_separators and word_offset == 0):
                word_offset += 1
            if mid_word:
                word_offset -= 1

            char_offset = 0
            if mid_word:
                char_offset = len(words[-1])
            elif mid_seperators:
                text_iterator = position.copy()
                text_iterator.backward_char()
                while text_iterator.get_char() in separators:
                    char_offset += 1
                    if text_iterator.starts_line():
                        break
                    text_iterator.backward_char()

        return {"word_offset": word_offset, "char_offset": char_offset,
                    "end_gravity": end_gravity, "mid_separators": mid_separators,
                    "end_of_line": end_of_line }

    def get_modifiers(self, state):
        modifiers = Gtk.accelerator_get_default_mod_mask()
        ctrl_on = (state & modifiers) == Gdk.ModifierType.CONTROL_MASK
        shift_on = (state & modifiers) == Gdk.ModifierType.SHIFT_MASK
        alt_on = (state & modifiers) == Gdk.ModifierType.MOD1_MASK
        caps_on = (state & modifiers) == Gdk.ModifierType.LOCK_MASK
        return (ctrl_on, shift_on, alt_on, caps_on)

