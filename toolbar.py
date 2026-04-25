# Copyright (C) 2006, Martin Sevior
# Copyright (C) 2006-2007, Marc Maurer <uwog@uwog.net>
# Copyright (C) 2007, One Laptop Per Child
# Copyright (C) 2025 MostlyK
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

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GObject

from sugar4.graphics.toolbutton import ToolButton
from sugar4.graphics.toolcombobox import ToolComboBox
from sugar4.graphics.colorbutton import ColorToolButton
from sugar4.graphics.toggletoolbutton import ToggleToolButton
from sugar4.graphics.palettemenu import PaletteMenuBox
from sugar4.graphics.palettemenu import PaletteMenuItem
from sugar4.graphics.palette import Palette
from sugar4.graphics import style
from sugar4.activity.widgets import CopyButton, PasteButton, UndoButton, RedoButton

from fontcombobox import FontComboBox, FontSize
from gridcreate import GridCreateWidget

logger = logging.getLogger('write-activity')


class EditToolbar(Gtk.Box):
    def __init__(self, pc, toolbar_box):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self._document_view = pc.document_view

        copy = CopyButton()
        copy.connect('clicked', lambda button: self._document_view.copy())
        self.append(copy)

        paste = PasteButton()
        paste.connect('clicked', lambda button: self._document_view.paste())
        self.append(paste)

        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.append(separator)

        undo = UndoButton(sensitive=True)
        undo.connect('clicked', lambda button: self._document_view.undo())
        self.append(undo)

        redo = RedoButton(sensitive=True)
        redo.connect('clicked', lambda button: self._document_view.redo())
        self.append(redo)

        separator2 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.append(separator2)

        # Table insertion with Popover
        table_btn = ToolButton(icon_name='insert-table')
        table_btn.set_tooltip(_('Insert Table'))

        def open_grid(widget):
            pop = Gtk.Popover()
            pop.set_parent(widget)

            grid = GridCreateWidget()

            def create_table(_, rows, cols):
                self._document_view.insert_table(rows, cols)
                pop.popdown()

            grid.connect('create-table', create_table)

            pop.set_child(grid)
            pop.popup()

        table_btn.connect("clicked", open_grid)
        self.append(table_btn)

        # Image insertion
        img_btn = ToolButton(icon_name='insert-image')
        img_btn.set_tooltip(_('Insert Image'))

        def pick_image(_):
            dialog = Gtk.FileChooserNative(
                title="Select Image",
                action=Gtk.FileChooserAction.OPEN
            )

            def on_response(d, res):
                if res == Gtk.ResponseType.ACCEPT:
                    file = d.get_file()
                    if file:
                        self._document_view.insert_image(file.get_path())

            dialog.connect("response", on_response)
            dialog.show()

        img_btn.connect("clicked", pick_image)
        self.append(img_btn)

        separator3 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.append(separator3)

        # Search
        self._search_entry = Gtk.Entry()
        self._search_entry.set_placeholder_text(_('Search...'))
        self._search_entry.set_width_chars(20)
        self._search_entry.set_margin_start(10)
        self._search_entry.set_margin_end(10)
        self._search_entry.connect('activate', self._search_activate_cb)
        self.append(self._search_entry)

        find_next = ToolButton(icon_name='go-next')
        find_next.set_tooltip(_('Find next'))
        find_next.connect('clicked', lambda b: self._document_view.find_next())
        self.append(find_next)



    def _search_activate_cb(self, entry):
        text = entry.get_text()
        if text:
            self._document_view.set_find_string(text)
            self._document_view.find_next()


