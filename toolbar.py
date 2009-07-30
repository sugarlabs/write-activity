# Copyright (C) 2006, Martin Sevior
# Copyright (C) 2006-2007, Marc Maurer <uwog@uwog.net>
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
import dbus

import abiword
import gtk

from sugar.graphics.radiopalette import RadioMenuButton
from sugar.graphics.icon import Icon
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.toggletoolbutton import ToggleToolButton
from sugar.graphics.colorbutton import ColorToolButton
from sugar.graphics.toolcombobox import ToolComboBox
from sugar.graphics.objectchooser import ObjectChooser
from sugar.graphics import iconentry
from sugar.activity import activity
from sugar.graphics.menuitem import MenuItem
from sugar.graphics.palette import Palette
from sugar.datastore import datastore
from sugar import mime
from port import chooser
import sugar.profile

import widgets

logger = logging.getLogger('write-activity')

class WriteActivityToolbarExtension:

    # file mime type, abiword exporter properties, drop down name, journal entry postfix
    _EXPORT_FORMATS = [['application/rtf', _('Rich Text (RTF)'), _('RTF'), ""],
        ['text/html', _('Hypertext (HTML)'), _('HTML'), "html4:yes; declare-xml:no; embed-css:yes; embed-images:yes;"],
        ['text/plain', _('Plain Text (TXT)'), _('TXT'), ""]]

    def __init__(self, activity, toolbox, abiword_canvas):

        self._activity = activity
        self._abiword_canvas = abiword_canvas
        self._activity_toolbar = toolbox.get_activity_toolbar()
        self._keep_palette = self._activity_toolbar.keep.get_palette()

        # hook up the export formats to the Keep button
        for i, f in enumerate(self._EXPORT_FORMATS):
            menu_item = MenuItem(f[1])
            menu_item.connect('activate', self._export_as_cb, f[0], f[2], f[3])
            self._keep_palette.menu.append(menu_item)
            menu_item.show()

    def _export_as_cb(self, menu_item, mimetype, jpostfix, exp_props):
        logger.debug('exporting file, mimetype: %s, exp_props: %s', mimetype, exp_props);

        # special case HTML export to set the activity name as the HTML title
        if mimetype == "text/html":
            exp_props += " title:" + self._activity.metadata['title'] + ';';

        # create a new journal item
        fileObject = datastore.create()
        act_meta = self._activity.metadata
        fileObject.metadata['title'] = act_meta['title'] + ' (' + jpostfix + ')';
        fileObject.metadata['title_set_by_user'] = act_meta['title_set_by_user']
        fileObject.metadata['mime_type'] = mimetype
        fileObject.metadata['fulltext'] = \
            self._abiword_canvas.get_content(extension_or_mimetype=".txt")[:3000]

        fileObject.metadata['icon-color'] = act_meta['icon-color']
        fileObject.metadata['activity'] = act_meta['activity']
        fileObject.metadata['keep'] = act_meta['keep']

# TODO: Activity class should provide support for preview, see #5119
#        self._activity.take_screenshot()
#        if self._activity._preview:
#            preview = self._activity._get_preview()
#            fileObject.metadata['preview'] = dbus.ByteArray(preview)

        fileObject.metadata['share-scope'] = act_meta['share-scope']

        # write out the document contents in the requested format
        fileObject.file_path = os.path.join(self._activity.get_activity_root(), 'instance', '%i' % time.time())
        self._abiword_canvas.save('file://' + fileObject.file_path, mimetype, exp_props)
       
        # store the journal item
        datastore.write(fileObject, transfer_ownership=True)
        fileObject.destroy()
        del fileObject

