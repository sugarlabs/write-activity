# Copyright (C) 2023
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
import unicodedata

from gi.repository import Gtk
from gi.repository import GObject

# List of Unicode blocks known to cause rendering issues in AbiWord
PROBLEMATIC_UNICODE_BLOCKS = [
    (0x2000, 0x206F),  # General Punctuation
    (0x2200, 0x22FF),  # Mathematical Operators
    (0x25A0, 0x25FF),  # Geometric Shapes
    (0x2600, 0x26FF),  # Miscellaneous Symbols
    (0x2700, 0x27BF),  # Dingbats
    (0x1D400, 0x1D7FF),  # Mathematical Alphanumeric Symbols
]

# Characters that are known to work reliably
SAFE_SPECIAL_CHARS = "αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ€£¥¢©®°±×÷½¼¾"

class SpecialCharactersWidget(Gtk.Grid):
    """A widget displaying a grid of special characters that can be inserted"""

    __gsignals__ = {
        'character-selected': (GObject.SignalFlags.RUN_FIRST, None, ([str])),
    }

    # Define categories with ONLY characters that are guaranteed to render correctly
    CATEGORIES = {
        _('Greek Lowercase'): 'αβγδεζηθικλμνξοπρστυφχψω',
        _('Greek Uppercase'): 'ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ',
        _('Currency'): '€£¥¢',
        _('Math'): '+-±×÷½¼¾',
        _('Symbols'): '©®°',
        _('Accented'): 'áàâäãåæçéèêëíìîïñóòôöõøœúùûüýÿ',
    }

    def __init__(self):
        Gtk.Grid.__init__(self)
        self.set_row_spacing(2)
        self.set_column_spacing(2)
        self.set_border_width(5)
        
        # Set a more appropriate size that fits the content
        self.set_size_request(300, 200)

        # Filter out problematic characters and replace with safer alternatives
        self._filter_problematic_chars()
        
        self._setup_ui()
    
    def _filter_problematic_chars(self):
        """Filter out characters known to cause rendering issues after document reload"""
        safe_categories = {}
        for category, chars in self.CATEGORIES.items():
            safe_chars = []
            for char in chars:
                if char in SAFE_SPECIAL_CHARS or not self._is_problematic(char):
                    safe_chars.append(char)
            safe_categories[category] = ''.join(safe_chars)
        self.CATEGORIES = safe_categories
    
    def _is_problematic(self, char):
        """Check if a character is likely to cause rendering problems"""
        code_point = ord(char)
        for start, end in PROBLEMATIC_UNICODE_BLOCKS:
            if start <= code_point <= end:
                return True
        return False

    def _setup_ui(self):
        # Create a notebook with tabs for character categories
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.attach(self.notebook, 0, 0, 1, 1)

        # Create a tab for each category
        for category, chars in self.CATEGORIES.items():
            page_grid = Gtk.Grid()
            page_grid.set_row_spacing(1)
            page_grid.set_column_spacing(1)
            page_grid.set_border_width(2)
            page_grid.set_margin_start(0)
            page_grid.set_margin_end(0)
            page_grid.set_margin_top(0)
            page_grid.set_margin_bottom(0)

            # Create button for each character
            row, col = 0, 0
            for char in chars:
                button = Gtk.Button(label=char)
                button.set_relief(Gtk.ReliefStyle.NONE)
                # Make buttons smaller and more compact
                button.set_size_request(25, 25)
                button.set_margin_start(0)
                button.set_margin_end(0)
                button.set_margin_top(0)
                button.set_margin_bottom(0)
                
                # Add tooltip with Unicode name if available
                try:
                    name = unicodedata.name(char)
                    button.set_tooltip_text(name)
                except ValueError:
                    pass  # No Unicode name available
                
                button.connect('clicked', self._character_clicked)
                page_grid.attach(button, col, row, 1, 1)
                
                # Arrange in a grid with 10 columns
                col += 1
                if col > 9:
                    col = 0
                    row += 1
            
            # Add the grid to the notebook with category as label
            label = Gtk.Label(label=category)
            self.notebook.append_page(page_grid, label)
        
        # Add a "Recently Used" tab
        self.recent_grid = Gtk.Grid()
        self.recent_grid.set_row_spacing(1)
        self.recent_grid.set_column_spacing(1)
        self.recent_grid.set_border_width(2)
        recent_label = Gtk.Label(label=_("Recently Used"))
        self.notebook.append_page(self.recent_grid, recent_label)
        
        self.recent_chars = []
        
        self.show_all()

    def _character_clicked(self, button):
        """Emit signal when a character button is clicked"""
        char = button.get_label()
        self.emit('character-selected', char)
        
        # Add to recently used
        if char in self.recent_chars:
            self.recent_chars.remove(char)
        self.recent_chars.insert(0, char)
        
        # Limit to 20 recent items
        if len(self.recent_chars) > 20:
            self.recent_chars = self.recent_chars[:20]
            
        # Update the recent grid
        for child in self.recent_grid.get_children():
            self.recent_grid.remove(child)
            
        row, col = 0, 0
        for char in self.recent_chars:
            button = Gtk.Button(label=char)
            button.set_relief(Gtk.ReliefStyle.NONE)
            
            # Keep the same compact button style
            button.set_size_request(25, 25)
            button.set_margin_start(0)
            button.set_margin_end(0)
            button.set_margin_top(0)
            button.set_margin_bottom(0)
            
            # Add tooltip with Unicode name if available
            try:
                name = unicodedata.name(char)
                button.set_tooltip_text(name)
            except ValueError:
                pass  # No Unicode name available
                
            button.connect('clicked', self._character_clicked)
            self.recent_grid.attach(button, col, row, 1, 1)
            
            # Arrange in a grid with 10 columns
            col += 1
            if col > 9:
                col = 0
                row += 1
                
        self.recent_grid.show_all() 