class TextToolbar(Gtk.Box):
    def __init__(self, document_view):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self._document_view = document_view

        self.font_name_combo = FontComboBox()
        self.font_name_combo.connect('font-changed', self._on_font_changed)
        self.append(ToolComboBox(self.font_name_combo))

        self.font_size = FontSize()
        self.font_size.connect('changed', self._on_font_size_changed)
        self.append(self.font_size)

        bold = ToggleToolButton(icon_name='format-text-bold')
        bold.set_tooltip(_('Bold'))
        bold.connect('clicked', lambda sender: self._document_view.toggle_tag("bold"))
        self.append(bold)

        italic = ToggleToolButton(icon_name='format-text-italic')
        italic.set_tooltip(_('Italic'))
        italic.connect('clicked', lambda sender: self._document_view.toggle_tag("italic"))
        self.append(italic)

        underline = ToggleToolButton(icon_name='format-text-underline')
        underline.set_tooltip(_('Underline'))
        underline.connect('clicked', lambda sender: self._document_view.toggle_tag("underline"))
        self.append(underline)

        super_btn = ToggleToolButton(icon_name='format-text-super')
        super_btn.set_tooltip(_('Superscript'))
        super_btn.connect('clicked', lambda sender: self._document_view.toggle_sup())
        self.append(super_btn)

        sub = ToggleToolButton(icon_name='format-text-sub')
        sub.set_tooltip(_('Subscript'))
        sub.connect('clicked', lambda sender: self._document_view.toggle_sub())
        self.append(sub)

        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.append(separator)

        color = ColorToolButton()
        color.set_tooltip_text(_('Text Color'))
        color.connect('notify::color', self._text_color_cb)
        self.append(color)

        separator2 = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.append(separator2)

        # Alignment buttons with Palette
        self._alignment_btn = ToolButton(icon_name='format-justify-left')
        self._alignment_btn.set_tooltip_text(_('Alignment'))
        menu_box = PaletteMenuBox()
        palette = Palette(label=_("Alignment"))
        palette.set_content(menu_box)
        self._alignment_btn.set_palette(palette)

        def add_align(icon, label, callback):
            item = PaletteMenuItem(icon_name=icon, text_label=label)
            item.connect('activate', lambda i: callback())
            menu_box.append_item(item)

        add_align('format-justify-left',   _('Left'),    lambda: self._document_view.set_alignment(Gtk.Justification.LEFT))
        add_align('format-justify-center',  _('Center'),  lambda: self._document_view.set_alignment(Gtk.Justification.CENTER))
        add_align('format-justify-right',   _('Right'),   lambda: self._document_view.set_alignment(Gtk.Justification.RIGHT))
        add_align('format-justify-fill',    _('Fill'),    lambda: self._document_view.set_alignment(Gtk.Justification.FILL))

        self.append(self._alignment_btn)

    def sync_state(self, text_iter):
        tags = [t.get_property("name") for t in text_iter.get_tags()]

        child = self.get_first_child()
        while child:
            if isinstance(child, ToggleToolButton):
                icon = child.get_icon_name()

                if icon == 'format-text-bold':
                    child.set_active("bold" in tags)

                elif icon == 'format-text-italic':
                    child.set_active("italic" in tags)

                elif icon == 'format-text-underline':
                    child.set_active("underline" in tags)

                elif icon == 'format-text-super':
                    child.set_active("superscript" in tags)

                elif icon == 'format-text-sub':
                    child.set_active("subscript" in tags)
            child = child.get_next_sibling()

        if "align_center" in tags:
            self._alignment_btn.set_icon_name('format-justify-center')
        elif "align_right" in tags:
            self._alignment_btn.set_icon_name('format-justify-right')
        elif "align_fill" in tags:
            self._alignment_btn.set_icon_name('format-justify-fill')
        else:
            self._alignment_btn.set_icon_name('format-justify-left')

    def _on_font_changed(self, widget, font_name):
        self._document_view.set_font_name(font_name)

    def _on_font_size_changed(self, widget):
        size = widget.get_font_size()
        self._document_view.set_font_size(size)

    def _text_color_cb(self, button, pspec):
        c = button.get_color()
        self._document_view.set_text_color(
            int(c.red * 255), int(c.green * 255), int(c.blue * 255))


class ParagraphToolbar(Gtk.Box):
    def __init__(self, abi):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        label = Gtk.Label(label=_('Styling'))
        self.append(label)


class ViewToolbar(Gtk.Box):
    def __init__(self, abi):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self._abi = abi

        zoom_in = ToolButton(icon_name='zoom-in')
        zoom_in.set_tooltip(_('Zoom in'))
        zoom_in.connect('clicked', self._zoom_in_cb)
        self.append(zoom_in)

        zoom_out = ToolButton(icon_name='zoom-out')
        zoom_out.set_tooltip(_('Zoom out'))
        zoom_out.connect('clicked', self._zoom_out_cb)
        self.append(zoom_out)

    def _zoom_in_cb(self, button):
        self._abi.set_zoom_percentage(self._abi.get_zoom_percentage() + 10)

    def _zoom_out_cb(self, button):
        self._abi.set_zoom_percentage(self._abi.get_zoom_percentage() - 10)
