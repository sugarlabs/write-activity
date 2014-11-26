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

import os
import dbus
import time
from gettext import gettext as _
import logging

from gi.repository import Abi
from gi.repository import GLib

from sugar3.graphics.radiotoolbutton import RadioToolButton
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.datastore import datastore

from sugar3.activity.activity import SCOPE_PRIVATE

logger = logging.getLogger('write-activity')


class AbiButton(RadioToolButton):

    def __init__(self, abi, abi_signal, do_abi_cb, on_abi_cb=None, **kwargs):
        RadioToolButton.__init__(self, **kwargs)

        self._abi_handler = abi.connect(abi_signal, self.__abi_cb,
                                        abi_signal, on_abi_cb)
        self._toggled_handler = self.connect('toggled', self.__toggled_cb,
                                             abi, do_abi_cb)

    def __toggled_cb(self, button, abi, do_abi_cb):
        if not button.props.active:
            return

        abi.handler_block(self._abi_handler)
        try:
            logging.debug('Do abi %s' % do_abi_cb)
            do_abi_cb()
        finally:
            abi.handler_unblock(self._abi_handler)

    def __abi_cb(self, abi, prop, abi_signal, on_abi_cb):
        if (on_abi_cb is None and not prop) or \
                (on_abi_cb is not None and not on_abi_cb(abi, prop)):
            return

        self.handler_block(self._toggled_handler)
        try:
            logging.debug('On abi %s prop=%r' % (abi_signal, prop))
            self.set_active(True)
        finally:
            self.handler_unblock(self._toggled_handler)


class AbiMenuItem(PaletteMenuItem):

    def __init__(self, abi, abi_signal, do_abi_cb, icon_name, label,
                 button, on_abi_cb=None, button_icon_name=None):
        self._icon_name = icon_name
        # _button_icon_name is used only in the first case of
        # the list menu
        self._button_icon_name = button_icon_name
        self._button = button
        PaletteMenuItem.__init__(self, icon_name=icon_name, text_label=label)

        self._abi_handler = abi.connect(abi_signal, self.__abi_cb,
                                        abi_signal, on_abi_cb)
        self.connect('activate', self.__activated_cb, abi, do_abi_cb)

    def __activated_cb(self, button, abi, do_abi_cb):

        if self._button_icon_name is not None:
            if self._button.get_icon_name() == self._button_icon_name:
                return
        else:
            if self._button.get_icon_name() == self._icon_name:
                return

        abi.handler_block(self._abi_handler)
        try:
            logging.debug('Do abi %s' % do_abi_cb)
            do_abi_cb()
            if self._button_icon_name is not None:
                self._button.set_icon_name(self._button_icon_name)
            else:
                self._button.set_icon_name(self._icon_name)
        finally:
            abi.handler_unblock(self._abi_handler)

    def __abi_cb(self, abi, prop, abi_signal, on_abi_cb):
        if (on_abi_cb is None and not prop) or \
                (on_abi_cb is not None and not on_abi_cb(abi, prop)):
            return

        logging.debug('On abi %s prop=%r' % (abi_signal, prop))
        if self._button_icon_name is not None:
            self._button.set_icon_name(self._button_icon_name)
        else:
            self._button.set_icon_name(self._icon_name)