class SearchToolbar(gtk.Toolbar):

    def __init__(self, abiword_canvas, text_toolbar):

        gtk.Toolbar.__init__(self)

        self._abiword_canvas = abiword_canvas
        self._text_toolbar = text_toolbar

        # setup the search options
        self._search_entry = iconentry.IconEntry()
        self._search_entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                              'system-search')
        self._search_entry.connect('activate', self._search_entry_activated_cb)
        self._search_entry.connect('changed', self._search_entry_changed_cb)
        self._search_entry.add_clear_button();
        self._add_widget(self._search_entry, expand=True)

        self._findprev = ToolButton('go-previous')
        self._findprev.set_tooltip(_('Find previous'))
        self.insert(self._findprev, -1)
        self._findprev.show()
        self._findprev.connect('clicked', self._findprev_cb);

        self._findnext = ToolButton('go-next')
        self._findnext.set_tooltip(_('Find next'))
        self.insert(self._findnext, -1)
        self._findnext.show()
        self._findnext.connect('clicked', self._findnext_cb);

        # set the initial state of the search controls
        # note: we won't simple call self._search_entry_changed_cb
        # here, as that will call into the abiword_canvas, which
        # is not mapped on screen here, causing the set_find_string
        # call to fail
        self._findprev.set_sensitive(False)
        self._findnext.set_sensitive(False)

    def _search_entry_activated_cb(self, entry):
        logger.debug('_search_entry_activated_cb')
        if not self._search_entry.props.text:
            return

        # find the next entry
        self._abiword_canvas.find_next(False)

    def _search_entry_changed_cb(self, entry):
        logger.debug('_search_entry_changed_cb search for \'%s\'',
                self._search_entry.props.text)

        if not self._search_entry.props.text:
            self._search_entry.activate()
            # set the button contexts
            self._findprev.set_sensitive(False)
            self._findnext.set_sensitive(False)
            return

        self._abiword_canvas.set_find_string(self._search_entry.props.text)

        # set the button contexts
        self._findprev.set_sensitive(True)
        self._findnext.set_sensitive(True)

        # immediately start seaching
        self._abiword_canvas.find_next(True)

    def _findprev_cb(self, button):
        logger.debug('_findprev_cb')
        if self._search_entry.props.text:
            self._abiword_canvas.find_prev()
        else:
            logger.debug('nothing to search for!')

    def _findnext_cb(self, button):
        logger.debug('_findnext_cb')
        if self._search_entry.props.text:
            self._abiword_canvas.find_next(False)
        else:
            logger.debug('nothing to search for!')

    # bad foddex! this function was copied from sugar's activity.py
    def _add_widget(self, widget, expand=False):
        tool_item = gtk.ToolItem()
        tool_item.set_expand(expand)

        tool_item.add(widget)
        widget.show()

        self.insert(tool_item, -1)
        tool_item.show()

class InsertToolbar(gtk.Toolbar):
    def __init__(self, abiword_canvas):
        gtk.Toolbar.__init__(self)

        self._abiword_canvas = abiword_canvas

        self._table = abiword.TableCreator()
        self._table.set_labels(_('Table'), _('Cancel'))
        self._table_id = self._table.connect('selected', self._table_cb)
        tool_item = gtk.ToolItem()
        tool_item.add(self._table)
        self.insert(tool_item, -1)
        tool_item.show_all()

        self._table_rows_after = ToolButton('row-insert')
        self._table_rows_after.set_tooltip(_('Insert Row'))
        self._table_rows_after_id = self._table_rows_after.connect('clicked', self._table_rows_after_cb)
        self.insert(self._table_rows_after, -1)

        self._table_delete_rows = ToolButton('row-remove')
        self._table_delete_rows.set_tooltip(_('Delete Row'))
        self._table_delete_rows_id = self._table_delete_rows.connect('clicked', self._table_delete_rows_cb)
        self.insert(self._table_delete_rows, -1)

        self._table_cols_after = ToolButton('column-insert')
        self._table_cols_after.set_tooltip(_('Insert Column'))
        self._table_cols_after_id = self._table_cols_after.connect('clicked', self._table_cols_after_cb)
        self.insert(self._table_cols_after, -1)

        self._table_delete_cols = ToolButton('column-remove')
        self._table_delete_cols.set_tooltip(_('Delete Column'))
        self._table_delete_cols_id = self._table_delete_cols.connect('clicked', self._table_delete_cols_cb)
        self.insert(self._table_delete_cols, -1)

        separator = gtk.SeparatorToolItem()
        self.insert(separator, -1)

        image = ToolButton('insert-image')
        image.set_tooltip(_('Insert Image'))
        self._image_id = image.connect('clicked', self._image_cb)
        self.insert(image, -1)

        self.show_all()

        self._abiword_canvas.connect('table-state', self._isTable_cb)
        #self._abiword_canvas.connect('image-selected', self._image_selected_cb)

    def _image_cb(self, button):
        def cb(object):
            logging.debug('ObjectChooser: %r' % object)
            self._abiword_canvas.insert_image(object.file_path, True)
        chooser.pick(what=chooser.IMAGE, cb=cb)

    def _table_cb(self, abi, rows, cols):
        self._abiword_canvas.insert_table(rows,cols)

    def _table_rows_after_cb(self, button):
        self._abiword_canvas.invoke_cmd('insertRowsAfter', '', 0, 0)

    def _table_delete_rows_cb(self, button):
        self._abiword_canvas.invoke_cmd('deleteRows', '', 0, 0)

    def _table_cols_after_cb(self, button):
        self._abiword_canvas.invoke_cmd('insertColsAfter', '', 0, 0)

    def _table_delete_cols_cb(self, button):
        self._abiword_canvas.invoke_cmd('deleteColumns', '', 0, 0)

    def _isTable_cb(self, abi, b):
        self._table_rows_after.set_sensitive(b)
        self._table_delete_rows.set_sensitive(b)
        self._table_cols_after.set_sensitive(b)
        self._table_delete_cols.set_sensitive(b)

