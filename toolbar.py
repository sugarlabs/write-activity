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
from sugar.activity.widgets import *
from sugar.graphics.palette import Palette
from sugar import mime
from port import chooser
import sugar.profile

import widgets

logger = logging.getLogger('write-activity')

class EditToolbar(gtk.Toolbar):
    def __init__(self, pc):
    
        gtk.Toolbar.__init__(self)

        copy = CopyButton()
        copy.props.accelerator = '<Ctrl>C'
        copy.connect('clicked', lambda button: pc.abiword_canvas.copy())
        self.insert(copy, -1)
        copy.show()

        paste = PasteButton()
        paste.props.accelerator = '<Ctrl>V'
        paste.connect('clicked', lambda button: pc.abiword_canvas.paste())
        self.insert(paste, -1)
        paste.show()

        separator = gtk.SeparatorToolItem()
        self.insert(separator, -1)
        separator.show()

        undo = UndoButton(sensitive=False)
        undo.connect('clicked', lambda button: pc.abiword_canvas.undo())
        pc.abiword_canvas.connect("can-undo", lambda abi, can_undo:
                undo.set_sensitive(can_undo))
        self.insert(undo, -1)
        undo.show()

        redo = RedoButton(sensitive=False)
        redo.connect('clicked', lambda button: pc.abiword_canvas.redo())
        pc.abiword_canvas.connect("can-redo", lambda abi, can_redo:
                redo.set_sensitive(can_redo))
        self.insert(redo, -1)
        redo.show()

        pc.abiword_canvas.connect('text-selected', lambda abi, b:
                copy.set_sensitive(True))
        pc.abiword_canvas.connect('image-selected', lambda abi, b:
                copy.set_sensitive(True))
        pc.abiword_canvas.connect('selection-cleared', lambda abi, b:
                copy.set_sensitive(False))


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

        font_name = ToolComboBox(widgets.FontCombo(abiword_canvas))
        self.insert(font_name, -1)

        font_size = ToolComboBox(widgets.FontSizeCombo(abiword_canvas))
        self.insert(font_size, -1)

        # MAGIC NUMBER WARNING: Secondary toolbars are not a standard height?
        self.set_size_request(-1, 75)

        self.show_all()

class ParagraphToolbar(gtk.Toolbar):
    def __init__(self, abi):
        gtk.Toolbar.__init__(self)

        self.insert(ToolComboBox(widgets.StyleCombo(abi)), -1)
        self.insert(gtk.SeparatorToolItem(), -1)

        group = widgets.AbiButton(abi, 'left-align', abi.align_left)
        group.props.named_icon = 'format-justify-left'
        group.props.tooltip = _('Left justify')
        self.insert(group, -1)

        button = widgets.AbiButton(abi, 'center-align', abi.align_center)
        button.props.group = group
        button.props.named_icon = 'format-justify-center'
        button.props.tooltip = _('Center justify')
        self.insert(button, -1)

        button = widgets.AbiButton(abi, 'right-align', abi.align_right)
        button.props.group = group
        button.props.named_icon = 'format-justify-right'
        button.props.tooltip = _('Right justify')
        self.insert(button, -1)

        button = widgets.AbiButton(abi, 'justify-align', abi.align_justify)
        button.props.group = group
        button.props.named_icon = 'format-justify-fill'
        button.props.tooltip = _('Fill justify')
        self.insert(button, -1)

        self.insert(gtk.SeparatorToolItem(), -1)
        lists = RadioMenuButton(palette=widgets.ListsPalette(abi))
        self.insert(lists, -1)

        self.show_all()
