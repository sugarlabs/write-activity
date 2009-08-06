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

# Abiword needs this to happen as soon as possible
import gobject
gobject.threads_init()

import dbus
import gtk
import telepathy
import telepathy.client

from sugar.graphics.toolcombobox import ToolComboBox
from sugar.graphics.toolbarbox import ToolbarButton, ToolbarBox
from sugar.activity import activity
from sugar.activity.widgets import *
from sugar.presence import presenceservice
from sugar.graphics import style

from abiword import Canvas
import toolbar
import widgets
from sugar.activity.activity import get_bundle_path

logger = logging.getLogger('write-activity')

class AbiWordActivity (activity.Activity):

    def __init__ (self, handle):
        activity.Activity.__init__ (self, handle)

        # abiword uses the current directory for all its file dialogs
        os.chdir(os.path.expanduser('~'))

        # create our main abiword canvas
        self.abiword_canvas = Canvas()

        toolbar_box = ToolbarBox()

        activity_button = ActivityToolbarButton(self)
        toolbar_box.toolbar.insert(activity_button, 0)

        separator = gtk.SeparatorToolItem()
        toolbar_box.toolbar.insert(separator, -1)

        text_toolbar = ToolbarButton(
                page=toolbar.TextToolbar(self.abiword_canvas),
                icon_name='format-text-size')
        toolbar_box.toolbar.insert(text_toolbar, -1)

        text_toolbar = ToolbarButton(
                page=toolbar.ParagraphToolbar(self.abiword_canvas),
                icon_name='paragraph-bar')
        toolbar_box.toolbar.insert(text_toolbar, -1)

        separator = gtk.SeparatorToolItem()
        toolbar_box.toolbar.insert(separator, -1)

        copy = CopyButton()
        copy.connect('clicked', lambda button: self.abiword_canvas.copy())
        toolbar_box.toolbar.insert(copy, -1)

        paste = PasteButton()
        paste.connect('clicked', lambda button: self.abiword_canvas.paste())
        toolbar_box.toolbar.insert(paste, -1)

        separator = gtk.SeparatorToolItem()
        toolbar_box.toolbar.insert(separator, -1)

        undo = UndoButton(sensitive=False)
        undo.connect('clicked', lambda button: self.abiword_canvas.undo())
        self.abiword_canvas.connect("can-undo", lambda abi, can_undo:
                undo.set_sensitive(can_undo))
        toolbar_box.toolbar.insert(undo, -1)

        redo = RedoButton(sensitive=False)
        redo.connect('clicked', lambda button: self.abiword_canvas.redo())
        self.abiword_canvas.connect("can-redo", lambda abi, can_redo:
                redo.set_sensitive(can_redo))
        toolbar_box.toolbar.insert(redo, -1)

        separator = gtk.SeparatorToolItem()
        toolbar_box.toolbar.insert(separator, -1)

        self.abiword_canvas.connect('text-selected', lambda abi, b:
                copy.set_sensitive(True))
        self.abiword_canvas.connect('image-selected', lambda abi, b:
                copy.set_sensitive(True))
        self.abiword_canvas.connect('selection-cleared', lambda abi, b:
                copy.set_sensitive(False))

        insert_toolbar = ToolbarButton(
                page=toolbar.InsertToolbar(self.abiword_canvas),
                icon_name='transfer-from')
        toolbar_box.toolbar.insert(insert_toolbar, -1)

        search_toolbar = ToolbarButton(
                page=toolbar.SearchToolbar(self.abiword_canvas, toolbar_box),
                icon_name='search-bar')
        toolbar_box.toolbar.insert(search_toolbar, -1)

        view_toolbar = ToolbarButton(
                page=toolbar.ViewToolbar(self.abiword_canvas),
                icon_name='toolbar-view')
        toolbar_box.toolbar.insert(view_toolbar, -1)

        separator = gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        separator.show()
        toolbar_box.toolbar.insert(separator, -1)

        stop = StopButton(self)
        toolbar_box.toolbar.insert(stop, -1)

        toolbar_box.show_all()
        self.set_toolbar_box(toolbar_box)

        self.set_canvas(self.abiword_canvas)
        self.abiword_canvas.connect_after('map-event', self.__map_event_cb)
        self.abiword_canvas.show()

        self._zoom_handler = self.abiword_canvas.connect("zoom", self.__zoom_cb)

    def __zoom_cb(self, abi, zoom):
        abi.disconnect(self._zoom_handler)

        # XXX workarond code to redraw abi document on every resize, see #1121
        def size_allocate_cb(abi, alloc):
            zoom = abi.get_zoom_percentage()
            abi.set_zoom_percentage(zoom)
        abi.set_zoom_percentage(zoom)
        abi.connect('size-allocate', size_allocate_cb)

    def __map_event_cb(self, event, activity):
        logger.debug('__map_event_cb')

        # set custom keybindings for Write
        logger.debug("Loading keybindings")
        keybindings_file = os.path.join( get_bundle_path(), "keybindings.xml" )
        self.abiword_canvas.invoke_cmd(
                'com.abisource.abiword.loadbindings.fromURI',
                keybindings_file, 0, 0)

        # no ugly borders please
        self.abiword_canvas.set_property("shadow-type", gtk.SHADOW_NONE)

        # we only do per-word selections (when using the mouse)
        self.abiword_canvas.set_word_selections(True)

        # we want a nice border so we can select paragraphs easily
        self.abiword_canvas.set_show_margin(True)

        # activity sharing
        self.participants = {}
        pservice = presenceservice.get_instance()

        bus = dbus.Bus()
        name, path = pservice.get_preferred_connection()
        self.conn = telepathy.client.Connection(name, path)
        self.initiating = None
        self.joined = False

        self.connect('shared', self._shared_cb)

        if self._shared_activity:
            # we are joining the activity
            logger.debug("We are joining an activity")
            self.connect('joined', self._joined_cb)
            self._shared_activity.connect('buddy-joined', self._buddy_joined_cb)
            self._shared_activity.connect('buddy-left', self._buddy_left_cb)
            if self.get_shared():
