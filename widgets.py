# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gtk
from gettext import gettext as _

import logging
logger = logging.getLogger('write-activity')

from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.combobox import ComboBox
from sugar.graphics.palette import Palette
from sugar.graphics.radiopalette import RadioPalette

class FontCombo(ComboBox):
    def __init__(self, abi):
        ComboBox.__init__(self)

        self._has_custom_fonts = False
        self._fonts = sorted(abi.get_font_names())
        self._fonts_changed_id = self.connect('changed', self._font_changed_cb,
                abi)

        for i, f in enumerate(self._fonts):
            self.append_item(i, f, None)
            if f == 'Times New Roman':
                self.set_active(i)

        self._abi_handler = abi.connect('font-family', self._font_family_cb)

    def _font_changed_cb(self, combobox, abi):
        if self.get_active() != -1:
            logger.debug('Setting font: %s', self._fonts[self.get_active()])
            try:
                abi.handler_block(self._abi_handler)
                abi.set_font_name(self._fonts[self.get_active()])
            finally:
                abi.handler_unblock(self._abi_handler)

    def _font_family_cb(self, abi, font_family):
        font_index = -1

        # search for the font name in our font list
        for i, f in enumerate(self._fonts):
            if f == font_family:
                font_index = i
                break;

        # if we don't know this font yet, then add it (temporary) to the list
        if font_index == -1:
            logger.debug('Font not found in font list: %s', font_family)
            if not self._has_custom_fonts:
                # add a separator to seperate the non-available fonts from
                # the available ones
                self._fonts.append('') # ugly
                self.append_separator()
                self._has_custom_fonts = True
            # add the new font
            self._fonts.append(font_family)
            self.append_item(0, font_family, None)
            # see how many fonts we have now, so we can select the last one
            model = self.get_model()
            num_children = model.iter_n_children(None)
            logger.debug('Number of fonts in the list: %d', num_children)
            font_index = num_children-1

        # activate the found font
        if (font_index > -1):
            self.handler_block(self._fonts_changed_id)
            self.set_active(font_index)
            self.handler_unblock(self._fonts_changed_id)

class FontSizeCombo(ComboBox):
    def __init__(self, abi):
        ComboBox.__init__(self)

        self._abi_handler = abi.connect('font-size', self._font_size_cb)

        self._font_sizes = ['8', '9', '10', '11', '12', '14', '16', '20', \
                            '22', '24', '26', '28', '36', '48', '72']
        self._changed_id = self.connect('changed', self._font_size_changed_cb,
                abi)

        for i, s in enumerate(self._font_sizes):
            self.append_item(i, s, None)
            if s == '12':
                self.set_active(i)

    def _font_size_changed_cb(self, combobox, abi):
        if self.get_active() != -1:
            logger.debug('Setting font size: %d',
                    int(self._font_sizes[self.get_active()]))

            abi.handler_block(self._abi_handler)
            try:
                abi.set_font_size(self._font_sizes[self.get_active()])
            finally:
                abi.handler_unblock(self._abi_handler)

    def _font_size_cb(self, abi, size):
        for i, s in enumerate(self._font_sizes):
            if int(s) == int(size):
                self.handler_block(self._changed_id)
                self.set_active(i)
                self.handler_unblock(self._changed_id)
                break;

