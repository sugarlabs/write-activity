# Copyright (C) 2006, Martin Sevior
# Copyright (C) 2006-2007, Marc Maurer <uwog@uwog.net>
# Copyright (C) 2007, One Laptop Per Child
#
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
from gettext import gettext as _
import logging

import abiword
import gtk

from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.toggletoolbutton import ToggleToolButton
from sugar.graphics.combobox import ComboBox

class TextToolbar(gtk.Toolbar):
    _ACTION_ALIGNMENT_LEFT = 0
    _ACTION_ALIGNMENT_CENTER = 1
    _ACTION_ALIGNMENT_RIGHT = 2

    def __init__(self, abiword_canvas):
        gtk.Toolbar.__init__(self)

        self._abiword_canvas = abiword_canvas

        self._bold = ToggleToolButton('format-text-bold')
        self._bold_id = self._bold.connect('clicked', self._bold_cb)
        self._abiword_canvas.connect('bold', self._isBold_cb)
        self.insert(self._bold, -1)
        self._bold.show()

        self._italic = ToggleToolButton('format-text-italic')
        self._italic_id = self._italic.connect('clicked', self._italic_cb)
        self._abiword_canvas.connect('italic', self._isItalic_cb)
        self.insert(self._italic, -1)
        self._italic.show()

        self._underline = ToggleToolButton('format-text-underline')
        self._underline_id = self._underline.connect('clicked', self._underline_cb)
        self._abiword_canvas.connect('underline', self._isUnderline_cb)
        self.insert(self._underline, -1)
        self._underline.show()

        separator = gtk.SeparatorToolItem()
        separator.set_draw(True)
        self.insert(separator, -1)

        self._font_size_combo = ComboBox()
        self._font_sizes = ['8', '9', '10', '11', '12', '14', '16', '20', '22', '24', '26', '28', '36', '48', '72'];
        for i, s in enumerate(self._font_sizes):
            self._font_size_combo.append_item(i, s, None)
        self._font_size_changed_id = self._font_size_combo.connect('changed',
            self._font_size_changed_cb)
        self._add_widget(self._font_size_combo)

        self._font_combo = ComboBox()
        self._fonts = sorted(self._abiword_canvas.get_font_names())
        for i, f in enumerate(self._fonts):
            self._font_combo.append_item(i, f, None)
        self._fonts_changed_id = self._font_combo.connect('changed',
            self._font_changed_cb)
        self._add_widget(self._font_combo)

        separator = gtk.SeparatorToolItem()
        separator.set_draw(True)
        self.insert(separator, -1)
        separator.show()

        self._alignment = ComboBox()
        self._alignment.append_item(self._ACTION_ALIGNMENT_LEFT, None,
                                    'format-justify-left')
        self._alignment.append_item(self._ACTION_ALIGNMENT_CENTER, None,
                                    'format-justify-center')
        self._alignment.append_item(self._ACTION_ALIGNMENT_RIGHT, None,
                                    'format-justify-right')
        self._alignment_changed_id = self._alignment.connect('changed',
            self._alignment_changed_cb)
        self._add_widget(self._alignment)

        self._abiword_canvas.connect('left-align', self._isLeftAlign_cb)
        self._abiword_canvas.connect('center-align', self._isCenterAlign_cb)
        self._abiword_canvas.connect('right-align', self._isRightAlign_cb)

    def _add_widget(self, widget, expand=False):
        tool_item = gtk.ToolItem()
        tool_item.set_expand(expand)

        tool_item.add(widget)
        widget.show()

        self.insert(tool_item, -1)
        tool_item.show()

    def setToggleButtonState(self,button,b,id):
        button.handler_block(id)
        button.set_active(b)
        button.handler_unblock(id)

    def _italic_cb(self, button):
        self._abiword_canvas.toggle_italic()

    def _isItalic_cb(self, abi, b):
        print 'isItalic',b
        self.setToggleButtonState(self._italic, b, self._italic_id)

    def _underline_cb(self, button):
        self._abiword_canvas.toggle_underline()

    def _isUnderline_cb(self, abi, b):
        print 'isUnderline',b
        self.setToggleButtonState(self._underline, b, self._underline_id)

    def _bold_cb(self, button):
        self._abiword_canvas.toggle_bold()

    def _isBold_cb(self, abi, b):
        print 'isBold',b
        self.setToggleButtonState(self._bold,b,self._bold_id)

    def _font_changed_cb(self, combobox):
        if self._font_combo.get_active() != -1:
            print 'Setting font name:',self._fonts[self._font_combo.get_active()]
            self._abiword_canvas.set_font_name(self._fonts[self._font_combo.get_active()])

    def _font_size_changed_cb(self, combobox):
        if self._font_size_combo.get_active() != -1:
            print 'Setting font size:',self._font_sizes[self._font_size_combo.get_active()]
            self._abiword_canvas.set_font_size(self._font_sizes[self._font_size_combo.get_active()])

    def _alignment_changed_cb(self, combobox):
        if self._alignment.get_active() == self._ACTION_ALIGNMENT_LEFT:
            self._abiword_canvas.align_left()
        elif self._alignment.get_active() == self._ACTION_ALIGNMENT_CENTER:
            self._abiword_canvas.align_center()
        elif self._alignment.get_active() == self._ACTION_ALIGNMENT_RIGHT:
            self._abiword_canvas.align_right()
        else:
            raise ValueError, 'Unknown option in alignment combobox.'

    def _update_alignment_icon(self, index):
        self._alignment.handler_block(self._alignment_changed_id)
        try:
            self._alignment.set_active(index)
        finally:
            self._alignment.handler_unblock(self._alignment_changed_id)

    def _isLeftAlign_cb(self, abi, b):
        print 'isLeftAlign',b
        if b:
            self._update_alignment_icon(self._ACTION_ALIGNMENT_LEFT)

    def _isCenterAlign_cb(self, abi, b):
        print 'isCenterAlign',b
        if b:
            self._update_alignment_icon(self._ACTION_ALIGNMENT_CENTER)

    def _isRightAlign_cb(self, abi, b):
        print 'isRightAlign',b
        if b:
            self._update_alignment_icon(self._ACTION_ALIGNMENT_RIGHT)

class ImageToolbar(gtk.Toolbar):
    def __init__(self, abiword_canvas):
        gtk.Toolbar.__init__(self)

        self._abiword_canvas = abiword_canvas

        # insert-image does not exist yet; someone kick Eben please :)
        self._image = ToolButton('insert-image')
        self._image_id = self._image.connect('clicked', self._image_cb)
        self.insert(self._image, -1)
        self._image.show()

    def _image_cb(self, button):
        print 'fileInsertGraphic'
        self._abiword_canvas.invoke_cmd('fileInsertGraphic', '', 0, 0)

class TableToolbar(gtk.Toolbar):
    def __init__(self, abiword_canvas):
        gtk.Toolbar.__init__(self)

        self._abiword_canvas = abiword_canvas

        self._table = abiword.TableCreator()
        self._table.set_labels(_('Table'), _('Cancel'))
        self._table_id = self._table.connect('selected', self._table_cb)
        #self._table_id = self._abiword_canvas.connect('table-state', self._tableState)

        tool_item = gtk.ToolItem()
        tool_item.add(self._table)
        self._table.show()

        self.insert(tool_item, -1)
        tool_item.show()

    def _table_cb(self, abi, rows, cols):
        self._abiword_canvas.insert_table(rows,cols)
