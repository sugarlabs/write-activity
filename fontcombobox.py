# Copyright (C) 2012 Gonzalo Odiard <gonzalo@laptop.org>
# Based in code form Flavio Danesse <fdanesse@activitycentral.com>
# and Ariel Calzada <ariel.calzada@gmail.com>
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
import gtk

FONT_BLACKLIST = ['cmex10', 'cmmi10', 'cmr10', 'cmsy10', 'esint10', 'eufm10',
            'msam10', 'msbm10', 'rsfs10', 'wasy10']


class FontComboBox(gtk.ComboBox):

    def __init__(self):
        gtk.ComboBox.__init__(self)
        font_renderer = gtk.CellRendererText()
        self.pack_start(font_renderer)
        self.add_attribute(font_renderer, 'text', 0)
        self.add_attribute(font_renderer, 'font', 0)
        font_model = gtk.ListStore(str)

        context = self.get_pango_context()
        font_index = 0
        self.faces = {}

        for family in context.list_families():
            name = family.get_name()
            if name not in FONT_BLACKLIST:
                font_model.append([name])
                font_faces = []
                for face in family.list_faces():
                    face_name = face.get_face_name()
                    font_faces.append(face_name)
                self.faces[name] = font_faces

        sorter = gtk.TreeModelSort(font_model)
        sorter.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.set_model(sorter)
        self.show()

    def set_font_name(self, font_name):
        count = 0
        tree_iter = self.get_model().get_iter_first()
        while tree_iter is not None:
            value = self.get_model().get_value(tree_iter, 0)
            if value == font_name:
                self.set_active(count)
            count = count + 1
            tree_iter = self.get_model().iter_next(tree_iter)

    def get_font_name(self):
        tree_iter = self.get_active_iter()
        return self.get_model().get_value(tree_iter, 0)
