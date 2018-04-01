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

# Abiword needs this to happen as soon as possible
from gi.repository import GObject
GObject.threads_init()

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import telepathy
import telepathy.client
import dbus

from sugar3.activity import activity
from sugar3.activity.widgets import StopButton
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.activity.activity import get_bundle_path

from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toolbarbox import ToolbarButton, ToolbarBox
from sugar3.graphics import style
from sugar3.graphics.icon import Icon
from sugar3.graphics.xocolor import XoColor
from sugar3.graphics.palettemenu import PaletteMenuBox
from sugar3.graphics.palettemenu import PaletteMenuItem

from toolbar import EditToolbar
from toolbar import ViewToolbar
from toolbar import TextToolbar
from toolbar import InsertToolbar
from toolbar import ParagraphToolbar
from widgets import ExportButtonFactory
from widgets import DocumentView
from sugar3.graphics.objectchooser import ObjectChooser
try:
    from sugar3.graphics.objectchooser import FILTER_TYPE_GENERIC_MIME
except:
    FILTER_TYPE_GENERIC_MIME = 'generic_mime'

logger = logging.getLogger('write-activity')


class ConnectingBox(Gtk.VBox):

    def __init__(self):
        Gtk.VBox.__init__(self)
        self.props.halign = Gtk.Align.CENTER
        self.props.valign = Gtk.Align.CENTER
        waiting_icon = Icon(icon_name='zoom-neighborhood',
                            pixel_size=style.STANDARD_ICON_SIZE)
        waiting_icon.set_xo_color(XoColor('white'))
        self.add(waiting_icon)
        self.add(Gtk.Label(_('Connecting...')))
        self.show_all()
        self.hide()


