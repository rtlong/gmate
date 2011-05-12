from gi.repository import Gdk

class MultiEditKeybinds:


    columns_always_avail = True
    sc_auto_increment_str = '\n'.join(('- abc:a', '_ abc:A','= abc:z','+ abc:Z',
                            '0 num:0,1',') num:1,1',
                            'x list:"This","is","an","example",";)",""',))
    sc_add_mark_str = 'r'
    sc_level_marks_str = 'l'
    sc_temp_increment_marks = 'i'
    sc_vertical_mark_str = {
            'up': 'Page_Up',
            'down': 'Page_Down',
            'smart_up': 's+Page_Up',
            'smart_down': 's+Page_Down',
        }
    def __init__(self):
        self._set_shortcut_keyvals()

    def _get_keyval(string):
        if len(string) == 1:
            return (Gdk.unicode_to_keyval(ord(unicode(string))), None)
        if len(string) > 1:
            shift_req = string[:2] == 's+'
            if shift_req:
                string = string[2:]
            keyval = Gdk.keyval_from_name(string)
            if Gdk.keyval_to_unicode(keyval) != 0:
                shift_req = None
            return (keyval, shift_req)
        else:
            return (0, None)

    def _set_shortcut_keyvals(self):
        self.add_mark = self._get_keyval(self.add_mark_str)
        self.level_marks = self._get_keyval(self.sc_level_marks_str))
        self.temp_incr = self._get_keyval(self.sc_temp_increment_mark_str)
        self.auto_incr = self._parse_sc_auto_incr(self.sc_auto_increment_str)
        self.mark_vert = {
            'up': self._get_keyval(self._sc_mark_vert_str['up']),
            'down': self._get_keyval(self._sc_mark_vert_str['down']),
            'smart_up': self._get_keyval(self._sc_mark_vert_str['smart_up']),
            'smart_down': self._get_keyval(self._sc_mark_vert_str['smart_down']),
        }

    def _parse_sc_auto_incr(self, string):
        lines = string.splitlines()
        result = {}
        for line in lines:
            (line, sep, args) = line.partition(':')
            if sep != ':': continue
            (key, sep, incr_type) = line.partition(' ')
            if sep != ' ': continue
            keyval, shift_req = self._get_keyval(key)
            if keyval == 0: continue
            args = csv.reader([args]).next()
            if len(args) == 0: continue
            result[keyval] = {
                'shift_req': shift_req,
                'type': incr_type,
                'args': args,
            }
        return result

