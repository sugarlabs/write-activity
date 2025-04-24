from gi.repository import Gtk, GLib, Pango
from sugar3.graphics.toolbutton import ToolButton
import asyncio
import threading
from queue import Queue, Empty
import logging
from llm import LLMManager
from llm.config import LLMConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
CHAT_DIALOG_WIDTH = 500
CHAT_DIALOG_HEIGHT = 400
UI_UPDATE_INTERVAL_MS = 500

# Chat colors
STATUS_COLORS = {
    "you": "#3498db",
    "ai": "#2ecc71", 
    "error": "#e74c3c"
}

class AIAssistanceToolbar:
    def __init__(self, abiword_canvas):
        self.abiword_canvas = abiword_canvas
        self.llm_manager = None
        self.text_queue = Queue()
        self.current_response = []
        self.stop_requested = False
        self.is_model_loaded = False
        self.chat_dialog = None
        self.chat_view = None
        self.user_entry = None
        self.chat_history = []
        self.thinking_indicator = None
        self.thinking_dots = 0
        self.thinking_timer = None
        self.thinking_animation = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.animation_index = 0

    def create_button(self):
        button = ToolButton('bulb')
        button.set_tooltip('AI Assistant')
        button.connect('clicked', self.show_ai_feedback)
        return button

    def create_chat_dialog(self):
        dialog = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        dialog.set_title("AI Assistant")
        dialog.set_default_size(CHAT_DIALOG_WIDTH, CHAT_DIALOG_HEIGHT)
        dialog.set_position(Gtk.WindowPosition.CENTER)
        dialog.connect("delete-event", lambda w,e: w.hide() or True)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        main_box.set_border_width(8)

        chat_view = self._setup_chat_view()
        scrolled_window = self._create_scrolled_window(chat_view)
        input_area = self._create_input_area(chat_view)

        main_box.pack_start(scrolled_window, True, True, 0)
        main_box.pack_start(input_area, False, False, 0)

        dialog.add(main_box)
        self.chat_dialog = dialog
        self.chat_view = chat_view
        self.add_to_chat("AI", "Hello! I'm your AI assistant. How can I help you today?")

        return dialog

    def _setup_chat_view(self):
        chat_view = Gtk.TextView()
        chat_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        chat_view.set_editable(False)
        chat_view.set_cursor_visible(False)
        chat_view.set_margin_start(8)
        chat_view.set_margin_end(8)

        buffer = chat_view.get_buffer()
        for role, color in STATUS_COLORS.items():
            buffer.create_tag(role, weight=Pango.Weight.BOLD, foreground=color)

        return chat_view

    def _create_scrolled_window(self, chat_view):
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(chat_view)
        scrolled.set_vexpand(True)
        return scrolled

    def _create_input_area(self, chat_view):
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        self.user_entry = Gtk.Entry()
        self.user_entry.set_placeholder_text("Type your message...")
        self.user_entry.connect('activate', self.on_entry_activate, chat_view)

        send_button = Gtk.Button(label="Send")
        send_button.connect('clicked', lambda b: self.on_entry_activate(self.user_entry, chat_view))

        clear_button = Gtk.Button(label="Clear Chat")
        clear_button.connect('clicked', lambda b: self.clear_chat(chat_view))

        input_box.pack_start(self.user_entry, True, True, 0)
        input_box.pack_start(send_button, False, False, 0)
        input_box.pack_start(clear_button, False, False, 0)

        return input_box

    def add_to_chat(self, sender, message):
        buffer = self.chat_view.get_buffer()
        end = buffer.get_end_iter()

        if buffer.get_char_count() > 0:
            buffer.insert(end, "\n")

        sender_key = sender.lower()
        tag = buffer.get_tag_table().lookup(sender_key)
        if tag is None:
            tag = buffer.create_tag(sender_key, weight=Pango.Weight.BOLD, 
                                  foreground=STATUS_COLORS.get(sender_key, STATUS_COLORS["you"]))
            
        buffer.insert_with_tags(end, f"{sender}: ", tag)
        buffer.insert(end, message)
        GLib.idle_add(self.scroll_to_bottom)

    def scroll_to_bottom(self):
        adj = self.chat_view.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())
        return False

    def clear_chat(self, chat_view):
        chat_view.get_buffer().set_text("")
        self.add_to_chat("AI", "Chat cleared. How can I help you?")

    def update_thinking_indicator(self):
        if not hasattr(self, '_thinking_mark'):
            buffer = self.chat_view.get_buffer()
            end = buffer.get_end_iter()
            buffer.insert(end, "\n")
            self._thinking_start = buffer.create_mark("thinking_start", buffer.get_end_iter(), True)
            self.animation_index = (self.animation_index + 1) % len(self.thinking_animation)
            spinner = self.thinking_animation[self.animation_index]
            buffer.insert(buffer.get_end_iter(), f"AI: Thinking {spinner}")
            self._thinking_mark = buffer.create_mark("thinking", buffer.get_end_iter(), False)
        else:
            buffer = self.chat_view.get_buffer()
            start = buffer.get_iter_at_mark(self._thinking_start)
            end = buffer.get_iter_at_mark(self._thinking_mark)
            self.animation_index = (self.animation_index + 1) % len(self.thinking_animation)
            spinner = self.thinking_animation[self.animation_index]
            buffer.delete(start, end)
            buffer.insert(start, f"AI: Thinking {spinner}")
        return True

    def clear_thinking_indicator(self):
        if hasattr(self, '_thinking_mark'):
            buffer = self.chat_view.get_buffer()
            start = buffer.get_iter_at_mark(self._thinking_start)
            end = buffer.get_iter_at_mark(self._thinking_mark)
            buffer.delete(start, end)
            buffer.delete_mark(self._thinking_start)
            buffer.delete_mark(self._thinking_mark)
            delattr(self, '_thinking_mark')
            delattr(self, '_thinking_start')

    async def run_llm(self, text):
        try:
            if not self.is_model_loaded:
                self.llm_manager = LLMManager()
                init_successful = self.llm_manager.initialize()
                if not init_successful:
                    self.text_queue.put("Sorry, I couldn't initialize the AI model.")
                    return
                self.is_model_loaded = True

            response = await self.llm_manager.get_feedback_as_list(text)
            if response:
                self.text_queue.put(''.join(response))
            else:
                self.text_queue.put("I couldn't generate a response. Please try again.")

        except Exception as e:
            logger.error(f"Error in run_llm: {e}")
            

    def run_llm_thread(self, text):
        self.stop_requested = True
        if hasattr(self, 'llm_thread') and self.llm_thread and self.llm_thread.is_alive():
            self.llm_thread.join(timeout=0.1)
        self.stop_requested = False

        def thread_func():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.run_llm(text))
            loop.close()

        self.llm_thread = threading.Thread(target=thread_func, daemon=True)
        self.llm_thread.start()
        GLib.timeout_add(UI_UPDATE_INTERVAL_MS, self.process_queue)

    def process_queue(self):
        if self.stop_requested:
            return False

        try:
            text = self.text_queue.get_nowait()
            if self.thinking_timer:
                GLib.source_remove(self.thinking_timer)
                self.thinking_timer = None
                self.clear_thinking_indicator()
            self.add_to_chat("AI", text)
            self.text_queue.task_done()
        except Empty:
            pass
        except Exception as e:
            logger.error(f"Error in process_queue: {e}")
            self.add_to_chat("Error", str(e))

        return True

    def process_user_input(self, text):
        if not text.strip():
            return
            
        self.add_to_chat("You", text)
        self.thinking_timer = GLib.timeout_add(100, self.update_thinking_indicator)
        self.run_llm_thread(text)

    def on_entry_activate(self, entry, chat_view):
        text = entry.get_text()
        entry.set_text("")
        self.process_user_input(text)

    def show_ai_feedback(self, button):
        if self.chat_dialog is None:
            self.create_chat_dialog()
        self.chat_dialog.show_all()
        self.user_entry.grab_focus()
