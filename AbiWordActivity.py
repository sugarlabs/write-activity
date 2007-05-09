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
import os
import time

import gtk

from sugar.activity import activity
from sugar.datastore import datastore
from sugar.datastore.datastore import Text
from sugar import profile
from abiword import Canvas

from toolbar import TextToolbar, ImageToolbar, TableToolbar, ViewToolbar

class AbiWordActivity (activity.Activity):

    def __init__ (self, handle):
        activity.Activity.__init__ (self, handle)
        self.set_title ("Write")

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

        if handle.object_id:
            self._journal_handle = handle.object_id
            obj = datastore.read(handle.object_id)
            self.abiword_canvas.load_file('file://' + obj.get_file_path())
        else:
            # open a blank file
            self.abiword_canvas.load_file("")

        self.abiword_canvas.show()

        self.connect('focus-out-event', self._focus_out_event_cb)
        self.connect('delete-event', self._delete_event_cb)

    def _can_undo_cb(self, canvas, can_undo):
        self._edit_toolbar.undo.set_sensitive(can_undo)

    def _can_redo_cb(self, canvas, can_redo):
        self._edit_toolbar.redo.set_sensitive(can_redo)

    def _undo_cb(self, button):
        self.abiword_canvas.undo()

    def _redo_cb(self, button):
        self.abiword_canvas.redo()

    def _focus_out_event_cb(self, widget, event):
        self._autosave()

    def _delete_event_cb(self, widget, event):
        self._autosave()

    def _autosave(self):
        text_content = self.abiword_canvas.get_content(".txt")[0]
        if not self._journal_handle:
            home_dir = os.path.expanduser('~')
            journal_dir = os.path.join(home_dir, "Journal")
            text = Text({'preview'      : text_content[0:60],
                         'date'         : str(time.time()),
                         'title'        : text_content[0:30],
                         'icon'         : 'theme:object-text',
                         'keep'         : '0',
                         'buddies'      : str([ { 'name' : profile.get_nick_name(),
                                                  'color': profile.get_color().to_string() }]),
                         'icon-color'   : profile.get_color().to_string()})
            f = open(os.path.join(journal_dir, '%i.abw' % time.time()), 'w')
            try:
                f.write(self.abiword_canvas.get_content(".abw")[0])
            finally:
                f.close()
            text.set_file_path(f.name)
            self._journal_handle = datastore.write(text)
        elif text_content != self._last_saved_text:
            text = datastore.read(self._journal_handle)
            metadata = text.get_metadata()
            metadata['preview'] = text_content[0:60]
            metadata['title'] = text_content[0:30]
            metadata['date'] = str(time.time())
            f = open(text.get_file_path(), 'w')
            try:
                f.write(self.abiword_canvas.get_content(".abw")[0])
            finally:
                f.close()
            datastore.write(text)

        self._last_saved_text = text_content
