# Copyright (C) 2006 by Martin Sevior
# Copyright (C) 2006-2007 Marc Maurer <uwog@uwog.net>
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
import os
import time

import gtk

from sugar.activity import activity
from abiword import Canvas

from toolbar import TextToolbar, ImageToolbar, TableToolbar, ViewToolbar

class AbiWordActivity (activity.Activity):

    def __init__ (self, handle):
        activity.Activity.__init__ (self, handle)
        self.set_title ("Write")

        # abiword uses the current directory for all its file dialogs 
        os.chdir(os.path.expanduser('~'))

        toolbox = activity.ActivityToolbox(self)
        self.set_toolbox(toolbox)
        toolbox.show()

        self._journal_handle = None
        self._last_saved_text = None

        # create our main abiword canvas
        self.abiword_canvas = Canvas()
        self.abiword_canvas.connect("can-undo", self._can_undo_cb)
        self.abiword_canvas.connect("can-redo", self._can_redo_cb)

        self._edit_toolbar = activity.EditToolbar()

        self._edit_toolbar.undo.set_sensitive(False)
        self._edit_toolbar.undo.connect('clicked', self._undo_cb)

        self._edit_toolbar.redo.set_sensitive(False)
        self._edit_toolbar.redo.connect('clicked', self._redo_cb)

        toolbox.add_toolbar(_('Edit'), self._edit_toolbar)
        self._edit_toolbar.show()

        text_toolbar = TextToolbar(self.abiword_canvas)
        toolbox.add_toolbar(_('Text'), text_toolbar)
        text_toolbar.show()

        image_toolbar = ImageToolbar(self.abiword_canvas)
        toolbox.add_toolbar(_('Image'), image_toolbar)
        image_toolbar.show()

        table_toolbar = TableToolbar(self.abiword_canvas)
        toolbox.add_toolbar(_('Table'), table_toolbar)
        table_toolbar.show()

        view_toolbar = ViewToolbar(self.abiword_canvas)
        toolbox.add_toolbar(_('View'), view_toolbar)
        view_toolbar.show()

        self.set_canvas(self.abiword_canvas)

        # FIXME: we need to load_file('') before show(), why?
        self.abiword_canvas.load_file('')
        self.abiword_canvas.show()

        if not self.jobject['title']:
            self.jobject['title'] = _('Text document')
        
        # FIXME: this should be called by activity.Activity on realize
        self.read_file()

    def read_file(self):
        logging.debug('AbiWordActivity.read_file')
        self.abiword_canvas.load_file('file://' + self.jobject.file_path)

    def write_file(self):
        text_content = self.abiword_canvas.get_content(".txt")[0]
        self.jobject['preview'] = text_content[0:60]
        self.jobject['icon'] = 'theme:object-text'
        f = open(self.jobject.file_path, 'w')
        try:
            f.write(self.abiword_canvas.get_content(".abw")[0])
        finally:
            f.close()

        self._last_saved_text = text_content

        return f.name

    def _can_undo_cb(self, canvas, can_undo):
        self._edit_toolbar.undo.set_sensitive(can_undo)

    def _can_redo_cb(self, canvas, can_redo):
        self._edit_toolbar.redo.set_sensitive(can_redo)

    def _undo_cb(self, button):
        self.abiword_canvas.undo()

    def _redo_cb(self, button):
        self.abiword_canvas.redo()