class AbiWordActivity(activity.Activity):

    def __init__(self, handle):
        activity.Activity.__init__(self, handle)

        # abiword uses the current directory for all its file dialogs
        os.chdir(os.path.expanduser('~'))

        # create our main abiword canvas
        self.abiword_canvas = DocumentView()
        self._new_instance = True
        toolbar_box = ToolbarBox()

        self.activity_button = ActivityToolbarButton(self)
        toolbar_box.toolbar.insert(self.activity_button, -1)

        separator = Gtk.SeparatorToolItem()
        separator.show()
        self.activity_button.props.page.insert(separator, 2)
        ExportButtonFactory(self, self.abiword_canvas)
        self.activity_button.show()

        edit_toolbar = ToolbarButton()
        edit_toolbar.props.page = EditToolbar(self, toolbar_box)
        edit_toolbar.props.icon_name = 'toolbar-edit'
        edit_toolbar.props.label = _('Edit')
        toolbar_box.toolbar.insert(edit_toolbar, -1)

        view_toolbar = ToolbarButton()
        view_toolbar.props.page = ViewToolbar(self.abiword_canvas)
        view_toolbar.props.icon_name = 'toolbar-view'
        view_toolbar.props.label = _('View')
        toolbar_box.toolbar.insert(view_toolbar, -1)

        # due to http://bugzilla.abisource.com/show_bug.cgi?id=13585
        if self.abiword_canvas.get_version() != '3.0':
            self.speech_toolbar_button = ToolbarButton(icon_name='speak')
            toolbar_box.toolbar.insert(self.speech_toolbar_button, -1)
            self._init_speech()

        separator = Gtk.SeparatorToolItem()
        toolbar_box.toolbar.insert(separator, -1)

        text_toolbar = ToolbarButton()
        text_toolbar.props.page = TextToolbar(self.abiword_canvas)
        text_toolbar.props.icon_name = 'format-text'
        text_toolbar.props.label = _('Text')
        toolbar_box.toolbar.insert(text_toolbar, -1)

        para_toolbar = ToolbarButton()
        para_toolbar.props.page = ParagraphToolbar(self.abiword_canvas)
        para_toolbar.props.icon_name = 'paragraph-bar'
        para_toolbar.props.label = _('Paragraph')
        toolbar_box.toolbar.insert(para_toolbar, -1)

        insert_toolbar = ToolbarButton()
        insert_toolbar.props.page = InsertToolbar(self.abiword_canvas)
        insert_toolbar.props.icon_name = 'insert-table'
        insert_toolbar.props.label = _('Table')
        toolbar_box.toolbar.insert(insert_toolbar, -1)

        image = ToolButton('insert-picture')
        image.set_tooltip(_('Insert Image'))
        self._image_id = image.connect('clicked', self.__image_cb)
        toolbar_box.toolbar.insert(image, -1)

        palette = image.get_palette()
        box = PaletteMenuBox()
        palette.set_content(box)
        box.show()
        menu_item = PaletteMenuItem(_('Floating'))
        menu_item.connect('activate', self.__image_cb, True)
        box.append_item(menu_item)
        menu_item.show()

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_size_request(0, -1)
        separator.set_expand(True)
        separator.show()
        toolbar_box.toolbar.insert(separator, -1)

        stop = StopButton(self)
        toolbar_box.toolbar.insert(stop, -1)

        toolbar_box.show_all()
        self.set_toolbar_box(toolbar_box)

        # add a overlay to be able to show a icon while joining a shared doc
        overlay = Gtk.Overlay()
        overlay.add(self.abiword_canvas)
        overlay.show()

        self._connecting_box = ConnectingBox()
        overlay.add_overlay(self._connecting_box)

        self.set_canvas(overlay)

        # we want a nice border so we can select paragraphs easily
        self.abiword_canvas.set_show_margin(True)

        # Set default font face and size
        self._default_font_face = 'Sans'
        self._default_font_size = 12

        # activity sharing
        self.participants = {}
        self.joined = False

        self.connect('shared', self._shared_cb)

        if self.shared_activity:
            # we are joining the activity
            logger.error('We are joining an activity')
            # display a icon while joining
            self._connecting_box.show()
            # disable the abi widget
            self.abiword_canvas.set_sensitive(False)
            self._new_instance = False
            self.connect('joined', self._joined_cb)
            self.shared_activity.connect('buddy-joined',
                                         self._buddy_joined_cb)
            self.shared_activity.connect('buddy-left', self._buddy_left_cb)
            if self.get_shared():
                self._joined_cb(self)
        else:
            # we are creating the activity
            logger.error("We are creating an activity")

        self.abiword_canvas.zoom_width()
        self.abiword_canvas.show()
        self.connect_after('map-event', self.__map_activity_event_cb)

        self.abiword_canvas.connect('size-allocate', self.size_allocate_cb)

    def _init_speech(self):
        import speech
        from speechtoolbar import SpeechToolbar
        if speech.supported:
            self.speech_toolbar = SpeechToolbar(self)
            self.speech_toolbar_button.set_page(self.speech_toolbar)
            self.speech_toolbar_button.show()

    def size_allocate_cb(self, abi, alloc):
        GObject.idle_add(abi.queue_draw)

    def __map_activity_event_cb(self, event, activity):
        # set custom keybindings for Write
        # we do it later because have problems if done before - OLPC #11049
        logger.error('Loading keybindings')
        keybindings_file = os.path.join(get_bundle_path(), 'keybindings.xml')
        self.abiword_canvas.invoke_ex(
            'com.abisource.abiword.loadbindings.fromURI',
            keybindings_file, 0, 0)
        # set default font
        if self._new_instance:
            self.abiword_canvas.select_all()
            logging.error('Setting default font to %s %d in new documents',
                          self._default_font_face, self._default_font_size)
            self.abiword_canvas.set_font_name(self._default_font_face)
            self.abiword_canvas.set_font_size(str(self._default_font_size))
            self.abiword_canvas.moveto_bod()
            self.abiword_canvas.select_bod()
        if hasattr(self.abiword_canvas, 'toggle_rulers'):
            # this is not available yet on upstream abiword
            self.abiword_canvas.view_print_layout()
            self.abiword_canvas.toggle_rulers(False)

        self.abiword_canvas.grab_focus()

    def get_preview(self):
        if not hasattr(self.abiword_canvas, 'render_page_to_image'):
            return activity.Activity.get_preview(self)

        from gi.repository import GdkPixbuf

        pixbuf = self.abiword_canvas.render_page_to_image(1)
        pixbuf = pixbuf.scale_simple(style.zoom(300), style.zoom(225),
                                     GdkPixbuf.InterpType.BILINEAR)

        preview_data = []

        def save_func(buf, lenght, data):
            data.append(buf)
            return True

        pixbuf.save_to_callbackv(save_func, preview_data, 'png', [], [])
        preview_data = ''.join(preview_data)

        return preview_data

    def _shared_cb(self, activity):
        logger.error('My Write activity was shared')
        self._sharing_setup()

        self.shared_activity.connect('buddy-joined', self._buddy_joined_cb)
        self.shared_activity.connect('buddy-left', self._buddy_left_cb)

        def create_tube_reply_cb(path, props):
            logging.error('DBus tube channel created')
            self._tube_chan = telepathy.client.Channel(self.conn.bus_name, path)
            address = self._tube_chan[telepathy.CHANNEL_TYPE_DBUS_TUBE].Offer( \
                {},
                telepathy.SOCKET_ACCESS_CONTROL_LOCALHOST)
            logging.error('Address: %r', address)
            self._got_tube(props, address)

        def create_tube_error_cb(e):
            logging.error('DBus tube channel creation failed: %s' % e)

        room_handle = self.shared_activity.room_handle
        self.conn.CreateChannel(dbus.Dictionary({
            telepathy.CHANNEL_INTERFACE + ".ChannelType": telepathy.CHANNEL_TYPE_DBUS_TUBE,
            telepathy.CHANNEL_INTERFACE + ".TargetHandleType": telepathy.CONNECTION_HANDLE_TYPE_ROOM,
            telepathy.CHANNEL_INTERFACE + ".TargetHandle": int(room_handle),
            telepathy.CHANNEL_TYPE_DBUS_TUBE + ".ServiceName": 'com.abisource.abiword.abicollab'}, signature='sv'),
            reply_handler=create_tube_reply_cb,
            error_handler=create_tube_error_cb)
        logger.error('This is my activity: offering a tube...')

    def _sharing_setup(self):
        logger.debug("_sharing_setup()")

        if self.shared_activity is None:
            logger.error('Failed to share or join activity')
            return

        self.conn = self.shared_activity.telepathy_conn
        self.text_chan = self.shared_activity.telepathy_text_chan
        self.tube_path = None

    def _joined_cb(self, activity):
        logger.error("_joined_cb()")
        if not self.shared_activity:
            self._enable_collaboration()
            return

        self.joined = True
        logging.error('Joined an existing Write session')
        self._sharing_setup()

        logging.error('This is not my activity: waiting for a tube chan...')
        self._waiting_for_tube = True
        self.conn.connect_to_signal('NewChannels', self.__new_channels_cb)
        self.conn.Get(telepathy.CONNECTION_INTERFACE_REQUESTS, 'Channels',
            reply_handler=self.__get_channels_reply_cb,
            error_handler=self.__get_channels_error_cb)

    def _enable_collaboration(self):
        """
        when communication established, hide the download icon
        and enable the abi widget
        """
        self.abiword_canvas.zoom_width()
        self.abiword_canvas.set_sensitive(True)
        self._connecting_box.hide()

    def __new_channels_cb(self, channels):
        """Callback when a new channel is created. We are interested about the stream tube ones"""
        for path, props in channels:
            if props[telepathy.CHANNEL_INTERFACE + ".ChannelType"] != telepathy.CHANNEL_TYPE_DBUS_TUBE:
                continue

            if self._waiting_for_tube and props[telepathy.CHANNEL_TYPE_DBUS_TUBE + '.ServiceName'] == 'com.abisource.abiword.abicollab':
                logging.debug('I could use this tube chan')
                self._waiting_for_tube = False
                self.tube_path = path
                self._tube_chan = telepathy.client.Channel(self.conn.bus_name, path)
                address = self._tube_chan[telepathy.CHANNEL_TYPE_DBUS_TUBE].Accept( \
                    telepathy.SOCKET_ACCESS_CONTROL_LOCALHOST)
                logging.error('Address %r', address)
                self._enable_collaboration()
                self._got_tube(props, address)

    def __get_channels_reply_cb(self, channels):
        """Callback when existing channels are available."""
        self.__new_channels_cb(channels)

    def __get_channels_error_cb(self, e):
        """Handle get channels error by logging."""
        logging.error('Get channels failed: %s', e)

    def _got_tube(self, props, address):
        # look for the initiator's D-Bus unique name
        initiator_handle = props[telepathy.CHANNEL_INTERFACE + '.InitiatorHandle']
        logging.error('Initiator: %r', initiator_handle)
        dbus_names = self._tube_chan[dbus.PROPERTIES_IFACE].Get(telepathy.CHANNEL_TYPE_DBUS_TUBE, 'DBusNames')
        logging.error('DBus Names: %r', dbus_names)
        initiator_dbus_name = dbus_names.get(initiator_handle)

        if initiator_dbus_name is None:
            logger.error('Unable to get the D-Bus name of the tube initiator')
            return

        cmd_prefix = 'com.abisource.abiword.abicollab.olpc.'
        if self.joined:
            logger.error('Passing tube address to abicollab (join): %s',
                         address)
            self.abiword_canvas.invoke_ex(cmd_prefix + 'joinTube',
                                          address, 0, 0)
            # The intiator of the session has to be the first passed
            # to the Abicollab backend.
            logger.error('Adding the initiator to the session: %s',
                         initiator_dbus_name)
            self.abiword_canvas.invoke_ex(cmd_prefix + 'buddyJoined',
                                          initiator_dbus_name, 0, 0)
        else:
            logger.error('Passing tube address to abicollab (offer): %s',
                         address)
            self.abiword_canvas.invoke_ex(cmd_prefix + 'offerTube', address,
                                          0, 0)
        self.tube_path = id

        self._tube_chan.connect_to_signal('DBusNamesChanged',
                                  self._on_dbus_names_changed)
        self._on_dbus_names_changed(id, dbus_names, [])

    def _on_dbus_names_changed(self, tube_path, added, removed):
        """
        We call com.abisource.abiword.abicollab.olpc.buddy{Joined,Left}
        according members of the D-Bus tube. That's why we don't add/remove
        buddies in _buddy_{joined,left}_cb.
        """
        logger.error('_on_dbus_names_changed')
