from gettext import gettext as _
from gi.repository import Gtk, Gdk, GObject
from sugar3.graphics.icon import Icon
from sugar3.graphics.toolbutton import ToolButton
import os
from sugar3.graphics import style
from conversation_manager import ConversationContext
from sugarai_api import load_story_prompt

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
    def __init__(self, activity, initial_messages=None):
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
        header.pack_start(create_btn, True, False, 0)
        self.chat_view_box.pack_start(header, False, True, 10)

        # Chat messages area
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.messages_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scroll.add(self.messages_box)
        self.chat_view_box.pack_start(scroll, True, True, 0)

        # Input area
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text(_('My story is about...'))
        self.entry.connect('activate', self._send_message)

        send_btn = Gtk.Button(label=_('Send'))
        send_btn.connect('clicked', self._send_message)

        input_box.pack_start(self.entry, True, True, 5)
        input_box.pack_start(send_btn, False, True, 5)

        self.chat_view_box.pack_end(input_box, False, True, 10)
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
        advice_icon = Gtk.Image.new_from_icon_name('advice', Gtk.IconSize.LARGE_TOOLBAR)
        advice_icon.set_pixel_size(40)
        self.advice_toggle_btn.set_image(advice_icon)
        self.advice_toggle_btn.set_always_show_image(True)
        self.advice_toggle_btn.set_tooltip_text(_('Advice'))
        self.advice_toggle_btn.connect('clicked', self._toggle_advice_section)
        framework_buttons_box.pack_start(self.advice_toggle_btn, False, False, 0)

        # Add a back button for the framework view
        framework_back_btn = Gtk.Button()
        chat_icon = Gtk.Image.new_from_icon_name('chat', Gtk.IconSize.LARGE_TOOLBAR)
        chat_icon.set_pixel_size(40)
        framework_back_btn.set_image(chat_icon)
        framework_back_btn.set_always_show_image(True)
        framework_back_btn.set_tooltip_text(_('Back to Chat'))
        framework_back_btn.connect('clicked', self._show_chat)
        framework_buttons_box.pack_start(framework_back_btn, False, False, 0)

        self.framework_view_box.pack_start(framework_buttons_box, False, False, 0)

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
        advice_header_box.pack_start(advice_header_label, True, True, 0)
        # Add a separator at the top of the advice section
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(5)
        separator.set_margin_bottom(5)
        self.advice_section_box.pack_start(separator, False, False, 0)

        self.advice_section_box.pack_start(advice_header_box, False, False, 0)

        self.advice_label = Gtk.Label(label='')
        self.advice_label.set_line_wrap(True)
        self.advice_label.set_max_width_chars(50)
        self.advice_label.set_justify(Gtk.Justification.LEFT)

        advice_scroll = Gtk.ScrolledWindow()
        advice_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        advice_scroll.set_min_content_height(150)
        advice_scroll.add(self.advice_label)
        self.advice_section_box.pack_start(advice_scroll, False, False, 0)

        # Scrolled window for framework content
        self.framework_scroll = Gtk.ScrolledWindow()
        self.framework_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.framework_content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10) # This will hold the actual framework pairs
        self.framework_scroll.add(self.framework_content_box)
        self.framework_scroll.set_vexpand(True)
        self.framework_view_box.pack_start(self.framework_scroll, True, True, 0)

        self.framework_view_box.pack_start(self.advice_section_box, False, False, 0)
        self.advice_section_box.set_vexpand(False)

        self.generate_advice_btn = Gtk.Button(label=_('Generate Advice'))
        self.generate_advice_btn.connect('clicked', self._generate_and_display_advice)
        self.advice_section_box.pack_end(self.generate_advice_btn, False, False, 0)

        # Add framework view to the stack
        self.main_stack.add_titled(self.framework_view_box, "framework_view", "Framework")

        # Pack the stack into the ChatSidebar
        self.pack_start(self.main_stack, True, True, 0)

        # Ensure advice section is hidden by default after all packing
        self.advice_section_box.hide()

    def _toggle_advice_section(self, widget):
        if self.advice_section_box.get_visible():
            self.advice_section_box.hide()
        else:
            self.advice_section_box.show()

    def _generate_and_display_advice(self, widget):
        self.advice_label.set_text("Generating advice...")
        advice = self.activity.get_canvas_content_for_advice()
        self.advice_label.set_text(advice)

    def set_advice_text(self, advice_text):
        self.advice_label.set_text(advice_text)

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
        self.context.update_story_info()
        self._update_framework_display() # Call a new method to update content
        self.main_stack.set_visible_child_name("framework_view") # Switch to framework view
        self.advice_section_box.hide() # Ensure advice section is hidden by default when framework is created

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

    def _update_framework_display(self):
        # Clear existing framework content
        for child in self.framework_content_box.get_children():
            self.framework_content_box.remove(child)

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
            self.framework_content_box.pack_start(pair_box, False, False, 10)

        # Add a separator after keys with values
        if keys_with_values and keys_without_values:
            separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            separator.set_margin_top(10)
            separator.set_margin_bottom(10)
            self.framework_content_box.pack_start(separator, False, False, 0)

        # Then display keys without values
        for key, value in keys_without_values:
            pair_box = self._create_framework_pair(key, value)
            self.framework_content_box.pack_start(pair_box, False, False, 10)
        self.framework_content_box.show_all()

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
            self.hide()
        else:
            self.show()