class ViewToolbar(gtk.Toolbar):
    def __init__(self, abiword_canvas):
        gtk.Toolbar.__init__(self)

        self._abiword_canvas = abiword_canvas
        self._zoom_percentage = 0;

        self._zoom_out = ToolButton('zoom-out')
        self._zoom_out.set_tooltip(_('Zoom Out'))
        self._zoom_out_id = self._zoom_out.connect('clicked', self._zoom_out_cb)
        self.insert(self._zoom_out, -1)
        self._zoom_out.show()

        self._zoom_in = ToolButton('zoom-in')
        self._zoom_in.set_tooltip(_('Zoom In'))
        self._zoom_in_id = self._zoom_in.connect('clicked', self._zoom_in_cb)
        self.insert(self._zoom_in, -1)
        self._zoom_in.show()

        # TODO: fix the initial value
        self._zoom_spin_adj = gtk.Adjustment(0, 25, 400, 25, 50, 0)
        self._zoom_spin = gtk.SpinButton(self._zoom_spin_adj, 0, 0)
        self._zoom_spin_id = self._zoom_spin.connect('value-changed', self._zoom_spin_cb)
        self._zoom_spin.set_numeric(True)
        self._zoom_spin.show()
        tool_item_zoom = gtk.ToolItem()
        tool_item_zoom.add(self._zoom_spin)
        self.insert(tool_item_zoom, -1)
        tool_item_zoom.show()

        zoom_perc_label = gtk.Label(_("%"))
        zoom_perc_label.show()
        tool_item_zoom_perc_label = gtk.ToolItem()
        tool_item_zoom_perc_label.add(zoom_perc_label)
        self.insert(tool_item_zoom_perc_label, -1)
        tool_item_zoom_perc_label.show()

        separator = gtk.SeparatorToolItem()
        separator.set_draw(True)
        separator.show()
        self.insert(separator, -1)

        page_label = gtk.Label(_("Page: "))
        page_label.show()
        tool_item_page_label = gtk.ToolItem()
        tool_item_page_label.add(page_label)
        self.insert(tool_item_page_label, -1)
        tool_item_page_label.show()

        self._page_spin_adj = gtk.Adjustment(0, 1, 0, 1, 1, 0)
        self._page_spin = gtk.SpinButton(self._page_spin_adj, 0, 0)
        self._page_spin_id = self._page_spin.connect('value-changed', self._page_spin_cb)
        self._page_spin.set_numeric(True)
        self._page_spin.show()
        tool_item_page = gtk.ToolItem()
        tool_item_page.add(self._page_spin)
        self.insert(tool_item_page, -1)
        tool_item_page.show()

        self._total_page_label = gtk.Label(" / 0")
        self._total_page_label.show()
        tool_item = gtk.ToolItem()
        tool_item.add(self._total_page_label)
        self.insert(tool_item, -1)
        tool_item.show()

        self._abiword_canvas.connect("page-count", self._page_count_cb)
        self._abiword_canvas.connect("current-page", self._current_page_cb)
        self._abiword_canvas.connect("zoom", self._zoom_cb)

    def set_zoom_percentage(self, zoom):
        self._zoom_percentage = zoom
        self._abiword_canvas.set_zoom_percentage(self._zoom_percentage)

    def _zoom_cb(self, canvas, zoom):
        self._zoom_spin.handler_block(self._zoom_spin_id)
        try:
            self._zoom_spin.set_value(zoom)
        finally:
            self._zoom_spin.handler_unblock(self._zoom_spin_id)

    def _zoom_out_cb(self, button):
        if self._zoom_percentage == 0:
            self._zoom_percentage = self._abiword_canvas.get_zoom_percentage()
        if self._zoom_percentage >= 50:
            self.set_zoom_percentage(self._zoom_percentage - 25)

    def _zoom_in_cb(self, button):
        if self._zoom_percentage == 0:
            self._zoom_percentage = self._abiword_canvas.get_zoom_percentage()
        if self._zoom_percentage <= 375:
            self.set_zoom_percentage(self._zoom_percentage + 25)

    def _zoom_spin_cb(self, button):
        self._zoom_percentage = self._zoom_spin.get_value_as_int()
        self._abiword_canvas.set_zoom_percentage(self._zoom_percentage)

    def _page_spin_cb(self, button):
        self._page_num = self._page_spin.get_value_as_int()
        self._abiword_canvas.set_current_page(self._page_num)

    def _page_count_cb(self, canvas, count):
        current_page = canvas.get_current_page_num()
        self._page_spin_adj.set_all(current_page, 1, count, 1, 1, 0)
        self._total_page_label.props.label = \
            ' / ' + str(count)

    def _current_page_cb(self, canvas, num):
        self._page_spin.handler_block(self._page_spin_id)
        try:
            self._page_spin.set_value(num)
        finally:
            self._page_spin.handler_unblock(self._page_spin_id)