#                # oh, OK, we've already joined
                self._joined_cb()
        else:
            # we are creating the activity
            logger.debug("We are creating an activity")

        owner = pservice.get_owner()

    def get_preview(self):
        if not hasattr(self.abiword_canvas, 'render_page_to_image'):
            return activity.Activity.get_preview(self)

        pixbuf = self.abiword_canvas.render_page_to_image(1)
        pixbuf = pixbuf.scale_simple(style.zoom(300), style.zoom(225),
                                     gtk.gdk.INTERP_BILINEAR)

        preview_data = []
        def save_func(buf, data):
            data.append(buf)

        pixbuf.save_to_callback(save_func, 'png', user_data=preview_data)
        preview_data = ''.join(preview_data)

        return preview_data

    def _shared_cb(self, activity):
        logger.debug('My Write activity was shared')
        self.initiating = True
        self._setup()

        self._shared_activity.connect('buddy-joined', self._buddy_joined_cb)
        self._shared_activity.connect('buddy-left', self._buddy_left_cb)

        logger.debug('This is my activity: offering a tube...')
        id = self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].OfferDBusTube(
            "com.abisource.abiword.abicollab", {})
        logger.debug('Tube address: %s', self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].GetDBusTubeAddress(id))


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
                self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].AcceptDBusTube(id)

            initiator_path = None;
            contacts = self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].GetDBusNames(id)
            #print 'dbus contact mapping',self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].GetDBusNames(id)
            for i, struct in enumerate(contacts):
                #print 'mapping i',i
                handle, path = struct
                if handle == initiator:
                    logger.debug('found initiator dbus path: %s', path)
                    initiator_path = path
                    break;

            if initiator_path is None:
                logger.error('Unable to get the dbus path of the tube initiator')
            else:
                # pass this tube to abicollab
                address = self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].GetDBusTubeAddress(id)
                if self.joined:
                    logger.debug('Passing tube address to abicollab (join): %s', address)
                    self.abiword_canvas.invoke_cmd('com.abisource.abiword.abicollab.olpc.joinTube', address, 0, 0)
                    if initiator_path is not None:
                        logger.debug('Adding the initiator to the session: %s', initiator_path)
                        self.abiword_canvas.invoke_cmd('com.abisource.abiword.abicollab.olpc.buddyJoined', initiator_path, 0, 0)
                else:
                    logger.debug('Passing tube address to abicollab (offer): %s', address)
                    self.abiword_canvas.invoke_cmd('com.abisource.abiword.abicollab.olpc.offerTube', address, 0, 0)

            self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].connect_to_signal('DBusNamesChanged',
                self._on_dbus_names_changed)

            # HACK, as DBusNamesChanged doesn't fire on buddies leaving
            self.tubes_chan[telepathy.CHANNEL_INTERFACE_GROUP].connect_to_signal('MembersChanged',
                self._on_members_changed)

    def _on_dbus_names_changed(self, tube_id, added, removed):
        logger.debug('_on_dbus_names_changed')
