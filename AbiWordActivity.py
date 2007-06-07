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
import shutil

import dbus
import gtk
import telepathy
import telepathy.client

from sugar.activity.activity import Activity, ActivityToolbox, EditToolbar
from sugar.presence import presenceservice

from abiword import Canvas
from toolbar import TextToolbar, ImageToolbar, TableToolbar, ViewToolbar

logger = logging.getLogger('write-activity')

class AbiWordActivity (Activity):

    def __init__ (self, handle):
        Activity.__init__ (self, handle)
        self.set_title ("Write")

        # abiword uses the current directory for all its file dialogs 
        os.chdir(os.path.expanduser('~'))

        toolbox = ActivityToolbox(self)
        self.set_toolbox(toolbox)
        toolbox.show()

        self._file_opened = False

        # create our main abiword canvas
        self.abiword_canvas = Canvas()
        self.abiword_canvas.connect("can-undo", self._can_undo_cb)
        self.abiword_canvas.connect("can-redo", self._can_redo_cb)
        self.abiword_canvas.connect('text-selected', self._selection_cb)
        self.abiword_canvas.connect('image-selected', self._selection_cb)
        self.abiword_canvas.connect('selection-cleared', self._selection_cleared_cb)

        self._edit_toolbar = EditToolbar()

        self._edit_toolbar.undo.set_sensitive(False)
        self._edit_toolbar.undo.connect('clicked', self._undo_cb)

        self._edit_toolbar.redo.set_sensitive(False)
        self._edit_toolbar.redo.connect('clicked', self._redo_cb)

        self._edit_toolbar.copy.connect('clicked', self._copy_cb)
        self._edit_toolbar.paste.connect('clicked', self._paste_cb)

        toolbox.add_toolbar(_('Edit'), self._edit_toolbar)
        self._edit_toolbar.show()

        text_toolbar = TextToolbar(toolbox, self.abiword_canvas)
        toolbox.add_toolbar(_('Text'), text_toolbar)
        text_toolbar.show()

        image_toolbar = ImageToolbar(toolbox, self.abiword_canvas)
        toolbox.add_toolbar(_('Image'), image_toolbar)
        image_toolbar.show()

        table_toolbar = TableToolbar(toolbox, self.abiword_canvas)
        toolbox.add_toolbar(_('Table'), table_toolbar)
        table_toolbar.show()

        view_toolbar = ViewToolbar(self.abiword_canvas)
        toolbox.add_toolbar(_('View'), view_toolbar)
        view_toolbar.show()

        self.set_canvas(self.abiword_canvas)
        self.abiword_canvas.show()

        self.abiword_canvas.connect_after('map', self._map_cb)

    def _map_cb(self, activity):
        logger.debug('_map_cb')

        # always make sure at least 1 document is loaded (bad bad widget design)
        if not self._file_opened:
            print "Loading empty doc"
            self.abiword_canvas.load_file('', '');  

        # activity sharing
        pservice = presenceservice.get_instance()

        bus = dbus.Bus()
        name, path = pservice.get_preferred_connection()
        self.conn = telepathy.client.Connection(name, path)
        self.initiating = None
        self.joined = False

        self.connect('shared', self._shared_cb)

        if self._shared_activity:
            # we are joining the activity
            print "We are joining an activity"
            self.connect('joined', self._joined_cb)
            self._shared_activity.connect('buddy-joined', self._buddy_joined_cb)
            self._shared_activity.connect('buddy-left', self._buddy_left_cb)
            if self.get_shared():
