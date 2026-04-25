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

import logging
from gettext import gettext as _
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GObject, Gdk

from sugar4.activity import activity
from sugar4.activity.widgets import StopButton, ActivityToolbarButton
from sugar4.graphics.toolbarbox import ToolbarButton, ToolbarBox
from sugar4.graphics.toggletoolbutton import ToggleToolButton
from sugar4.graphics.toolbutton import ToolButton

from toolbar import EditToolbar, ViewToolbar, TextToolbar
from widgets import DocumentView
from chatbox import ChatSidebar

logger = logging.getLogger('write-activity')

class AbiWordActivity(activity.Activity):
    def __init__(self, handle):
        super().__init__(handle)
        
        self.document_view = DocumentView()
        
        self.toolbar_box = ToolbarBox()
        self.set_toolbar_box(self.toolbar_box)
        
        # Activity Tab
        self.activity_button = ActivityToolbarButton(self)
        self.toolbar_box.toolbar.append(self.activity_button)
        
        # Edit Tab
        self.edit_toolbar = EditToolbar(self, self.toolbar_box)
        edit_button = ToolbarButton(label=_('Edit'), icon_name='toolbar-edit')
        edit_button.set_page(self.edit_toolbar)
        self.toolbar_box.toolbar.append(edit_button)
        
        # Text Tab
        self.text_toolbar = TextToolbar(self.document_view)
        text_button = ToolbarButton(label=_('Text'), icon_name='format-text')
        text_button.set_page(self.text_toolbar)
        self.toolbar_box.toolbar.append(text_button)

        # View Tab
        view_toolbar = ViewToolbar(self.document_view)
        view_button = ToolbarButton(label=_('View'), icon_name='toolbar-view')
        view_button.set_page(view_toolbar)
        self.toolbar_box.toolbar.append(view_button)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        self.toolbar_box.toolbar.append(spacer)
        
        # Chat Toggle Button
        chat_toggle = ToolButton(icon_name='chat')
        chat_toggle.set_tooltip(_('Toggle Chat'))
        chat_toggle.connect('clicked', self._toggle_chat)
        self.toolbar_box.toolbar.append(chat_toggle)

        # Stop
        stop = StopButton(self)
        self.toolbar_box.toolbar.append(stop)

        # Build Exact Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        content_box.append(self.document_view)
        self.document_view.set_hexpand(True); self.document_view.set_vexpand(True)
        
        self.chat_sidebar = ChatSidebar(self)
        self.chat_sidebar.set_size_request(300, -1)
        self.chat_sidebar.set_visible(False)
        content_box.append(self.chat_sidebar)
        
        main_box.append(content_box)
        self.set_canvas(main_box)
        self.set_visible(True)
        
        # Sync toolbar on cursor move
        self.document_view.buffer.connect("mark-set", self._on_mark_set)

    def _on_mark_set(self, buf, iter, mark):
        if mark.get_name() == "insert":
            it = buf.get_iter_at_mark(mark)
            self._sync_toolbar(it)

    def _sync_toolbar(self, it):
        # FIX: only update UI, not typing engine
        if hasattr(self.text_toolbar, 'sync_state'):
            self.text_toolbar.sync_state(it)

    def _toggle_chat(self, button):
        self.chat_sidebar.set_visible(not self.chat_sidebar.get_visible())

    def get_canvas_content_for_advice(self):
        return self.document_view.get_text()

    def read_file(self, file_path):
        self.document_view.load_file(file_path)

    def write_file(self, file_path):
        self.document_view.save_file(file_path)

if __name__ == "__main__":
    from sugar4.activity.activityhandle import ActivityHandle
    handle = ActivityHandle()
    handle.activity_id = "org.sugarlabs.WriteActivity"
    activity = AbiWordActivity(handle)
    activity.present()
