# Copyright (C) 2008, 2009 James D. Simmons
# Copyright (C) 2009 Aleksey S. Lim
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

_logger = logging.getLogger('write-activity')

supported = True

try:
    from gi.repository import Gst
    Gst.init(None)
    Gst.ElementFactory.make('espeak', None)
    from speech_gst import *
    _logger.error('use gst-plugins-espeak')
except Exception as e:
    _logger.error('disable gst-plugins-espeak: %s' % e)
    try:
        from speech_dispatcher import *
        _logger.error('use speech-dispatcher')
    except Exception as e:
        supported = False
        _logger.error('disable speech: %s' % e)

voice = 'default'
pitch = 0
rate = 0

highlight_cb = None
end_text_cb = None
reset_cb = None
