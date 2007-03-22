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
        os.chdir(os.path.expanduser("~"))

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

        if handle.uri:
            self.abiword_canvas.load_file(handle.uri)
        else:
            # open a blank file
            self.abiword_canvas.load_file("")

        self.abiword_canvas.show()
