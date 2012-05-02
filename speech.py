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

_logger = logging.getLogger('read-etexts-activity')

supported = True

try:
    import gst
    gst.element_factory_make('espeak')
    from speech_gst import *
    _logger.info('use gst-plugins-espeak')
except Exception, e:
    _logger.info('disable gst-plugins-espeak: %s' % e)
    try:
        from speech_dispatcher import *
        _logger.info('use speech-dispatcher')
    except Exception, e:
        supported = False
        _logger.info('disable speech: %s' % e)

voice = 'default'
pitch = 0
rate = 0

highlight_cb = None
end_text_cb = None
reset_cb = None
