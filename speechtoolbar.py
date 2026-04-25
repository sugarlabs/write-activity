# Copyright (C) 2006, Red Hat, Inc.
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
from gi.repository import Gtk

logger = logging.getLogger('write-activity')


class SpeechToolbar(Gtk.Box):

    def __init__(self, activity):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self._activity = activity

        label = Gtk.Label(label=_("Speech not available in GTK4 build"))
        label.set_margin_start(10)
        self.append(label)
