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

from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.combobox import ComboBox
from sugar.graphics.palette import Palette
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.menuitem import MenuItem
from sugar.datastore import datastore

logger = logging.getLogger('write-activity')

class FontCombo(ComboBox):
    def __init__(self, abi):
        ComboBox.__init__(self)

        self._has_custom_fonts = False
        self._fonts = sorted(abi.get_font_names())
        self._fonts_changed_id = self.connect('changed', self._font_changed_cb,
                abi)

        for i, f in enumerate(self._fonts):
            self.append_item(i, f, None)
            if f == 'Times New Roman':
                self.set_active(i)

        self._abi_handler = abi.connect('font-family', self._font_family_cb)

    def _font_changed_cb(self, combobox, abi):
        if self.get_active() != -1:
            logger.debug('Setting font: %s', self._fonts[self.get_active()])
            try:
                abi.handler_block(self._abi_handler)
                abi.set_font_name(self._fonts[self.get_active()])
            finally:
                abi.handler_unblock(self._abi_handler)

    def _font_family_cb(self, abi, font_family):
        font_index = -1

        # search for the font name in our font list
        for i, f in enumerate(self._fonts):
            if f == font_family:
                font_index = i
                break

        # if we don't know this font yet, then add it (temporary) to the list
        if font_index == -1:
            logger.debug('Font not found in font list: %s', font_family)
            if not self._has_custom_fonts:
                # add a separator to seperate the non-available fonts from
                # the available ones
                self._fonts.append('') # ugly
                self.append_separator()
                self._has_custom_fonts = True
            # add the new font
            self._fonts.append(font_family)
            self.append_item(0, font_family, None)
            # see how many fonts we have now, so we can select the last one
            model = self.get_model()
            num_children = model.iter_n_children(None)
            logger.debug('Number of fonts in the list: %d', num_children)
            font_index = num_children-1

        # activate the found font
        if (font_index > -1):
            self.handler_block(self._fonts_changed_id)
            self.set_active(font_index)
            self.handler_unblock(self._fonts_changed_id)

class FontSizeCombo(ComboBox):
    def __init__(self, abi):
        ComboBox.__init__(self)

        self._abi_handler = abi.connect('font-size', self._font_size_cb)

        self._font_sizes = ['8', '9', '10', '11', '12', '14', '16', '20', \
                            '22', '24', '26', '28', '36', '48', '72']
        self._changed_id = self.connect('changed', self._font_size_changed_cb,
                abi)

        for i, s in enumerate(self._font_sizes):
            self.append_item(i, s, None)
            if s == '12':
                self.set_active(i)

    def _font_size_changed_cb(self, combobox, abi):
        if self.get_active() != -1:
            logger.debug('Setting font size: %d',
                    int(self._font_sizes[self.get_active()]))

            abi.handler_block(self._abi_handler)
            try:
                abi.set_font_size(self._font_sizes[self.get_active()])
            finally:
                abi.handler_unblock(self._abi_handler)

    def _font_size_cb(self, abi, size):
        for i, s in enumerate(self._font_sizes):
            if int(s) == int(size):
                self.handler_block(self._changed_id)
                self.set_active(i)
                self.handler_unblock(self._changed_id)
                break

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

class ExportButton(ToolButton):
    _EXPORT_FORMATS = [{'mime_type' : 'application/rtf',
                        'title'     : _('Rich Text (RTF)'),
                        'jpostfix'  : _('RTF'),
                        'exp_props' : ''},

                       {'mime_type' : 'text/html',
                        'title'     : _('Hypertext (HTML)'),
                        'jpostfix'  : _('HTML'),
                        'exp_props' : 'html4:yes; declare-xml:no; ' \
                                      'embed-css:yes; embed-images:yes;'},

                       {'mime_type' : 'text/plain',
                        'title'     : _('Plain Text (TXT)'),
                        'jpostfix'  : _('TXT'),
                        'exp_props' : ''}]

    def __init__(self, activity, abi):
        ToolButton.__init__(self, 'document-save')
        self.props.tooltip = _('Export')
        self.props.label = _('Export')

        for i in self._EXPORT_FORMATS:
            menu_item = MenuItem(i['title'])
            menu_item.connect('activate', self.__activate_cb, activity, abi, i)
            self.props.palette.menu.append(menu_item)
            menu_item.show()

    def do_clicked(self):
        if self.props.palette.is_up():
            self.props.palette.popdown(immediate=True)
        else:
            self.props.palette.popup(immediate=True, state=Palette.SECONDARY)

    def __activate_cb(self, menu_item, activity, abi, format):
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
        fileObject.metadata['title_set_by_user'] = act_meta['title_set_by_user']
        fileObject.metadata['mime_type'] = format['mime_type']
        fileObject.metadata['fulltext'] = abi.get_content(
                extension_or_mimetype=".txt")[:3000]

        fileObject.metadata['icon-color'] = act_meta['icon-color']
        fileObject.metadata['activity'] = act_meta['activity']
        fileObject.metadata['keep'] = act_meta['keep']

        preview = activity.get_preview()
        if preview is not None:
            fileObject.metadata['preview'] = dbus.ByteArray(preview)

        fileObject.metadata['share-scope'] = act_meta['share-scope']

        # write out the document contents in the requested format
        fileObject.file_path = os.path.join(activity.get_activity_root(),
                'instance', '%i' % time.time())
        abi.save('file://' + fileObject.file_path,
                format['mime_type'], exp_props)

        # store the journal item
        datastore.write(fileObject, transfer_ownership=True)
        fileObject.destroy()
        del fileObject
