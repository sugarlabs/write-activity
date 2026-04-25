# Copyright (C) 2006 by Martin Sevior
# Copyright (C) 2006-2007 Marc Maurer <uwog@uwog.net>
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

import os
import logging
from gettext import gettext as _

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib, GObject, Pango, GdkPixbuf

logger = logging.getLogger('write-activity')

class DocumentView(Gtk.ScrolledWindow):
    """GTK4-native text editor engine with strict GTK4 patterns."""

    def __init__(self):
        super().__init__()
        self.set_hexpand(True)
        self.set_vexpand(True)

        self.textview = Gtk.TextView()
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textview.set_left_margin(24)
        self.textview.set_right_margin(24)
        self.textview.set_top_margin(16)
        self.textview.set_bottom_margin(16)
        self.set_child(self.textview)

        self.buffer = self.textview.get_buffer()
        self._active_tags = set()
        self._is_restoring = False

        # Undo/Redo stacks
        self.undo_stack = [""]
        self.redo_stack = []

        # State
        self._find_text = None
        self._zoom = 100

        self._zoom_provider = Gtk.CssProvider()
        self._create_tags()
        self._connect_signals()

    def _create_tags(self):
        buf = self.buffer
        buf.create_tag("bold", weight=Pango.Weight.BOLD)
        buf.create_tag("italic", style=Pango.Style.ITALIC)
        buf.create_tag("underline", underline=Pango.Underline.SINGLE)
        buf.create_tag("superscript", rise=14000, scale=0.6)
        buf.create_tag("subscript", rise=-14000, scale=0.6)
        
        buf.create_tag("align_left", justification=Gtk.Justification.LEFT)
        buf.create_tag("align_center", justification=Gtk.Justification.CENTER)
        buf.create_tag("align_right", justification=Gtk.Justification.RIGHT)
        buf.create_tag("align_fill", justification=Gtk.Justification.FILL)

    def _connect_signals(self):
        self.buffer.connect("insert-text", self._on_insert_text)
        self.buffer.connect("changed", self._on_buffer_changed)

    def _on_insert_text(self, buf, iter_, text, length):
        offset = iter_.get_offset()
        GLib.idle_add(self._apply_active_tags, offset + length, length)

    def _apply_active_tags(self, offset, length):
        buf = self.buffer
        start = buf.get_iter_at_offset(max(0, offset - length))
        end = buf.get_iter_at_offset(offset)

        for tag_name in list(self._active_tags):
            tag = buf.get_tag_table().lookup(tag_name)
            if tag:
                buf.apply_tag(tag, start, end)
        return False

    def _on_buffer_changed(self, buf):
        if self._is_restoring:
            return

        if not hasattr(self, "_last_save"):
            self._last_save = ""

        text = self.get_text()

        if text != self._last_save and len(text) % 5 == 0:
            self.undo_stack.append(text)
            self._last_save = text

            if len(self.undo_stack) > 50:
                self.undo_stack.pop(0)

            self.redo_stack.clear()

    def get_text(self):
        start, end = self.buffer.get_bounds()
        return self.buffer.get_text(start, end, True)

    # ---- Formatting API ----

    def toggle_tag(self, tag_name):
        buf = self.buffer
        tag = buf.get_tag_table().lookup(tag_name)
        if not tag:
            return

        # selection case

        if buf.get_has_selection():
            start, end = buf.get_selection_bounds()

            has_tag = False
            iter_ = start.copy()
            while iter_.compare(end) < 0:
                if iter_.has_tag(tag):
                    has_tag = True
                    break
                iter_.forward_char()

            if has_tag:
                buf.remove_tag(tag, start, end)
            else:
                buf.apply_tag(tag, start, end)

        else:
            # cursor mode (future typing)
            if tag_name in self._active_tags:
                self._active_tags.remove(tag_name)
            else:
                self._active_tags.add(tag_name)

        self.textview.grab_focus()

    def set_dynamic_tag(self, category, value, **props):
        buf = self.buffer
        tag_name = f"{category}{value}"
        tag = buf.get_tag_table().lookup(tag_name) or buf.create_tag(tag_name, **props)

        if buf.get_has_selection():
            start, end = buf.get_selection_bounds()
            tag_table = buf.get_tag_table()
            
            def remove_if_match(tag, data):
                name = tag.get_property("name")
                if name and name.startswith(category):
                    buf.remove_tag(tag, start, end)
            
            tag_table.foreach(remove_if_match, None)
            buf.apply_tag(tag, start, end)
        else:
            self._active_tags = {t for t in self._active_tags if not t.startswith(category)}
            self._active_tags.add(tag_name)
        self.textview.grab_focus()

    def set_alignment(self, justification):
        buf = self.buffer

        if buf.get_has_selection():
            start, end = buf.get_selection_bounds()
        else:
            insert = buf.get_iter_at_mark(buf.get_insert())
            start = insert.copy()
            start.set_line_offset(0)

            end = insert.copy()
            if not end.ends_line():
                end.forward_to_line_end()

        # REMOVE OLD ALIGN TAGS FIRST
        tag_table = buf.get_tag_table()

        def remove_align(tag, data):
            name = tag.get_property("name")
            if name and name.startswith("align_"):
                buf.remove_tag(tag, start, end)

        tag_table.foreach(remove_align, None)

        tag_name = f"align_{justification}"
        tag = tag_table.lookup(tag_name) or buf.create_tag(
            tag_name, justification=justification
        )

        buf.apply_tag(tag, start, end)
        self.textview.grab_focus()

    def get_current_tags(self):
        buf = self.buffer
        iter_ = buf.get_iter_at_mark(buf.get_insert())
        return [t.get_property("name") for t in iter_.get_tags()]

    def insert_table(self, rows=3, cols=3):
        buf = self.buffer
        it = buf.get_iter_at_mark(buf.get_insert())
        anchor = buf.create_child_anchor(it)
        grid = Gtk.Grid()
        grid.set_row_spacing(4); grid.set_column_spacing(4)
        for r in range(rows):
            for c in range(cols):
                entry = Gtk.Entry()
                entry.set_width_chars(8)
                entry.set_hexpand(True)
                grid.attach(entry, c, r, 1, 1)
        self.textview.add_child_at_anchor(grid, anchor)
        grid.show()
        self.textview.show()
        self.textview.grab_focus()
        self.grab_focus()

    # ---- Font System ----

    def set_font_name(self, font_name):
        self.set_dynamic_tag("font_", font_name, font=font_name)

    def set_font_size(self, size):
        self.set_dynamic_tag("size_", size, size=size * Pango.SCALE)

    def set_text_color(self, r, g, b):
        color = f"#{r:02x}{g:02x}{b:02x}"
        self.set_dynamic_tag("color_", color, foreground=color)

    # ---- Sup / Sub ----

    def toggle_sup(self):
        if "subscript" in self._active_tags:
            self._active_tags.remove("subscript")
        self.toggle_tag("superscript")

    def toggle_sub(self):
        if "superscript" in self._active_tags:
            self._active_tags.remove("superscript")
        self.toggle_tag("subscript")

    # ---- Image Insertion ----

    def insert_image(self, path):
        if not os.path.exists(path):
            return
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
        except Exception:
            return
        buf = self.buffer
        iter_ = buf.get_iter_at_mark(buf.get_insert())
        buf.insert_pixbuf(iter_, pixbuf)

    def _insert_image_at_cursor(self, path):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
            # resize
            width = 300
            if pixbuf.get_width() == 0:
                return
            height = int(pixbuf.get_height() * (width / pixbuf.get_width()))
            pixbuf = pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)

            iter_ = self.buffer.get_iter_at_mark(self.buffer.get_insert())
            self.buffer.insert_pixbuf(iter_, pixbuf)
        except Exception as e:
            logger.error(f"Image insert failed: {e}")

    # ---- Search ----

    def set_find_string(self, text):
        self._find_text = text

    def find_next(self):
        if not self._find_text:
            return
        buf = self.buffer
        start = buf.get_iter_at_mark(buf.get_insert())
        match = start.forward_search(self._find_text, 0, None)
        if not match:
            match = buf.get_start_iter().forward_search(self._find_text, 0, None)

        if match:
            mstart, mend = match
            buf.select_range(mstart, mend)
            self.textview.scroll_to_iter(mstart, 0.1, False, 0, 0)

    # ---- Zoom ----

    def set_zoom_percentage(self, value):
        self._zoom = max(50, min(200, value))

        css = f"textview {{ font-size: {self._zoom}%; }}".encode()

        try:
            self._zoom_provider.load_from_data(css)

            display = Gdk.Display.get_default()
            if display:
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    self._zoom_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
        except Exception as e:
            logger.warning(f"Zoom CSS load failed: {e}")

    def get_zoom_percentage(self):
        return self._zoom

    # ---- Undo / Redo ----

    def undo(self):
        if len(self.undo_stack) > 1:
            self._is_restoring = True
            self.redo_stack.append(self.undo_stack.pop())
            self.buffer.set_text(self.undo_stack[-1])
            self._is_restoring = False

    def redo(self):
        if self.redo_stack:
            self._is_restoring = True
            text = self.redo_stack.pop()
            self.undo_stack.append(text)
            self.buffer.set_text(text)
            self._is_restoring = False

    def copy(self):
        display = Gdk.Display.get_default()
        if display: self.buffer.copy_clipboard(display.get_clipboard())
    def paste(self):
        display = Gdk.Display.get_default()
        if display: self.buffer.paste_clipboard(display.get_clipboard(), None, True)

    def save_file(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.get_text())

    def load_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.buffer.set_text(f.read())
        except: pass
