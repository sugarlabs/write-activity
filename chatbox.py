from gettext import gettext as _
from gi.repository import Gtk, Gdk, GObject
from sugar3.graphics.icon import Icon
from sugar3.graphics.toolbutton import ToolButton
import os
from sugar3.graphics import style

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
        self.show_all()

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
        
        # Header with Create Framework button
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        create_btn = Gtk.Button(label=_('Create framework'))
        create_btn.get_style_context().add_class('create-framework-button')
        header.pack_start(create_btn, True, False, 0)
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
        self.show_all()
    
    def _send_message(self, widget):
        message = self.entry.get_text()
        if message:
            self.add_message(message, False)
            self.entry.set_text('')
            # Add mock bot response
            self.add_message(_('Bot is going to be live soon'), True)
    
    def add_message(self, message, is_bot=True):
        msg = ChatMessage(message, is_bot)
        self.messages_box.pack_start(msg, False, True, 0)
        msg.show_all()