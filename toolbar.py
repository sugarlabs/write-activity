# Copyright (C) 2006 by Martin Sevior
# Copyright (C) 2006-2007 Marc Maurer <uwog@uwog.net>
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

class TextToolbar(gtk.Toolbar):
    def __init__(self, abiword_canvas):
        gtk.Toolbar.__init__(self)

        self._abiword_canvas = abiword_canvas

        self._bold = ToggleToolButton('format-text-bold')
        self._bold_id = self._bold.connect('clicked', self._bold_cb)
        self._abiword_canvas.connect('bold', self._isBold_cb)
        self.insert(self._bold, -1)
        self._bold.show()

        # TODO: Add italic ToggleToolButton.

        self._underline = ToggleToolButton('format-text-underline')
        self._underline_id = self._underline.connect('clicked', self._underline_cb)
        self._abiword_canvas.connect('underline', self._isUnderline_cb)
        self.insert(self._underline, -1)
        self._underline.show()

        separator = gtk.SeparatorToolItem()
        separator.set_draw(True)
        self.insert(separator, -1)
        separator.show()

        self._align_left = ToggleToolButton('format-justify-left')
        self._align_left_id = self._align_left.connect('clicked', self._align_left_cb)
        self._abiword_canvas.connect('left-align', self._isLeftAlign_cb)
        self.insert(self._align_left, -1)
        self._align_left.show()

        self._align_center = ToggleToolButton('format-justify-center')
        self._align_center_id = self._align_center.connect('clicked', self._align_center_cb)
        self._abiword_canvas.connect('center-align', self._isCenterAlign_cb)
        self.insert(self._align_center, -1)
        self._align_center.show()
        
        self._align_right = ToggleToolButton('format-justify-right')
        self._align_right_id = self._align_right.connect('clicked', self._align_right_cb)
        self._abiword_canvas.connect('right-align', self._isRightAlign_cb)
        self.insert(self._align_right, -1)
        self._align_right.show()

    def setToggleButtonState(self,button,b,id):
        button.handler_block(id)
        button.set_active(b)
        button.handler_unblock(id)

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

    def _align_left_cb(self, button):
        self._abiword_canvas.align_left()

    def _isLeftAlign_cb(self, abi, b):
        print 'isLeftAlign',b
        self.setToggleButtonState(self._align_left,b,self._align_left_id)

    def _align_center_cb(self, button):
        self._abiword_canvas.align_center()

    def _isCenterAlign_cb(self, abi, b):
        print 'isCenterAlign',b
        self.setToggleButtonState(self._align_center,b,self._align_center_id)

    def _align_right_cb(self, button):
        self._abiword_canvas.align_right()

    def _isRightAlign_cb(self, abi, b):
        print 'isRightAlign',b
        self.setToggleButtonState(self._align_right,b,self._align_right_id)

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