#                # oh, OK, we've already joined
                self._joined_cb()
        else:
            # we are creating the activity
            print "We are creating an activity"

        owner = pservice.get_owner()

    def _shared_cb(self, activity):
        logger.debug('My Write activity was shared')
        self.initiating = True
        self._setup()
        
        self._shared_activity.connect('buddy-joined', self._buddy_joined_cb)
        self._shared_activity.connect('buddy-left', self._buddy_left_cb)

        logger.debug('This is my activity: offering a tube...')
        id = self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].OfferTube(
            telepathy.TUBE_TYPE_DBUS, "com.abisource.abiword.abicollab", {})
        logger.debug('Tube address: %s', self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].GetDBusServerAddress(id))

    def _setup(self):
        logger.debug("_setup()")

        if self._shared_activity is None:
            logger.error('Failed to share or join activity')
            return

        bus_name, conn_path, channel_paths = self._shared_activity.get_channels()

        # Work out what our room is called and whether we have Tubes already
        room = None
        tubes_chan = None
        text_chan = None
        for channel_path in channel_paths:
            channel = telepathy.client.Channel(bus_name, channel_path)
            htype, handle = channel.GetHandle()
            if htype == telepathy.HANDLE_TYPE_ROOM:
                logger.debug('Found our room: it has handle#%d "%s"',
                    handle, self.conn.InspectHandles(htype, [handle])[0])
                room = handle
                ctype = channel.GetChannelType()
                if ctype == telepathy.CHANNEL_TYPE_TUBES:
                    logger.debug('Found our Tubes channel at %s', channel_path)
                    tubes_chan = channel
                elif ctype == telepathy.CHANNEL_TYPE_TEXT:
                    logger.debug('Found our Text channel at %s', channel_path)
                    text_chan = channel

        if room is None:
            logger.error("Presence service didn't create a room")
            return
        if text_chan is None:
            logger.error("Presence service didn't create a text channel")
            return

        # Make sure we have a Tubes channel - PS doesn't yet provide one
        if tubes_chan is None:
            logger.debug("Didn't find our Tubes negotation channel, requesting one...")
            tubes_chan = self.conn.request_channel(telepathy.CHANNEL_TYPE_TUBES,
                telepathy.HANDLE_TYPE_ROOM, room, True)
            logger.debug("Got our tubes negotiation channel")

        self.tubes_chan = tubes_chan
        self.text_chan = text_chan

        tubes_chan[telepathy.CHANNEL_TYPE_TUBES].connect_to_signal('NewTube',
            self._new_tube_cb)

    def _list_tubes_reply_cb(self, tubes):
        for tube_info in tubes:
            self._new_tube_cb(*tube_info)

    def _list_tubes_error_cb(self, e):
        logger.error('ListTubes() failed: %s', e)

    def _joined_cb(self, activity):
        logger.debug("_joined_cb()")
        if not self._shared_activity:
            return

        self.joined = True
        logger.debug('Joined an existing Write session')
        self._setup()

        logger.debug('This is not my activity: waiting for a tube...')
        self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].ListTubes(
            reply_handler=self._list_tubes_reply_cb,
            error_handler=self._list_tubes_error_cb)

    def _new_tube_cb(self, id, initiator, type, service, params, state):
        logger.debug('New tube: ID=%d initiator=%d type=%d service=%s '
                     'params=%r state=%d', id, initiator, type, service,
                     params, state)

        if (type == telepathy.TUBE_TYPE_DBUS and
            service == "com.abisource.abiword.abicollab"):
            if state == telepathy.TUBE_STATE_LOCAL_PENDING:
                self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].AcceptTube(id)

            initiator_path = None;
            contacts = self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].GetDBusNames(id)
            print 'dbus contact mapping',self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].GetDBusNames(id)
            for i, struct in enumerate(contacts):
                print 'mapping i',i
                handle, path = struct
                if handle == initiator:
                    print 'found initiator dbus path:',path
                    initiator_path = path
                    break;

            if initiator_path is None:
                logger.error('Unable to get the dbus path of the tube initiator')
            else:
                # pass this tube to abicollab
                address = self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].GetDBusServerAddress(id)
                if self.joined:
                    print 'Passing tube address to abicollab (join)', address
                    self.abiword_canvas.invoke_cmd('com.abisource.abiword.abicollab.olpc.joinTube', address, 0, 0)
                    if initiator_path is not None:
                        logger.debug('Adding the initiator to the session: %s', initiator_path)
                        self.abiword_canvas.invoke_cmd('com.abisource.abiword.abicollab.olpc.buddyJoined', initiator_path, 0, 0)
                else:
                    logger.debug('Passing tube address to abicollab (offer): %s', address)
                    self.abiword_canvas.invoke_cmd('com.abisource.abiword.abicollab.olpc.offerTube', address, 0, 0)

            self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].connect_to_signal('DBusNamesChanged',
                self._on_dbus_names_changed)

    def _on_dbus_names_changed(self, tube_id, added, removed):
        logger.debug('_on_dbus_names_changed')
#        if tube_id == self.tube_id:
        for handle, bus_name in added:
            logger.debug('added handle: %s, with dbus_name: %s', handle, bus_name)
            self.abiword_canvas.invoke_cmd('com.abisource.abiword.abicollab.olpc.buddyJoined', bus_name, 0, 0)

#            if handle == self.self_handle:
                # I've just joined - set my unique name
#                print 'i\'ve just joined'
#                self.set_unique_name(bus_name)
#            self.participants[handle] = bus_name
#            self.bus_name_to_handle[bus_name] = handle

        for handle, bus_name in removed:
            logger.debug('removed handle: %s, with dbus name: %s', handle, bus_name)

    def _buddy_joined_cb (self, activity, buddy):
        print 'buddy joined with object path: %s',buddy.object_path()
#        self.abiword_canvas.invoke_cmd('com.abisource.abiword.abicollab.olpc.buddyJoined', buddy.object_path(), 0, 0)

    def _buddy_left_cb (self,  activity, buddy):
        logger.debug('buddy left with object path: %s', buddy.object_path())
        self.abiword_canvas.invoke_cmd('com.abisource.abiword.abicollab.olpc.buddyLeft', buddy.object_path(), 0, 0)

    def read_file(self, file_path):
        logging.debug('AbiWordActivity.read_file: %s', file_path)
        self.abiword_canvas.load_file('file://' + file_path, ".odt")
        self._file_opened = True

    def write_file(self, file_path):
        logging.debug('AbiWordActivity.write_file')

        text_content = self.abiword_canvas.get_content(".txt")[0]
        self.metadata['preview'] = text_content[0:60]
        f = open(file_path, 'w')
        try:
            logger.debug('Writing content as .odt')
            content, length = self.abiword_canvas.get_content(".odt")
            logger.debug('Content length: %d', length)
            f.write(content)
        finally:
            f.close()

    def _can_undo_cb(self, canvas, can_undo):
        self._edit_toolbar.undo.set_sensitive(can_undo)

    def _can_redo_cb(self, canvas, can_redo):
        self._edit_toolbar.redo.set_sensitive(can_redo)

    def _undo_cb(self, button):
        self.abiword_canvas.undo()

    def _redo_cb(self, button):
        self.abiword_canvas.redo()

    def _copy_cb(self, button):
        self.abiword_canvas.copy()

    def _paste_cb(self, button):
        self.abiword_canvas.paste()

    def _selection_cb(self, abi, b):
        self._edit_toolbar.copy.set_sensitive(True)

    def _selection_cleared_cb(self, abi, b):
        self._edit_toolbar.copy.set_sensitive(False)
