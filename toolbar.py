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

import logging
import abiword
import hippo

from sugar.graphics.toolbar import Toolbar
from sugar.graphics.iconbutton import IconButton
from sugar.graphics.toggleiconbutton import ToggleIconButton

class AbiToolbar(object):
    def __init__(self, hippoCanvasBox, abiword_canvas):
        toolbar = Toolbar()
        hippoCanvasBox.append(toolbar)

        self._abiword_canvas = abiword_canvas

        self._open = IconButton(icon_name='theme:stock-open')
        self._open.connect("activated", self._open_cb)
        toolbar.append(self._open)

        self._save = IconButton(icon_name='theme:stock-save')
        self._save.connect("activated", self._save_cb)
        self._abiword_canvas.connect("is-dirty", self._isDirty_cb)
        toolbar.append(self._save)

        self._undo = IconButton(icon_name='theme:stock-undo')
        self._undo.connect("activated", self._undo_cb)
        self._abiword_canvas.connect("can_undo", self._canUndo_cb)
        toolbar.append(self._undo)

        self._redo = IconButton(icon_name='theme:stock-redo')
        self._redo.connect("activated", self._redo_cb)
        self._abiword_canvas.connect("can_redo", self._canRedo_cb)
        toolbar.append(self._redo)

        self._underline = IconButton(icon_name='theme:stock-underline')
        self._underline_id = self._underline.connect("activated", self._underline_cb)
        self._abiword_canvas.connect("underline", self._isUnderline_cb)
        toolbar.append(self._underline)

        self._bold = ToggleIconButton(icon_name='theme:stock-bold')
        self._bold_id = self._bold.connect("activated", self._bold_cb)
        self._abiword_canvas.connect("bold", self._isBold_cb)
        toolbar.append(self._bold)

        #
        # alignment buttons
        #
        self._align_left = ToggleIconButton(icon_name='theme:stock-justify-left')
        self._align_left.connect("activated", self._align_left_cb)
        self._abiword_canvas.connect("left-align", self._isLeftAlign_cb)
        toolbar.append(self._align_left)

        self._align_center = ToggleIconButton(icon_name='theme:stock-justify-center')
        self._align_center.connect("activated", self._align_center_cb)
        self._abiword_canvas.connect("center-align", self._isCenterAlign_cb)
        toolbar.append(self._align_center)
        
        self._align_right = ToggleIconButton(icon_name='theme:stock-justify-right')
        self._align_right.connect("activated", self._align_right_cb)
        self._abiword_canvas.connect("right-align", self._isRightAlign_cb)
        toolbar.append(self._align_right)

        self._align_fill = ToggleIconButton(icon_name='theme:stock-justify-fill')
        self._align_fill.connect("activated", self._align_fill_cb)
        self._abiword_canvas.connect("justify-align", self._isFillAlign_cb)
        toolbar.append(self._align_fill)

        #
        # images
        #
        self._image = IconButton(icon_name='theme:stock-insert-image')
        self._image_id = self._image.connect("activated", self._image_cb)
        toolbar.append(self._image)

# reenable this after march 6th
#        self._table = abiword.TableCreator()
#        self._table.set_labels("Table", "Cancel")
#        self._table.show()
#        #self._tableCreate.label().hide()

#        tableContainer = hippo.CanvasWidget()
#        tableContainer.props.widget = self._table;
#        self._table_id = self._table.connect("selected", self._table_cb)
        #self._table_id = self._abiword_canvas.connect("table-state", self._tableState)
#        toolbar.append(tableContainer)

#    def setToggleButtonState(self, button, b, id):
#        button.handler_block(id)
#        button.set_active(b)
#        button.handler_unblock(id)

    def _open_cb(self, button):
        self._abiword_canvas.file_open()

    def _save_cb(self, button):
        self._abiword_canvas.file_save()

    def _isDirty_cb(self, abi, b):
        print "isDirty",b
#        self._save.set_sensitive(b)

    def _undo_cb(self, button):
        self._abiword_canvas.undo()

    def _canUndo_cb(self, abi, b):
        print "canUndo",b
#        self._undo.set_sensitive(b)

    def _redo_cb(self, button):
        self._abiword_canvas.redo()

    def _canRedo_cb(self, abi ,b):
        print "canRedo",b
#        self._redo.set_sensitive(b)

    def _underline_cb(self, button):
        self._abiword_canvas.toggle_underline()

    def _isUnderline_cb(self, abi, b):
        print "isUnderline",b
#        self.setToggleButtonState(self._underline, b, self._underline_id)

    def _bold_cb(self, button):
        self._abiword_canvas.toggle_bold()

    def _isBold_cb(self, abi, b):
        print "isBold",b
#        self.setToggleButtonState(self._bold,b,self._bold_id)

    def _align_left_cb(self, button):
        self._abiword_canvas.align_left()

    def _isLeftAlign_cb(self, abi, b):
        print "isLeftAlign",b
        self._align_left.active = b

    def _align_center_cb(self, button):
        self._abiword_canvas.align_center()

    def _isCenterAlign_cb(self, abi, b):
        print "isCenterAlign",b
        self._align_center.active = b

    def _align_right_cb(self, button):
        self._abiword_canvas.align_right()

    def _isRightAlign_cb(self, abi, b):
        print "isRightAlign",b
        self._align_right.active = b

    def _align_fill_cb(self, button):
        self._abiword_canvas.align_justify()

    def _isFillAlign_cb(self, abi, b):
        print "isFillAlign",b
        self._align_fill.active = b

    def _image_cb(self, button):
        print "fileInsertGraphic"
        self._abiword_canvas.invoke_cmd("fileInsertGraphic", "", 0, 0)

#    def _table_cb(self, abi, rows, cols):
#        self._abiword_canvas.insert_table(rows,cols)