class StyleCombo(ComboBox):
    def __init__(self, abi):
        ComboBox.__init__(self)

        self._abi_handler = abi.connect('style-name', self._style_cb)

        self._styles = [ ['Heading 1', _('Heading 1')],
                         ['Heading 2', _('Heading 2')],
                         ['Heading 3', _('Heading 3')],
                         ['Heading 4', _('Heading 4')],
                         ['Bullet List', _('Bullet List')],
                         ['Dashed List', _('Dashed List')],
                         ['Numbered List', _('Numbered List')],
                         ['Lower Case List', _('Lower Case List')],
                         ['Upper Case List', _('Upper Case List')],
                         ['Block Text', _('Block Text')],
                         ['Normal', _('Normal')],
                         ['Plain Text', _('Plain Text')] ]

        self._has_custom_styles = False
        self._style_changed_id = self.connect('changed', self._style_changed_cb,
                abi)

        for i, s in enumerate(self._styles):
            self.append_item(i, s[1], None)
            if s[0] == 'Normal':
                self.set_active(i)

    def _style_changed_cb(self, combobox, abi):
        if self.get_active() != -1:
            logger.debug('Set style: %s', self._styles[self.get_active()][0])
            try:
                abi.handler_block(self._abi_handler)
                abi.set_style(self._styles[self.get_active()][0])
            finally:
                abi.handler_unblock(self._abi_handler)

    def _style_cb(self, abi, style_name):
        if style_name is None or style_name == 'None':
            style_name = 'Normal'

        style_index = -1
        for i, s in enumerate(self._styles):
            if s[0] == style_name:
                style_index = i
                break;

        # if we don't know this style yet, then add it (temporary) to the list
        if style_index == -1:
            logger.debug('Style not found in style list: %s', style_name)

            if not self._has_custom_styles:
                # add a separator to seperate the non-available styles from
                # the available ones
                self._styles.append(['','']) # ugly
                self.append_separator()
                self._has_custom_styles = True

            # add the new style
            self._styles.append([style_name, style_name])
            self.append_item(0, style_name, None)

            # see how many styles we have now, so we can select the last one
            model = self.get_model()
            num_children = model.iter_n_children(None)
            logger.debug('Number of styles in the list: %d', num_children)
            style_index = num_children-1

        if style_index > -1:
            self.handler_block(self._style_changed_id)
            self.set_active(style_index)
            self.handler_unblock(self._style_changed_id)

class AbiButton(RadioToolButton):
    def __init__(self, abi, abi_signal, do_abi_cb, on_abi_cb=None, **kwargs):
        RadioToolButton.__init__(self, **kwargs)

        self._abi_handler = abi.connect(abi_signal, self.__abi_cb,
                abi_signal, on_abi_cb)
        self._toggled_handler = self.connect('toggled', self.__toggled_cb,
                abi, do_abi_cb)

    def __toggled_cb(self, button, abi, do_abi_cb):
        if not button.props.active:
            return

        abi.handler_block(self._abi_handler)
        try:
            logging.debug('Do abi %s' % do_abi_cb)
            do_abi_cb()
        finally:
            abi.handler_unblock(self._abi_handler)

    def __abi_cb(self, abi, prop, abi_signal, on_abi_cb):
        if (on_abi_cb is None and not prop) or \
                (on_abi_cb is not None and not on_abi_cb(abi, prop)):
            return

        self.handler_block(self._toggled_handler)
        try:
            logging.debug('On abi %s prop=%r' % (abi_signal, prop))
            self.set_active(True)
        finally:
            self.handler_unblock(self._toggled_handler)

class ListsPalette(RadioPalette):
    def __init__(self, abi):
        RadioPalette.__init__(self)

        def append(icon_name, tooltip, do_abi_cb, on_abi_cb):
            button = AbiButton(abi, 'style-name', do_abi_cb, on_abi_cb)
            button.show()
            button.props.icon_name = icon_name
            button.props.group = group
            RadioPalette.append(self, button, tooltip)
            return button

        group = None

        group = append('list-none', _('Normal'),
                lambda:
                    abi.set_style('Normal'),
                lambda abi, style:
                    style not in ['Bullet List',
                                  'Dashed List',
                                  'Numbered List',
                                  'Lower Case List',
                                  'Upper Case List'])

        append('list-bullet', _('Bullet List'),
                lambda: abi.set_style('Bullet List'),
                lambda abi, style: style == 'Bullet List')

        append('list-dashed', _('Dashed List'),
                lambda: abi.set_style('Dashed List'),
                lambda abi, style: style == 'Dashed List')

        append('list-numbered', _('Numbered List'),
                lambda: abi.set_style('Numbered List'),
                lambda abi, style: style == 'Numbered List')

        append('list-lower-case', _('Lower Case List'),
                lambda: abi.set_style('Lower Case List'),
                lambda abi, style: style == 'Lower Case List')

        append('list-upper-case', _('Upper Case List'),
                lambda: abi.set_style('Upper Case List'),
                lambda abi, style: style == 'Upper Case List')

        self.show_all()