#        if tube_path == self.tube_path:
        cmd_prefix = 'com.abisource.abiword.abicollab.olpc'
        for handle, bus_name in added.iteritems():
            logger.error('added handle: %s, with dbus_name: %s',
                         handle, bus_name)
            self.abiword_canvas.invoke_ex(cmd_prefix + '.buddyJoined',
                                          bus_name, 0, 0)
            self.participants[handle] = bus_name

    def _on_members_changed(self, message, added, removed, local_pending,
                            remote_pending, actor, reason):
        logger.error("_on_members_changed")
        for handle in removed:
            bus_name = self.participants.pop(handle, None)
            if bus_name is None:
                # FIXME: that shouldn't happen so probably hide another bug.
                # Should be investigated
                continue

            cmd_prefix = 'com.abisource.abiword.abicollab.olpc'
            logger.error('removed handle: %d, with dbus name: %s', handle,
                         bus_name)
            self.abiword_canvas.invoke_ex(cmd_prefix + '.buddyLeft',
                                          bus_name, 0, 0)

    def _buddy_joined_cb(self, activity, buddy):
        logger.error('buddy joined with object path: %s', buddy.object_path())

    def _buddy_left_cb(self, activity, buddy):
        logger.error('buddy left with object path: %s', buddy.object_path())

    def read_file(self, file_path):
        logging.debug('AbiWordActivity.read_file: %s, mimetype: %s',
                      file_path, self.metadata['mime_type'])
        if self._is_plain_text(self.metadata['mime_type']):
            self.abiword_canvas.load_file('file://' + file_path, 'text/plain')
        else:
            # we pass no mime/file type, let libabiword autodetect it,
            # so we can handle multiple file formats
            self.abiword_canvas.load_file('file://' + file_path, '')
        self.abiword_canvas.zoom_width()
        self._new_instance = False

    def write_file(self, file_path):
        logging.debug('AbiWordActivity.write_file: %s, mimetype: %s',
                      file_path, self.metadata['mime_type'])
        # if we were editing a text file save as plain text
        if self._is_plain_text(self.metadata['mime_type']):
            logger.debug('Writing file as type source (text/plain)')
            self.abiword_canvas.save('file://' + file_path, 'text/plain', '')
        else:
            #if the file is new, save in .odt format
            if self.metadata['mime_type'] == '':
                self.metadata['mime_type'] = 'application/rtf'

            # Abiword can't save in .doc format, save in .rtf instead
            if self.metadata['mime_type'] == 'application/msword':
                self.metadata['mime_type'] = 'application/rtf'

            self.abiword_canvas.save('file://' + file_path,
                                     self.metadata['mime_type'], '')

        # due to http://bugzilla.abisource.com/show_bug.cgi?id=13585
        if self.abiword_canvas.get_version() != '3.0':
            self.metadata['fulltext'] = self.abiword_canvas.get_content(
                'text/plain', None)[:3000]

    def _is_plain_text(self, mime_type):
        # These types have 'text/plain' in their mime_parents  but we need
        # use it like rich text
        if mime_type in ['application/rtf', 'text/rtf', 'text/html']:
            return False

        from sugar3 import mime

        mime_parents = mime.get_mime_parents(self.metadata['mime_type'])
        return self.metadata['mime_type'] in ['text/plain', 'text/csv'] or \
            'text/plain' in mime_parents

    def __image_cb(self, button, floating=False):
        try:
            chooser = ObjectChooser(self, what_filter='Image',
                                    filter_type=FILTER_TYPE_GENERIC_MIME,
                                    show_preview=True)
        except:
            # for compatibility with older versions
            chooser = ObjectChooser(self, what_filter='Image')

        try:
            result = chooser.run()
            if result == Gtk.ResponseType.ACCEPT:
                logging.debug('ObjectChooser: %r',
                              chooser.get_selected_object())
                jobject = chooser.get_selected_object()
                if jobject and jobject.file_path:
                    self.abiword_canvas.insert_image(jobject.file_path,
                                                     floating)
        finally:
            chooser.destroy()
            del chooser
