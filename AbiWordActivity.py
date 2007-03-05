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
import os
import time

import gobject
import hippo

from sugar.activity import activity
from sugar.datastore import datastore
from sugar.datastore.datastore import Text
from sugar import profile
from abiword import Canvas

from toolbar import AbiToolbar

class AbiWordActivity (activity.Activity):

    def __init__ (self, handle):
        activity.Activity.__init__ (self, handle)
        self.set_title ("Write")

        self._journal_handle = None
        self._last_saved_text = None

        hippoCanvasBox = hippo.CanvasBox()
        self.set_root(hippoCanvasBox)

        # create our main abiword canvas
        self.abiword_canvas = Canvas()

        # create and add a toolbar for our window, which listens to our canvas
        abiToolbar = AbiToolbar(hippoCanvasBox, self.abiword_canvas)

        # create a hippo container to embed our canvas in
        abiwordCanvasContainer = hippo.CanvasWidget()
        abiwordCanvasContainer.props.widget = self.abiword_canvas

        # add the controls to our window
        hippoCanvasBox.append(abiwordCanvasContainer, hippo.PACK_EXPAND)

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
