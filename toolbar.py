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

from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.toggletoolbutton import ToggleToolButton
from sugar.graphics.combobox import ComboBox
from sugar.graphics.toolcombobox import ToolComboBox
from sugar.graphics.objectchooser import ObjectChooser

logger = logging.getLogger('write-activity')

#ick
TOOLBAR_ACTIVITY = 0
TOOLBAR_EDIT = 1
TOOLBAR_TEXT = 2
TOOLBAR_IMAGE = 3
TOOLBAR_TABLE = 4
TOOLBAR_VIEW = 5

class TextToolbar(gtk.Toolbar):
    _ACTION_ALIGNMENT_LEFT = 0
    _ACTION_ALIGNMENT_CENTER = 1
    _ACTION_ALIGNMENT_RIGHT = 2
    _ACTION_ALIGNMENT_JUSTIFY = 3

    def __init__(self, toolbox, abiword_canvas):
        self._colorseldlg = None

        gtk.Toolbar.__init__(self)

        self._toolbox = toolbox
        self._abiword_canvas = abiword_canvas

        self._bold = ToggleToolButton('format-text-bold')
        self._bold_id = self._bold.connect('clicked', self._bold_cb)
        self._abiword_canvas.connect('bold', self._isBold_cb)
        self.insert(self._bold, -1)
        self._bold.show()

        self._italic = ToggleToolButton('format-text-italic')
        self._italic_id = self._italic.connect('clicked', self._italic_cb)
        self._abiword_canvas.connect('italic', self._isItalic_cb)
        self.insert(self._italic, -1)
        self._italic.show()

        self._underline = ToggleToolButton('format-text-underline')
        self._underline_id = self._underline.connect('clicked', self._underline_cb)
        self._abiword_canvas.connect('underline', self._isUnderline_cb)
        self.insert(self._underline, -1)
        self._underline.show()

        self._text_color = gtk.ColorButton()
        self._text_color_id = self._text_color.connect('color-set', self._text_color_cb)
        tool_item = gtk.ToolItem()
        tool_item.add(self._text_color)
        self.insert(tool_item, -1)
        tool_item.show_all()

        separator = gtk.SeparatorToolItem()
        separator.set_draw(True)
        separator.show()
        self.insert(separator, -1)

        self._font_size_combo = ComboBox()
        self._font_sizes = ['8', '9', '10', '11', '12', '14', '16', '20', '22', '24', '26', '28', '36', '48', '72']
        self._font_size_changed_id = self._font_size_combo.connect('changed', self._font_size_changed_cb)
        for i, s in enumerate(self._font_sizes):
            self._font_size_combo.append_item(i, s, None)
            if s == '12':
                self._font_size_combo.set_active(i)
        tool_item = ToolComboBox(self._font_size_combo)
        self.insert(tool_item, -1);
        tool_item.show()

        self._font_combo = ComboBox()
        self._fonts = sorted(self._abiword_canvas.get_font_names())
        self._fonts_changed_id = self._font_combo.connect('changed', self._font_changed_cb)
        for i, f in enumerate(self._fonts):
            self._font_combo.append_item(i, f, None)
            if f == 'Times New Roman':
                self._font_combo.set_active(i)
        tool_item = ToolComboBox(self._font_combo)
        self.insert(tool_item, -1);
        tool_item.show()

        separator = gtk.SeparatorToolItem()
        separator.set_draw(True)
        self.insert(separator, -1)
        separator.show()

        self._alignment = ComboBox()
        self._alignment.append_item(self._ACTION_ALIGNMENT_LEFT, None,
                                    'format-justify-left')
        self._alignment.append_item(self._ACTION_ALIGNMENT_CENTER, None,
                                    'format-justify-center')
        self._alignment.append_item(self._ACTION_ALIGNMENT_RIGHT, None,
                                    'format-justify-right')
        self._alignment.append_item(self._ACTION_ALIGNMENT_JUSTIFY, None,
                                    'format-justify-fill')
        self._alignment_changed_id = \
            self._alignment.connect('changed', self._alignment_changed_cb)
        tool_item = ToolComboBox(self._alignment)
        self.insert(tool_item, -1);
        tool_item.show()

        self._abiword_canvas.connect('color', self._color_cb)
        self._abiword_canvas.connect('font-size', self._font_size_cb)

        self._abiword_canvas.connect('left-align', self._isLeftAlign_cb)
        self._abiword_canvas.connect('center-align', self._isCenterAlign_cb)
        self._abiword_canvas.connect('right-align', self._isRightAlign_cb)
        self._abiword_canvas.connect('justify-align', self._isJustifyAlign_cb)

        self._abiword_canvas.connect('text-selected', self._text_selected_cb)

    def _add_widget(self, widget, expand=False):
        tool_item = gtk.ToolItem()
        tool_item.set_expand(expand)

        tool_item.add(widget)
        widget.show()

        self.insert(tool_item, -1)
        tool_item.show()

    def setToggleButtonState(self,button,b,id):
        button.handler_block(id)
        button.set_active(b)
        button.handler_unblock(id)

    def _bold_cb(self, button):
        self._abiword_canvas.toggle_bold()

    def _isBold_cb(self, abi, b):
        self.setToggleButtonState(self._bold,b,self._bold_id)

    def _italic_cb(self, button):
        self._abiword_canvas.toggle_italic()

    def _isItalic_cb(self, abi, b):
        self.setToggleButtonState(self._italic, b, self._italic_id)

    def _underline_cb(self, button):
        self._abiword_canvas.toggle_underline()

    def _isUnderline_cb(self, abi, b):
        self.setToggleButtonState(self._underline, b, self._underline_id)

    def _color_cb(self, abi, r, g, b):
        self._text_color.set_color(gtk.gdk.Color(r * 256, g * 256, b * 256))

    def _text_color_cb(self, button):
        newcolor = self._text_color.get_color()
        self._abiword_canvas.set_text_color(newcolor.red // 256.0, newcolor.green // 256.0, newcolor.blue // 256.0)

    def _font_size_cb(self, abi, size):
        logger.debug('Font size callback: %d', int(size));
        for i, s in enumerate(self._font_sizes):
            if int(s) == int(size):
                self._font_combo.handler_block(self._font_size_changed_id);
                self._font_size_combo.set_active(i)
                self._font_combo.handler_unblock(self._font_size_changed_id);
                break;

    def _font_size_changed_cb(self, combobox):
        if self._font_size_combo.get_active() != -1:
            logger.debug('Setting font size: %d', int(self._font_sizes[self._font_size_combo.get_active()]))
            self._abiword_canvas.set_font_size(self._font_sizes[self._font_size_combo.get_active()])

    def _font_changed_cb(self, combobox):
        if self._font_combo.get_active() != -1:
            logger.debug('Setting font name: %s', self._fonts[self._font_combo.get_active()])
            self._abiword_canvas.set_font_name(self._fonts[self._font_combo.get_active()])

    def _alignment_changed_cb(self, combobox):
        if self._alignment.get_active() == self._ACTION_ALIGNMENT_LEFT:
            self._abiword_canvas.align_left()
        elif self._alignment.get_active() == self._ACTION_ALIGNMENT_CENTER:
            self._abiword_canvas.align_center()
        elif self._alignment.get_active() == self._ACTION_ALIGNMENT_RIGHT:
            self._abiword_canvas.align_right()
        elif self._alignment.get_active() == self._ACTION_ALIGNMENT_JUSTIFY:
            self._abiword_canvas.align_justify()
        else:
            raise ValueError, 'Unknown option in alignment combobox.'

    def _update_alignment_icon(self, index):
        self._alignment.handler_block(self._alignment_changed_id)
        try:
            self._alignment.set_active(index)
        finally:
            self._alignment.handler_unblock(self._alignment_changed_id)

    def _isLeftAlign_cb(self, abi, b):
        if b:
            self._update_alignment_icon(self._ACTION_ALIGNMENT_LEFT)

    def _isCenterAlign_cb(self, abi, b):
        if b:
            self._update_alignment_icon(self._ACTION_ALIGNMENT_CENTER)

    def _isRightAlign_cb(self, abi, b):
        if b:
            self._update_alignment_icon(self._ACTION_ALIGNMENT_RIGHT)

    def _isJustifyAlign_cb(self, abi, b):
        if b:
            self._update_alignment_icon(self._ACTION_ALIGNMENT_JUSTIFY)

    def _text_selected_cb(self, abi, b):
        if b:
            self._toolbox.set_current_toolbar(TOOLBAR_TEXT)
            self._abiword_canvas.grab_focus() # hack: bad toolbox, bad!

class ImageToolbar(gtk.Toolbar):
    def __init__(self, toolbox, abiword_canvas, parent):
        gtk.Toolbar.__init__(self)

        self._toolbox = toolbox
        self._abiword_canvas = abiword_canvas
        self._parent = parent

        self._image = ToolButton('insert-image')
        self._image_id = self._image.connect('clicked', self._image_cb)
        self.insert(self._image, -1)
        self._image.show()

        self._abiword_canvas.connect('image-selected', self._image_selected_cb)

    def _image_cb(self, button):
        chooser = ObjectChooser(_('Choose image'), self._parent,
                                gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
        try:
            result = chooser.run()
            if result == gtk.RESPONSE_ACCEPT:
                logging.debug('ObjectChooser: %r' % chooser.get_selected_object())
                jobject = chooser.get_selected_object()
                if jobject and jobject.file_path:
                    self._abiword_canvas.insert_image(jobject.file_path, True)
        finally:
            chooser.destroy()
            del chooser
 
    def _image_selected_cb(self, abi, b):
        if b:
            self._toolbox.set_current_toolbar(TOOLBAR_IMAGE)
            self._abiword_canvas.grab_focus() # hack: bad toolbox, bad!

class TableToolbar(gtk.Toolbar):
    def __init__(self, toolbox, abiword_canvas):
        gtk.Toolbar.__init__(self)

        self._toolbox = toolbox
        self._abiword_canvas = abiword_canvas

        self._table = abiword.TableCreator()
        self._table.set_labels(_('Table'), _('Cancel'))
        self._table_id = self._table.connect('selected', self._table_cb)
        self._table.show()
        tool_item = gtk.ToolItem()
        tool_item.add(self._table)
        self.insert(tool_item, -1)
        tool_item.show_all()

        self._table_rows_after = ToolButton('row-insert')
        self._table_rows_after_id = self._table_rows_after.connect('clicked', self._table_rows_after_cb)
        self.insert(self._table_rows_after, -1)
        self._table_rows_after.show()

        self._table_delete_rows = ToolButton('row-remove')
        self._table_delete_rows_id = self._table_delete_rows.connect('clicked', self._table_delete_rows_cb)
        self.insert(self._table_delete_rows, -1)
        self._table_delete_rows.show()

        self._table_cols_after = ToolButton('column-insert')
        self._table_cols_after_id = self._table_cols_after.connect('clicked', self._table_cols_after_cb)
        self.insert(self._table_cols_after, -1)
        self._table_cols_after.show()

        self._table_delete_cols = ToolButton('column-remove')
        self._table_delete_cols_id = self._table_delete_cols.connect('clicked', self._table_delete_cols_cb)
        self.insert(self._table_delete_cols, -1)
        self._table_delete_cols.show()

        self._abiword_canvas.connect('table-state', self._isTable_cb)

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
        if b:
            self._toolbox.set_current_toolbar(TOOLBAR_TABLE)
            self._abiword_canvas.grab_focus() # hack: bad toolbox, bad!

class FormatToolbar(gtk.Toolbar):
    def __init__(self, toolbox, abiword_canvas):
        gtk.Toolbar.__init__(self)

        self._toolbox = toolbox
        self._abiword_canvas = abiword_canvas

        style_label = gtk.Label(_("Style: "))
        style_label.show()
        tool_item_style_label = gtk.ToolItem()
        tool_item_style_label.add(style_label)
        self.insert(tool_item_style_label, -1)
        tool_item_style_label.show()

        self._style_combo = ComboBox()
        self._styles = [['Heading 1',_('Heading 1')], 
            ['Heading 2',_('Heading 2')], 
            ['Heading 3',_('Heading 3')],
            ['Heading 4',_('Heading 4')],
            ['Bullet List',_('Bullet List')],
            ['Dashed List',_('Dashed List')],
            ['Numbered List',_('Numbered List')],
            ['Lower Case List',_('Lower Case List')],
            ['Upper Case List',_('Upper Case List')],
            ['Block Text',_('Block Text')],
            ['Normal',_('Normal')],
            ['Plain Text',_('Plain Text')]]
        self._style_changed_id = self._style_combo.connect('changed', self._style_changed_cb)
        for i, s in enumerate(self._styles):
            self._style_combo.append_item(i, s[1], None)
            if s[0] == 'Normal':
                self._style_combo.set_active(i)
        tool_item = ToolComboBox(self._style_combo)
        self.insert(tool_item, -1);
        tool_item.show()

    def _style_changed_cb(self, combobox):
        if self._style_combo.get_active() != -1:
            logger.debug('Setting style name: %s', self._styles[self._style_combo.get_active()][0])
            self._abiword_canvas.set_style(self._styles[self._style_combo.get_active()][0])

class ViewToolbar(gtk.Toolbar):
    def __init__(self, abiword_canvas):
        gtk.Toolbar.__init__(self)

        self._abiword_canvas = abiword_canvas
        self._zoom_percentage = 0;

        self._zoom_in = ToolButton('zoom-in')
        self._zoom_in_id = self._zoom_in.connect('clicked', self._zoom_in_cb)
        self.insert(self._zoom_in, -1)
        self._zoom_in.show()

        self._zoom_out = ToolButton('zoom-out')
        self._zoom_out_id = self._zoom_out.connect('clicked', self._zoom_out_cb)
        self.insert(self._zoom_out, -1)
        self._zoom_out.show()

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

    def _zoom_in_cb(self, button):
        if self._zoom_percentage == 0:
            self._zoom_percentage = self._abiword_canvas.get_zoom_percentage()
        if self._zoom_percentage <= 375:
            self.set_zoom_percentage(self._zoom_percentage + 25)

    def _zoom_out_cb(self, button):
        if self._zoom_percentage == 0:
            self._zoom_percentage = self._abiword_canvas.get_zoom_percentage()
        if self._zoom_percentage >= 50:
            self.set_zoom_percentage(self._zoom_percentage - 25)

    def _zoom_spin_cb(self, button):
        self._zoom_percentage = self._zoom_spin.get_value_as_int()
        self._abiword_canvas.set_zoom_percentage(self._zoom_percentage)

    def _page_spin_cb(self, button):
        self._page_num = self._page_spin.get_value_as_int()
#        TODO

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

