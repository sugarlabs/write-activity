from gettext import gettext as _
from gi.repository import Gtk, Gdk, GObject
from sugar3.graphics.icon import Icon
from sugar3.graphics.toolbutton import ToolButton
import os
from sugar3.graphics import style
from conversation_manager import ConversationContext
from groq_api import load_story_prompt

class ChatMessage(Gtk.Box):
    def __init__(self, message, is_bot=True):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)
        self.set_margin_top(5)
        self.set_margin_bottom(5)
        self.set_margin_start(10)
        self.set_margin_end(10)

        msg_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        msg_label = Gtk.Label(label=message)
        msg_label.set_line_wrap(True)
        msg_label.set_max_width_chars(30)
        msg_label.set_justify(Gtk.Justification.LEFT)
        
        if is_bot:
            msg_box.get_style_context().add_class('bot-message')
            self.pack_start(msg_box, True, True, 0)
        else:
            msg_box.get_style_context().add_class('user-message')
            self.pack_end(msg_box, True, True, 0)
            
        msg_box.pack_start(msg_label, True, True, 0)

class ChatSidebar(Gtk.Box):
    def __init__(self):
        # Load CSS
        css_provider = Gtk.CssProvider()
        css_file = os.path.join(os.path.dirname(__file__), 'chat.css')
        css_provider.load_from_path(css_file)
        display = Gdk.Display.get_default()
        screen = display.get_default_screen()
        Gtk.StyleContext.add_provider_for_screen(
            screen,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)

        self.context = ConversationContext()
        self.system_prompt = load_story_prompt()

        self.default_meanings = {
            'title': _('A concise and engaging title for the story.'),
            'setting': _('The time and place where the story unfolds.'),
            'main_character': _('The main character of the story.'),
            'side_character': _('A supporting character in the story.'),
            'goal': _('The main objective or desire of the protagonist.'),
            'conflict': _('The central struggle or problem in the story.'),
            'climax': _('The turning point or most intense moment of the story.'),
            'helpers': _('Characters who assist the protagonist.'),
            'villains': _('Characters who oppose the protagonist.'),
            'ending': _('The conclusion or resolution of the story.'),
            'theme': _('The underlying message or central idea of the story.')
        }
        
        # Header with Create Framework button
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        create_btn = Gtk.Button(label=_('Create framework'))
        create_btn.get_style_context().add_class('create-framework-button')
        create_btn.connect('clicked', self._create_framework)
        header.pack_start(create_btn, True, False, 0)
        # Add Back button to the right
        back_btn = Gtk.Button(label=_('Back'))
        back_btn.get_style_context().add_class('back-framework-button')
        back_btn.connect('clicked', self._show_framework)
        header.pack_start(back_btn, False, False, 0)
        self.pack_start(header, False, True, 10)

        # Chat messages area
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.messages_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scroll.add(self.messages_box)
        self.pack_start(scroll, True, True, 0)

        # Input area
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text(_('My story is about...'))
        self.entry.connect('activate', self._send_message)

        send_btn = Gtk.Button(label=_('Send'))
        send_btn.connect('clicked', self._send_message)

        input_box.pack_start(self.entry, True, True, 5)
        input_box.pack_start(send_btn, False, True, 5)

        self.pack_end(input_box, False, True, 10)
        # Show initial bot message
        self._show_initial_messages()

    def _show_initial_messages(self):
        for msg in self.context.messages:
            self.add_message(msg["content"], msg["role"] == "assistant")

    def _send_message(self, widget):
        message = self.entry.get_text()
        if message:
            self.context.add_user_message(message)
            self.add_message(message, False)
            self.entry.set_text('')
            # Get LLM response using the loaded system prompt
            response = self.context.get_llm_response(self.context.get_latest_context(), self.system_prompt)
            self.context.add_bot_message(response)
            self.add_message(response, True)

    def add_message(self, message, is_bot=True):
        msg = ChatMessage(message, is_bot)
        self.messages_box.pack_start(msg, False, True, 0)
        msg.show_all()
        # Auto-scroll to new message
        adj = self.messages_box.get_parent().get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    def _create_framework(self, widget):
        # Remove file writing, instead update story info and show framework in sidebar
        self.context.update_story_info()
        self._show_framework()

    def _create_framework_pair(self, key, value):
        pair_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        key_label = Gtk.Label(label=key.capitalize()+':')
        key_label.set_xalign(0)
        key_label.get_style_context().add_class('framework-key')
        value_frame = Gtk.Frame()
        value_frame.set_shadow_type(Gtk.ShadowType.IN)
        value_frame.get_style_context().add_class('framework-value-frame')
        value_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        if value:
            value_label = Gtk.Label(label=value)
            value_label.get_style_context().add_class('framework-value-label')
        else:
            value_label = Gtk.Label(label=self.default_meanings.get(key))
            value_label.get_style_context().add_class('framework-default-value-label')

        value_label.set_xalign(0.5)
        value_label.set_justify(Gtk.Justification.CENTER)
        value_label.set_halign(Gtk.Align.CENTER)
        value_label.set_valign(Gtk.Align.CENTER)
        value_box.pack_start(value_label, True, True, 10)
        value_frame.add(value_box)
        pair_box.pack_start(key_label, False, False, 0)
        pair_box.pack_start(value_frame, False, False, 0)
        return pair_box

    def _show_framework(self, widget=None):
        # Hide chat area and show framework display
        for child in self.get_children():
            child.hide()
        framework_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        framework_box.set_margin_top(20)
        framework_box.set_margin_bottom(20)
        framework_box.set_margin_start(20)
        framework_box.set_margin_end(20)
        # Add a back button
        back_btn = Gtk.Button(label=_('Back to chat'))
        back_btn.connect('clicked', self._show_chat)
        framework_box.pack_start(back_btn, False, False, 0)
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
            framework_box.pack_start(pair_box, False, False, 10)

        # Add a separator after keys with values
        if keys_with_values and keys_without_values:
            separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            separator.set_margin_top(10)
            separator.set_margin_bottom(10)
            framework_box.pack_start(separator, False, False, 0)

        # Then display keys without values
        for key, value in keys_without_values:
            pair_box = self._create_framework_pair(key, value)
            framework_box.pack_start(pair_box, False, False, 10)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(framework_box)
        self.pack_start(scroll, True, True, 0)
        scroll.show_all()
        self.framework_box = scroll

    def _show_chat(self, widget):
        # Remove framework and show chat area again
        if hasattr(self, 'framework_box'):
            self.framework_box.destroy()
        for child in self.get_children():
            child.show()

    def toggle_visibility(self):
        if self.get_visible():
            self.hide()
        else:
            self.show_all()