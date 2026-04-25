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

from gettext import gettext as _
import logging
logger = logging.getLogger('write-activity')
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GObject, GLib
from sugar4.graphics.icon import Icon
from sugar4.graphics.toolbutton import ToolButton
import os
from sugar4.graphics import style
from conversation_manager import ConversationContext
from sugarai_api import load_story_prompt, get_llm_response

class ChatMessage(Gtk.Box):
    def __init__(self, message, is_bot=True):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_margin_top(5)
        self.set_margin_bottom(5)
        self.set_margin_start(10)
        self.set_margin_end(10)

        msg_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        msg_label = Gtk.Label(label=message)
        msg_label.set_wrap(True)
        msg_label.set_hexpand(True)
        msg_label.set_justify(Gtk.Justification.LEFT)
        
        if is_bot:
            msg_box.get_style_context().add_class('bot-message')
            msg_box.set_halign(Gtk.Align.START)
            self.append(msg_box)
        else:
            msg_box.get_style_context().add_class('user-message')
            msg_box.set_halign(Gtk.Align.END)
            self.append(msg_box)
            self.set_halign(Gtk.Align.END) # user message container aligns to end
            
        msg_box.append(msg_label)

class ChatSidebar(Gtk.Box):
    def _apply_css(self):
        css_file = os.path.join(os.path.dirname(__file__), 'chat.css')

        if not os.path.exists(css_file):
            logger.warning("CSS file not found")
            return

        try:
            with open(css_file, "r", encoding="utf-8") as f:
                css_data = f.read()

            provider = Gtk.CssProvider()
            provider.load_from_data(css_data.encode("utf-8"))

            display = Gdk.Display.get_default()
            if display:
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )

        except Exception as e:
            logger.error(f"CSS load failed: {e}")

    def __init__(self, activity, initial_messages=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._apply_css()
        self.activity = activity

        self.context = ConversationContext()
        if initial_messages:
            self.context.messages = initial_messages

        self.system_prompt = load_story_prompt()

        self.default_meanings = {
            'title': _('The name of your story.'),
            'setting': _('Where and when your story happens.'),
            'main_character': _('The most important person or animal in your story.'),
            'side_character': _('A friend or helper character in your story.'),
            'goal': _('What the main character wants to do or get.'),
            'conflict': _('The big problem or challenge in the story.'),
            'climax': _('The most exciting part of the story, where things change!'),
            'helpers': _('Good guys who help the main character.'),
            'villains': _('Bad guys who try to stop the main character.'),
            'ending': _('How the story finishes.'),
            'theme': _('The main idea or lesson of the story.')
        }

        # Create a Gtk.Stack to manage different views (chat, framework)
        self.main_stack = Gtk.Stack()
        self.main_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.main_stack.set_transition_duration(300)

        # --- Chat View Setup ---
        self.chat_view_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header with Create Framework button
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        create_btn = Gtk.Button(label=_('Create framework'))
        create_btn.get_style_context().add_class('create-framework-button')
        create_btn.connect('clicked', self._create_framework)
        header.append(create_btn)
        create_btn.set_hexpand(True)
        self.chat_view_box.append(header)
        header.set_margin_top(10)
        header.set_margin_bottom(10)

        # Chat messages area
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.messages_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scroll.set_child(self.messages_box)
        self.chat_view_box.append(scroll)
        scroll.set_vexpand(True)

        # Input area
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text(_('My story is about...'))
        self.entry.connect('activate', self._send_message)

        send_btn = Gtk.Button(label=_('Send'))
        send_btn.connect('clicked', self._send_message)

        input_box.append(self.entry)
        self.entry.set_hexpand(True)
        self.entry.set_margin_start(5)
        self.entry.set_margin_end(5)
        input_box.append(send_btn)
        send_btn.set_margin_end(5)

        self.chat_view_box.append(input_box)
        input_box.set_margin_bottom(10)
        # Show initial bot message
        self._show_initial_messages()

        # Add chat view to the stack
        self.main_stack.add_titled(self.chat_view_box, "chat_view", "Chat")

        # --- Framework View Setup (initialized once) ---
        self.framework_view_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.framework_view_box.set_margin_top(20)
        self.framework_view_box.set_margin_bottom(20)
        self.framework_view_box.set_margin_start(20)
        self.framework_view_box.set_margin_end(20)
        
        # Buttons for framework view
        framework_buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        # Add advice button next to 'Back to chat'
        self.advice_toggle_btn = Gtk.Button()
        advice_icon = Icon(icon_name='advice', pixel_size=style.zoom(40))
        self.advice_toggle_btn.set_child(advice_icon)
        self.advice_toggle_btn.set_tooltip_text(_('Advice'))
        self.advice_toggle_btn.connect('clicked', self._toggle_advice_section)
        framework_buttons_box.append(self.advice_toggle_btn)

        # Add a back button for the framework view
        framework_back_btn = Gtk.Button()
        chat_icon = Icon(icon_name='chat', pixel_size=style.zoom(40))
        framework_back_btn.set_child(chat_icon)
        framework_back_btn.set_tooltip_text(_('Back to Chat'))
        framework_back_btn.connect('clicked', self._show_chat)
        framework_buttons_box.append(framework_back_btn)

        self.framework_view_box.append(framework_buttons_box)

        # Advice section setup
        self.advice_section_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.advice_section_box.set_margin_top(2)
        self.advice_section_box.set_margin_bottom(2)
        self.advice_section_box.set_margin_start(20)
        self.advice_section_box.set_margin_end(20)

        # Add "Mary Tales suggests" header
        advice_header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        advice_header_label = Gtk.Label(label=_('Mary Tales suggests'))
        advice_header_label.get_style_context().add_class('advice-header')
        advice_header_box.append(advice_header_label)
        advice_header_label.set_hexpand(True)
        # Add a separator at the top of the advice section
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(5)
        separator.set_margin_bottom(5)
        self.advice_section_box.append(separator)

        self.advice_section_box.append(advice_header_box)

        self.advice_label = Gtk.Label(label='')
        self.advice_label.set_wrap(True)
        self.advice_label.set_max_width_chars(50)
        self.advice_label.set_justify(Gtk.Justification.LEFT)

        advice_scroll = Gtk.ScrolledWindow()
        advice_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        advice_scroll.set_min_content_height(150)
        advice_scroll.set_child(self.advice_label)
        self.advice_section_box.append(advice_scroll)

        # Scrolled window for framework content
        self.framework_scroll = Gtk.ScrolledWindow()
        self.framework_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.framework_content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10) # This will hold the actual framework pairs
        self.framework_scroll.set_child(self.framework_content_box)
        self.framework_scroll.set_vexpand(True)
        self.framework_view_box.append(self.framework_scroll)

        self.framework_view_box.append(self.advice_section_box)
        self.advice_section_box.set_vexpand(False)

        self.generate_advice_btn = Gtk.Button(label=_('Generate Advice'))
        self.generate_advice_btn.connect('clicked', self._generate_and_display_advice)
        self.advice_section_box.append(self.generate_advice_btn)

        # Add framework view to the stack
        self.main_stack.add_titled(self.framework_view_box, "framework_view", "Framework")

        # Pack the stack into the ChatSidebar
        self.append(self.main_stack)
        self.main_stack.set_vexpand(True)

        # Ensure advice section is hidden by default after all packing
        self.advice_section_box.set_visible(False)

    def _toggle_advice_section(self, widget):
        if self.advice_section_box.get_visible():
            self.advice_section_box.set_visible(False)
        else:
            self.advice_section_box.set_visible(True)

    def _generate_and_display_advice(self, widget):
        self.advice_label.set_text("Generating...")

        content = self.activity.get_canvas_content_for_advice()

        messages = [{"role": "user", "content": content}]

        response = get_llm_response(messages)

        self.advice_label.set_text(response)

    def set_advice_text(self, advice_text):
        self.advice_label.set_text(advice_text)

    def _show_initial_messages(self):
        for msg in self.context.messages:
            self.add_message(msg["content"], msg["role"] == "assistant")

    def _send_message(self, widget):
        message = self.entry.get_text()

        if not message:
            return

        self.context.add_user_message(message)
        self.add_message(message, False)
        self.entry.set_text('')

        # async call
        GLib.idle_add(self._handle_llm_response)

    def _handle_llm_response(self):
        try:
            response = self.context.get_llm_response(
                self.context.get_latest_context(),
                self.system_prompt
            )
        except Exception as e:
            logger.error(f"LLM error: {e}")
            response = "Error getting response"

        self.context.add_bot_message(response)
        self.add_message(response, True)
        return False

    def add_message(self, message, is_bot=True):
        msg = ChatMessage(message, is_bot)
        self.messages_box.append(msg)
        # Auto-scroll to new message safely
        parent = self.messages_box.get_ancestor(Gtk.ScrolledWindow)
        if parent:
            adj = parent.get_vadjustment()
            if adj:
                GLib.idle_add(self._scroll_to_bottom, adj)

    def _scroll_to_bottom(self, adj):
        adj.set_value(adj.get_upper() - adj.get_page_size())
        return False

    def _create_framework(self, widget):
        self.context.update_story_info()
        self._update_framework_display() # Call a new method to update content
        self.main_stack.set_visible_child_name("framework_view") # Switch to framework view
        self.advice_section_box.set_visible(False) # Ensure advice section is hidden by default when framework is created

    def _create_framework_pair(self, key, value):
        pair_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        key_label = Gtk.Label(label=key.capitalize()+':')
        key_label.set_halign(Gtk.Align.START)
        key_label.get_style_context().add_class('framework-key')
        value_frame = Gtk.Frame()
        value_frame.get_style_context().add_class('framework-value-frame')
        value_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        if value:
            value_label = Gtk.Label(label=value)
            value_label.get_style_context().add_class('framework-value-label')
        else:
            value_label = Gtk.Label(label=self.default_meanings.get(key))
            value_label.get_style_context().add_class('framework-default-value-label')

        value_label.set_halign(Gtk.Align.CENTER)
        value_label.set_valign(Gtk.Align.CENTER)
        value_box.append(value_label)
        value_label.set_hexpand(True)
        value_label.set_margin_top(10)
        value_label.set_margin_bottom(10)
        value_frame.set_child(value_box)
        pair_box.append(key_label)
        pair_box.append(value_frame)
        return pair_box

    def _update_framework_display(self):
        # Clear existing framework content
        child = self.framework_content_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.framework_content_box.remove(child)
            child = next_child

        # Separate keys with values from keys without values
        keys_with_values = []
        keys_without_values = []
        for key, value in self.context.story_info.items():
            if value:
                keys_with_values.append((key, value))
            else:
                keys_without_values.append((key, value))

        # Display keys with values first
        for key, value in keys_with_values:
            pair_box = self._create_framework_pair(key, value)
            self.framework_content_box.append(pair_box)
            pair_box.set_margin_bottom(10)

        # Add a separator after keys with values
        if keys_with_values and keys_without_values:
            separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            separator.set_margin_top(10)
            separator.set_margin_bottom(10)
            self.framework_content_box.append(separator)

        # Then display keys without values
        for key, value in keys_without_values:
            pair_box = self._create_framework_pair(key, value)
            self.framework_content_box.append(pair_box)
            pair_box.set_margin_bottom(10)

    def _show_framework(self, widget=None):
        # This method is now primarily for the 'Back' button in the header
        # It will update the framework content and then switch to it.
        self._update_framework_display()
        self.main_stack.set_visible_child_name("framework_view")

    def _show_chat(self, widget=None):
        # Switch to chat view
        self.main_stack.set_visible_child_name("chat_view")

    def toggle_visibility(self):
        if self.get_visible():
            self.set_visible(False)
        else:
            self.set_visible(True)

