"""GUI Module for bushfire drone simulation."""

import tkinter as tk

from PIL import ImageTk

from bushfire_drone_simulation.aircraft import UAV, WaterBomber
from bushfire_drone_simulation.fire_utils import Location, WaterTank
from bushfire_drone_simulation.gui.map_image import MapImage
from bushfire_drone_simulation.lightning import Lightning


def create_point_from_elm(
    canvas_name, element: Location, list_name, rad=5
):  # center coordinates, radius
    """Create a point given an element extending Location."""
    x, y = element.to_coordinates()
    point = canvas_name.create_oval(
        x - rad, y - rad, x + rad, y + rad, fill=type_to_colour(element)
    )
    list_name.append(point)


def connect_points(canvas_name, p_1: Location, p_2: Location):
    """Connect two points with a line."""
    canvas_name.create_line(
        p_1.to_coordinates(), p_2.to_coordinates(), fill=type_to_colour(p_1), width=2
    )


def type_to_colour(element: Location):
    """Assign an element a colour based on its type."""
    if isinstance(element, WaterTank):
        return "blue"
    if isinstance(element, Lightning):
        if element.ignition:
            return "red"
        return "yellow"
    if isinstance(element, WaterBomber):
        return "green"
    if isinstance(element, UAV):
        return "brown"
    return "black"


def delete(canvas_name, points_list):
    """Delete list of points from canvas_name."""
    for point in points_list:
        canvas_name.delete(point)


def update(var_whaaaaaaaaaaaaaaat, canvas_name, water_bomber_base_points):
    """Update whether a set of points is displayed on the canvas."""
    if var_whaaaaaaaaaaaaaaat.get() == 1:
        delete(canvas_name, water_bomber_base_points)
    else:
        print("hi")


def start_gui(simulator):  # pylint: disable = too-many-locals
    """Start a basic GUI version of the drone simulation."""
    window = tk.Tk()

    window.title("ANU Bushfire Initiative Drone Simulation")
    canvas = tk.Canvas(window, width=800, height=800)

    lightning_points = []
    for strike in simulator.lightning_strikes:
        create_point_from_elm(canvas, strike, lightning_points)
    tank_points = []
    for tank in simulator.water_tanks:
        create_point_from_elm(canvas, tank, tank_points)
    uav_points = []
    for uav in simulator.uavs:
        for (idx, past_loc) in enumerate(uav.past_locations):
            if idx != 0:
                connect_points(canvas, past_loc, uav.past_locations[idx - 1])
        create_point_from_elm(canvas, uav, uav_points, rad=3)
    uav_base_points = []
    for base in simulator.uav_bases:
        create_point_from_elm(canvas, base, uav_base_points, rad=2)
    water_bomber_base_points = []
    water_bomber_points = []
    for water_bomber_type in simulator.water_bomber_bases_dict:
        for base in simulator.water_bomber_bases_dict[water_bomber_type]:
            create_point_from_elm(canvas, base, water_bomber_base_points, rad=2)
    for water_bomber in simulator.water_bombers:
        for (idx, past_loc) in enumerate(water_bomber.past_locations):
            if idx != 0:
                connect_points(canvas, past_loc, water_bomber.past_locations[idx - 1])
            create_point_from_elm(canvas, water_bomber, water_bomber_points, rad=3)

    # delete(canvas, water_bomber_base_points)
    int_var = tk.IntVar()
    c_1 = tk.Checkbutton(window, text="Remove UAV Bases", variable=int_var, onvalue=1, offvalue=0)
    canvas.create_window(10, 10, anchor="nw", window=c_1)

    button = tk.Button(
        canvas,
        text="Update",
        fg="red",
        command=lambda: update(int_var, canvas, water_bomber_base_points),
    )
    canvas.create_window(10, 50, anchor="nw", window=button)

    canvas.pack()

    title = tk.Label(window, text="ANU Bushfire Initiative Drone Simulation")
    title.pack()

    window.mainloop()


WIDTH = 800
HEIGHT = 600
ZOOM = 15
LATITUDE = 37.79
LONGITUDE = -79.44


class MapUI(tk.Tk):
    """Tkinter GUI for displaying a movable map."""

    def __init__(self):
        """__init__."""
        tk.Tk.__init__(self)
        self.title("ANU Bushfire Initiative Drone Simulation")
        self.canvas = tk.Canvas(self, width=WIDTH, height=HEIGHT)
        self.canvas.pack()
        # self.bind("<Key>", self.check_quit)
        self.bind("<B1-Motion>", self.drag)
        self.bind("<Button-1>", self.click)
        # self.bind("<MouseWheel>", self.mouse_wheel) # Windows
        # self.bind("<Button-4>", self.mouse_wheel) # Linux
        # self.bind("<Button-5>", self.mouse_wheel) # Linux

        self.label = tk.Label(self.canvas)
        self.zoom = ZOOM
        self.map_image = MapImage((WIDTH, HEIGHT), LATITUDE, LONGITUDE, self.zoom)

        self.zoom_in_button = self.add_zoom_button("+", +1)
        self.zoom_out_button = self.add_zoom_button("-", -1)
        self.restart()

        self.coords = None
        self.image = None
        self.tk_image = None

    # def mouse_wheel(self, event):
    # # respond to Linux or Windows wheel event
    # if event.num == 5 or event.delta == -120:
    # self.zoom -= 1
    # if event.num == 4 or event.delta == 120:
    # self.zoom += 1
    # self.map_image.change_zoom(self.zoom, event.x, event.y)
    # self.redraw()

    def add_zoom_button(self, text: str, change: int):
        """Add zoom button.

        Args:
            text (str): text
            change (int): change
        """
        button = tk.Button(
            self.canvas, text=text, width=1, command=lambda: self.change_zoom(change)
        )
        return button

    def change_zoom(self, change: int):
        """Change map zoom.

        Args:
            change (int): change
        """
        new_zoom = self.zoom + change
        if 0 < new_zoom < 20:
            self.zoom = new_zoom
            self.map_image.change_zoom(self.zoom)
            self.restart()

    def drag(self, event):
        """Process mouse drag.

        Args:
            event: Mouse drag event
        """
        self.map_image.move(self.coords[0] - event.x, self.coords[1] - event.y)
        self.redraw()
        self.coords = event.x, event.y

    def click(self, event):
        """Process click.

        Args:
            event: Click event
        """
        self.coords = event.x, event.y

    def reload(self):
        """Reload."""
        self["cursor"] = ""
        self.redraw()

    def restart(self):
        """Restart."""
        self["cursor"] = "watch"
        self.after(1, self.reload)

    def redraw(self):
        """Redraw display."""
        self.image = self.map_image.get_image()
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.label["image"] = self.tk_image
        self.label.place(x=0, y=0, width=WIDTH, height=HEIGHT)

        x = int(self.canvas["width"]) - 50
        y = int(self.canvas["height"]) - 80

        self.zoom_in_button.place(x=x, y=y)
        self.zoom_out_button.place(x=x, y=y + 30)


def start_map_gui():
    """Start a basic GUI version of the drone simulation."""
    MapUI().mainloop()
