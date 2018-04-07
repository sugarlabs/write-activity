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
gi.require_version('TelepathyGLib', '0.12')

from gi.repository import Gtk
from gi.repository import TelepathyGLib

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
            logger.debug('We are joining an activity')
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
            logger.debug("We are creating an activity")

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
        logger.debug('Loading keybindings')
        keybindings_file = os.path.join(get_bundle_path(), 'keybindings.xml')
        self.abiword_canvas.invoke_ex(
            'com.abisource.abiword.loadbindings.fromURI',
            keybindings_file, 0, 0)
        # set default font
        if self._new_instance:
            self.abiword_canvas.select_all()
            logging.debug('Setting default font to %s %d in new documents',
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
        preview_data = ''.join(map(str,preview_data)).encode()

        return preview_data

    def _shared_cb(self, activity):
        logger.debug('My Write activity was shared')
        self._sharing_setup()

        self.shared_activity.connect('buddy-joined', self._buddy_joined_cb)
        self.shared_activity.connect('buddy-left', self._buddy_left_cb)

        channel = self.tubes_chan[TelepathyGLib.IFACE_CHANNEL_TYPE_TUBES]
        logger.debug('This is my activity: offering a tube...')
        id = channel.OfferDBusTube('com.abisource.abiword.abicollab', {})
        logger.debug('Tube address: %s', channel.GetDBusTubeAddress(id))

    def _sharing_setup(self):
        logger.debug("_sharing_setup()")

        if self.shared_activity is None:
            logger.error('Failed to share or join activity')
            return

        self.conn = self.shared_activity.telepathy_conn
        self.tubes_chan = self.shared_activity.telepathy_tubes_chan
        self.text_chan = self.shared_activity.telepathy_text_chan
        self.tube_id = None
        self.tubes_chan[
            TelepathyGLib.IFACE_CHANNEL_TYPE_TUBES].connect_to_signal(
            'NewTube', self._new_tube_cb)

    def _list_tubes_reply_cb(self, tubes):
        for tube_info in tubes:
            self._new_tube_cb(*tube_info)

    def _list_tubes_error_cb(self, e):
        logger.error('ListTubes() failed: %s', e)

    def _joined_cb(self, activity):
        logger.debug("_joined_cb()")
        if not self.shared_activity:
            self._enable_collaboration()
            return

        self.joined = True
        logger.debug('Joined an existing Write session')
        self._sharing_setup()

        logger.debug('This is not my activity: waiting for a tube...')
        self.tubes_chan[TelepathyGLib.IFACE_CHANNEL_TYPE_TUBES].ListTubes(
            reply_handler=self._list_tubes_reply_cb,
            error_handler=self._list_tubes_error_cb)
        self._enable_collaboration()

    def _enable_collaboration(self):
        """
        when communication established, hide the download icon
        and enable the abi widget
        """
        self.abiword_canvas.zoom_width()
        self.abiword_canvas.set_sensitive(True)
        self._connecting_box.hide()

    def _new_tube_cb(self, id, initiator, type, service, params, state):
        logger.debug('New tube: ID=%d initiator=%d type=%d service=%s '
                     'params=%r state=%d', id, initiator, type, service,
                     params, state)

        if self.tube_id is not None:
            # We are already using a tube
            return

        if type != TelepathyGLib.TubeType.DBUS or \
                service != "com.abisource.abiword.abicollab":
            return

        channel = self.tubes_chan[TelepathyGLib.IFACE_CHANNEL_TYPE_TUBES]

        if state == TelepathyGLib.TubeState.LOCAL_PENDING:
            channel.AcceptDBusTube(id)

        # look for the initiator's D-Bus unique name
        initiator_dbus_name = None
        dbus_names = channel.GetDBusNames(id)
        for handle, name in dbus_names:
            if handle == initiator:
                logger.debug('found initiator D-Bus name: %s', name)
                initiator_dbus_name = name
                break

        if initiator_dbus_name is None:
            logger.error('Unable to get the D-Bus name of the tube initiator')
            return

        cmd_prefix = 'com.abisource.abiword.abicollab.olpc.'
        # pass this tube to abicollab
        address = channel.GetDBusTubeAddress(id)
        if self.joined:
            logger.debug('Passing tube address to abicollab (join): %s',
                         address)
            self.abiword_canvas.invoke_ex(cmd_prefix + 'joinTube',
                                          address, 0, 0)
            # The intiator of the session has to be the first passed
            # to the Abicollab backend.
            logger.debug('Adding the initiator to the session: %s',
                         initiator_dbus_name)
            self.abiword_canvas.invoke_ex(cmd_prefix + 'buddyJoined',
                                          initiator_dbus_name, 0, 0)
        else:
            logger.debug('Passing tube address to abicollab (offer): %s',
                         address)
            self.abiword_canvas.invoke_ex(cmd_prefix + 'offerTube', address,
                                          0, 0)
        self.tube_id = id

        channel.connect_to_signal('DBusNamesChanged',
                                  self._on_dbus_names_changed)

        self._on_dbus_names_changed(id, dbus_names, [])

    def _on_dbus_names_changed(self, tube_id, added, removed):
        """
        We call com.abisource.abiword.abicollab.olpc.buddy{Joined,Left}
        according members of the D-Bus tube. That's why we don't add/remove
        buddies in _buddy_{joined,left}_cb.
        """
        logger.debug('_on_dbus_names_changed')
#        if tube_id == self.tube_id:
        cmd_prefix = 'com.abisource.abiword.abicollab.olpc'
        for handle, bus_name in added:
            logger.debug('added handle: %s, with dbus_name: %s',
                         handle, bus_name)
            self.abiword_canvas.invoke_ex(cmd_prefix + '.buddyJoined',
                                          bus_name, 0, 0)
            self.participants[handle] = bus_name

    def _on_members_changed(self, message, added, removed, local_pending,
                            remote_pending, actor, reason):
        logger.debug("_on_members_changed")
        for handle in removed:
            bus_name = self.participants.pop(handle, None)
            if bus_name is None:
                # FIXME: that shouldn't happen so probably hide another bug.
                # Should be investigated
                continue

            cmd_prefix = 'com.abisource.abiword.abicollab.olpc'
            logger.debug('removed handle: %d, with dbus name: %s', handle,
                         bus_name)
            self.abiword_canvas.invoke_ex(cmd_prefix + '.buddyLeft',
                                          bus_name, 0, 0)

    def _buddy_joined_cb(self, activity, buddy):
        logger.debug('buddy joined with object path: %s', buddy.object_path())

    def _buddy_left_cb(self, activity, buddy):
        logger.debug('buddy left with object path: %s', buddy.object_path())

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
            # if the file is new, save in .odt format
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