class ExportButtonFactory():

    _EXPORT_FORMATS = [{'mime_type': 'application/rtf',
                        'title': _('Rich Text (RTF)'),
                        'icon': 'save-as-rtf',
                        'jpostfix': _('RTF'),
                        'exp_props': ''},

                       {'mime_type': 'text/html',
                        'title': _('Hypertext (HTML)'),
                        'icon': 'save-as-html',
                        'jpostfix': _('HTML'),
                        'exp_props': 'html4:yes; declare-xml:no; '
                                     'embed-css:yes; embed-images:yes;'},

                       {'mime_type': 'text/plain',
                        'title': _('Plain Text (TXT)'),
                        'icon': 'save-as-txt',
                        'jpostfix': _('TXT'),
                        'exp_props': ''},

                       {'mime_type': 'application/pdf',
                        'title': _('Portable Document Format (PDF)'),
                        'icon': 'save-as-pdf',
                        'jpostfix': _('PDF'),
                        'exp_props': ''}]

    def __init__(self, activity, abi):

        toolbar = activity.activity_button.props.page
        for i in self._EXPORT_FORMATS:
            if abi.get_version() == '3.0' and i['title'].find('PDF') > -1:
                # pdf export crashes on abiword 3.0
                continue
            button = ToolButton(i['icon'])
            button.set_tooltip(i['title'])
            button.connect('clicked', self.__clicked_cb, activity, abi, i)
            toolbar.insert(button, -1)
            button.show()

    def __clicked_cb(self, menu_item, activity, abi, format):
        logger.debug('exporting file: %r' % format)

        exp_props = format['exp_props']

        # special case HTML export to set the activity name as the HTML title
        if format['mime_type'] == "text/html":
            exp_props += " title:" + activity.metadata['title'] + ';'

        # create a new journal item
        fileObject = datastore.create()
        act_meta = activity.metadata
        fileObject.metadata['title'] = \
            act_meta['title'] + ' (' + format['jpostfix'] + ')'
        fileObject.metadata['title_set_by_user'] = \
            act_meta['title_set_by_user']
        fileObject.metadata['mime_type'] = format['mime_type']
        # due to http://bugzilla.abisource.com/show_bug.cgi?id=13585
        if abi.get_version() != '3.0':
            fileObject.metadata['fulltext'] = abi.get_content('text/plain',
                                                              None)[:3000]

        fileObject.metadata['icon-color'] = act_meta['icon-color']

        # don't set application if PDF because Write can't open PDF files
        if format['mime_type'] != 'application/pdf':
            fileObject.metadata['activity'] = act_meta['activity']

        fileObject.metadata['keep'] = act_meta.get('keep', '0')

        preview = activity.get_preview()
        if preview is not None:
            fileObject.metadata['preview'] = dbus.ByteArray(preview)

        fileObject.metadata['share-scope'] = act_meta.get('share-scope',
                                                          SCOPE_PRIVATE)

        # write out the document contents in the requested format
        fileObject.file_path = os.path.join(activity.get_activity_root(),
                                            'instance', '%i' % time.time())
        abi.save('file://' + fileObject.file_path,
                 format['mime_type'], exp_props)

        # store the journal item
        datastore.write(fileObject, transfer_ownership=True)
        fileObject.destroy()
        del fileObject


class DocumentView(Abi.Widget):

    def __init__(self):
        Abi.Widget.__init__(self)
        self.connect('size-allocate', self.__size_allocate_cb)
        try:
            self.connect('request-clear-area', self.__request_clear_area_cb)
        except:
            logging.error('EXCEPTION: request-clear-area signal not available')

        try:
            self.connect('unset-clear-area', self.__unset_clear_area_cb)
        except:
            logging.error('EXCEPTION: unset-clear-area signal not available')

        self.osk_changed = False
        self.dy = 0

    def __shallow_move_cb(self):
        self.moveto_right()
        return False

    def __size_allocate_cb(self, widget, allocation):
        self.set_allocation(allocation)

        if self.get_child() is not None:
            child_allocation = allocation
            child_allocation.y = 0
            child_allocation.x = 0
            child_allocation.height -= self.dy
            self.get_child().size_allocate(allocation)

        if self.osk_changed is True:
            self.moveto_left()
            GLib.timeout_add(100, self.__shallow_move_cb)
            self.osk_changed = False

    def __request_clear_area_cb(self, widget, clear, cursor):
        allocation = widget.get_allocation()
        allocation.x = 0
        allocation.y = 0
        allocation.x, allocation.y = \
            widget.get_window().get_root_coords(allocation.x, allocation.y)

        if clear.y > allocation.y + allocation.height or \
                clear.y + clear.height < allocation.y:
            return False

        self.dy = allocation.y + allocation.height - clear.y

        # Ensure there's at least some room for the view
        if self.dy > allocation.height - 80:
            self.dy = 0
            return False

        self.osk_changed = True
        self.queue_resize()
        return True

    def __unset_clear_area_cb(self, widget, snap_back):
        self.dy = 0
        self.queue_resize()
        return True

    def get_version(self):
        version = Abi._version
        logging.error('Abiword version %s', version)
        return version