class TextToolbar(gtk.Toolbar):
    def __init__(self, abiword_canvas):
        gtk.Toolbar.__init__(self)

        self._abiword_canvas = abiword_canvas

        self.insert(ToolComboBox(widgets.StyleCombo(abiword_canvas)), -1)

        separator = gtk.SeparatorToolItem()
        separator.show()
        self.insert(separator, -1)

        bold = ToggleToolButton('format-text-bold')
        bold.set_tooltip(_('Bold'))
        bold_id = bold.connect('clicked', lambda sender:
                abiword_canvas.toggle_bold())
        self._abiword_canvas.connect('bold', lambda abi, b:
                self.setToggleButtonState(bold, b, bold_id))
        self.insert(bold, -1)

        italic = ToggleToolButton('format-text-italic')
        italic.set_tooltip(_('Italic'))
        italic_id = italic.connect('clicked', lambda sender:
                abiword_canvas.toggle_italic())
        self._abiword_canvas.connect('italic', lambda abi, b:
                self.setToggleButtonState(italic, b, italic_id))
        self.insert(italic, -1)

        underline = ToggleToolButton('format-text-underline')
        underline.set_tooltip(_('Underline'))
        underline_id = underline.connect('clicked', lambda sender:
                abiword_canvas.toggle_underline())
        self._abiword_canvas.connect('underline', lambda abi, b:
                self.setToggleButtonState(underline, b, underline_id))
        self.insert(underline, -1)

        separator = gtk.SeparatorToolItem()
        separator.show()
        self.insert(separator, -1)

        alignment = RadioMenuButton(palette=widgets.Alignment(abiword_canvas))
        self.insert(alignment, -1)

        lists = RadioMenuButton(palette=widgets.Lists(abiword_canvas))
        self.insert(lists, -1)

        separator = gtk.SeparatorToolItem()
        separator.show()
        self.insert(separator, -1)

        color = ColorToolButton()
        color.connect('color-set', self._text_color_cb)
        tool_item = gtk.ToolItem()
        tool_item.add(color)
        self.insert(tool_item, -1)
        self._abiword_canvas.connect('color', lambda abi, r, g, b:
                color.set_color(gtk.gdk.Color(r * 256, g * 256, b * 256)))

        self.show_all()

    def setToggleButtonState(self,button,b,id):
        button.handler_block(id)
        button.set_active(b)
        button.handler_unblock(id)

    def _text_color_cb(self, button):
        newcolor = button.get_color()
        self._abiword_canvas.set_text_color(int(newcolor.red / 256.0), 
                                            int(newcolor.green / 256.0), 
                                            int(newcolor.blue / 256.0))

