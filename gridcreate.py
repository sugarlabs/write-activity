#!/usr/bin/python

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject


class GridCreateWidget(Gtk.DrawingArea):

    __gsignals__ = {
        'create-table': (
            GObject.SignalFlags.RUN_FIRST, None, [int, int]), }

    def __init__(self):
        super(GridCreateWidget, self).__init__()
        self._cell_width = 75  # will be style.GRID_CELL_SIZE
        self._cell_height = int(self._cell_width / 2)
        self._rows = 0
        self._columns = 0
        self._min_rows = 3
        self._min_columns = 3

        self._update_size()
        self.connect('draw', self.__draw_cb)
        self.set_events(Gdk.EventMask.TOUCH_MASK)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.add_events(Gdk.EventMask.BUTTON_MOTION_MASK)
        self.connect('event', self.__event_cb)

    def __event_cb(self, widget, event):
        if event.type in (
                Gdk.EventType.TOUCH_BEGIN,
                Gdk.EventType.TOUCH_CANCEL, Gdk.EventType.TOUCH_END,
                Gdk.EventType.TOUCH_UPDATE, Gdk.EventType.BUTTON_PRESS,
                Gdk.EventType.BUTTON_RELEASE, Gdk.EventType.MOTION_NOTIFY):
            x = event.get_coords()[1]
            y = event.get_coords()[2]

            if event.type in (
                    Gdk.EventType.TOUCH_BEGIN,
                    Gdk.EventType.TOUCH_UPDATE, Gdk.EventType.BUTTON_PRESS,
                    Gdk.EventType.MOTION_NOTIFY):
                # update rows and cols
                columns = int(x / self._cell_width) + 1
                rows = int(y / self._cell_height) + 1
                if self._columns != columns or self._rows != rows:
                    self._columns = columns
                    self._rows = rows
                    self._update_size()

            elif event.type in (Gdk.EventType.TOUCH_END,
                                Gdk.EventType.BUTTON_RELEASE):
                self.emit('create-table', self._rows, self._columns)

    def _update_size(self):
        self._min_col = max(self._columns + 1, self._min_columns)
        self._width = self._min_col * self._cell_width
        self._min_rows = max(self._rows + 1, self._min_rows)
        self._height = self._min_rows * self._cell_height
        self.set_size_request(self._width, self._height)
        self.queue_draw()

    def __draw_cb(self, widget, cr):
        # background
        cr.set_source_rgb(0.0, 0.0, 0.0)
        cr.rectangle(0, 0, self._width, self._height)
        cr.fill()
        # used area
        cr.set_source_rgb(0.9, 0.9, 0.9)
        width = self._columns * self._cell_width
        height = self._rows * self._cell_height
        cr.rectangle(0, 0, width, height)
        cr.fill()
        # draw grid
        cr.set_source_rgb(1.0, 1.0, 1.0)
        self._draw_grid(cr, self._min_rows, self._min_col, self._width,
                        self._height)
        cr.set_source_rgb(0.0, 0.0, 0.0)
        self._draw_grid(cr, self._rows, self._columns, width, height)

    def _draw_grid(self, cr, rows, cols, width, height):
        for n in range(rows + 1):
            cr.move_to(0, n * self._cell_height)
            cr.line_to(width, n * self._cell_height)
        for n in range(cols + 1):
            cr.move_to(n * self._cell_width, 0)
            cr.line_to(n * self._cell_width, height)
        cr.stroke()


class GridCreateTest(Gtk.Window):

    def __init__(self):
        super(GridCreateTest, self).__init__()
        self.connect("destroy", Gtk.main_quit)
        grid_create = GridCreateWidget()
        grid_create.connect('create-table', self.__create_table)
        self.add(grid_create)
        self.show_all()

    def __create_table(self, grid_creator, rows, columns):
        print 'rows %d columns %d' % (rows, columns)

if __name__ == '__main__':
    GridCreateTest()
    Gtk.main()