#        if tube_id == self.tube_id:
        for handle, bus_name in added:
            logger.debug('added handle: %s, with dbus_name: %s', handle, bus_name)
            self.abiword_canvas.invoke_cmd('com.abisource.abiword.abicollab.olpc.buddyJoined', bus_name, 0, 0)
            self.participants[handle] = bus_name

#            if handle == self.self_handle:
                # I've just joined - set my unique name
#                print 'i\'ve just joined'
#                self.set_unique_name(bus_name)
#            self.participants[handle] = bus_name
#            self.bus_name_to_handle[bus_name] = handle

# HACK: doesn't work yet, bad morgs!
#        for handle in removed:
#            logger.debug('removed handle: %s, with dbus name: %s', handle, bus_name)
#            bus_name = self.participants.pop(handle, None)

    def _on_members_changed(self, message, added, removed, local_pending, remote_pending, actor, reason):
        logger.debug("_on_members_changed")
        for handle in removed:
            bus_name = self.participants.pop(handle, None)
            if bus_name is None:
                # FIXME: that shouldn't happen so probably hide another bug.
                # Should be investigated
                continue

            logger.debug('removed handle: %d, with dbus name: %s', handle,
                         bus_name)
            self.abiword_canvas.invoke_cmd('com.abisource.abiword.abicollab.olpc.buddyLeft', bus_name, 0, 0)

    def _buddy_joined_cb (self, activity, buddy):
        logger.debug('buddy joined with object path: %s', buddy.object_path())
#        self.abiword_canvas.invoke_cmd('com.abisource.abiword.abicollab.olpc.buddyJoined', buddy.object_path(), 0, 0)

    def _buddy_left_cb (self,  activity, buddy):
        logger.debug('buddy left with object path: %s', buddy.object_path())
        #self.abiword_canvas.invoke_cmd('com.abisource.abiword.abicollab.olpc.buddyLeft', self.participants[buddy.object_path()], 0, 0)

    def read_file(self, file_path):
        logging.debug('AbiWordActivity.read_file: %s, mimetype: %s', file_path, self.metadata['mime_type'])
        if 'source' in self.metadata and self.metadata['source'] == '1':
            logger.debug('Opening file in view source mode')
            self.abiword_canvas.load_file('file://' + file_path, 'text/plain') 
        else:
            self.abiword_canvas.load_file('file://' + file_path, '') # we pass no mime/file type, let libabiword autodetect it, so we can handle multiple file formats

    def write_file(self, file_path):
        logging.debug('AbiWordActivity.write_file')

        # check if we have a default mimetype; if not, fall back to OpenDocument
        # also fallback if we know we cannot export in that format
        if 'mime_type' not in self.metadata or self.metadata['mime_type'] == '' or \
            self.metadata['mime_type'] == 'application/msword':
            self.metadata['mime_type'] = 'application/vnd.oasis.opendocument.text'

        # if we were viewing the source of a file, 
        # then always save as plain text
        actual_mimetype = self.metadata['mime_type'];
        if 'source' in self.metadata and self.metadata['source'] == '1':
            logger.debug('Writing file as type source (text/plain)')
            actual_mimetype = 'text/plain'

        self.metadata['fulltext'] = self.abiword_canvas.get_content(extension_or_mimetype=".txt")[:3000]
        self.abiword_canvas.save('file://' + file_path, actual_mimetype, '');
