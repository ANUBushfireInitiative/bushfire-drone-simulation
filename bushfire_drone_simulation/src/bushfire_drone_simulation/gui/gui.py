"""GUI Module for bushfire drone simulation."""

import tkinter as tk
from tkinter import Button, Event
from typing import Dict, List, Tuple

from PIL import ImageTk

from bushfire_drone_simulation.aircraft import UAV, WaterBomber
from bushfire_drone_simulation.fire_utils import Location, WaterTank
from bushfire_drone_simulation.gui.map_image import MapImage
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.simulator import Simulator


class GUI:
    """GUI class for bushfire drone simulation."""

    def __init__(self, simulator: Simulator) -> None:
        """Run GUI from simulator."""
        self.window = tk.Tk()
        self.window.title("ANU Bushfire Initiative Drone Simulation")
        self.canvas = tk.Canvas(self.window, width=800, height=800)
        self.simulator = simulator

        self.lightning_points, self.ignition_points = self.create_lightning()
        self.uav_points, self.uav_paths, self.uav_base_points = self.create_uavs()
        self.water_tank_points = self.create_water_tanks()
        (
            self.water_bomber_base_points,
            self.water_bomber_points,
            self.water_bomber_paths,
        ) = self.create_water_bombers()

        checkbox_dict = self.create_checkboxes()

        y = 2
        for key in checkbox_dict:
            checkbox_dict[key][1].select()  # type: ignore
            # self.canvas.create_window(10, 10, anchor="w", window=checkbox_dict[key][1])
            checkbox_dict[key][1].place(x=20, y=y)
            y += 20

        self.update(checkbox_dict)

        update_button = tk.Button(
            self.canvas, text="Update", fg="red", command=lambda: self.update(checkbox_dict)
        )
        # self.canvas.create_window(20, y+20, anchor="w", window=update_button)
        update_button.place(x=20, y=y + 20)

        self.canvas.pack()

        title = tk.Label(self.window, text="ANU Bushfire Initiative Drone Simulation")
        title.pack()

        self.window.mainloop()

    def create_lightning(self) -> Tuple[List[int], List[int]]:
        """Create lists of points of lightning and ignitions and add to canvas."""
        lightning_points: List[int] = []
        ignition_points: List[int] = []
        for strike in self.simulator.lightning_strikes:
            if strike.ignition:
                self.create_point_from_elm(strike, ignition_points)
            else:
                self.create_point_from_elm(strike, lightning_points)
        return lightning_points, ignition_points

    def create_uavs(self) -> Tuple[List[int], List[int], List[int]]:
        """Create lists of uav points, paths and bases and add to canvas."""
        uav_points: List[int] = []
        uav_paths: List[int] = []
        for uav in self.simulator.uavs:
            for idx, past_loc in enumerate(uav.past_locations):
                if idx != 0:
                    self.connect_points(past_loc, uav.past_locations[idx - 1], uav_paths)
            self.create_point_from_elm(uav, uav_points, rad=4)
        uav_base_points: List[int] = []
        for base in self.simulator.uav_bases:
            self.create_point_from_elm(base, uav_base_points, rad=2)
        return uav_points, uav_paths, uav_base_points

    def create_water_bombers(self) -> Tuple[List[int], List[int], List[int]]:
        """Create lists of water bomber points, paths and bases and add to canvas."""
        water_bomber_base_points: List[int] = []
        water_bomber_points: List[int] = []
        water_bomber_paths: List[int] = []
        for water_bomber_type in self.simulator.water_bomber_bases_dict:
            for base in self.simulator.water_bomber_bases_dict[water_bomber_type]:
                self.create_point_from_elm(base, water_bomber_base_points, rad=2)
        for water_bomber in self.simulator.water_bombers:
            for (idx, past_loc) in enumerate(water_bomber.past_locations):
                if idx != 0:
                    self.connect_points(
                        past_loc, water_bomber.past_locations[idx - 1], water_bomber_paths
                    )
                self.create_point_from_elm(water_bomber, water_bomber_points, rad=4)
        return water_bomber_base_points, water_bomber_points, water_bomber_paths

    def create_water_tanks(self) -> List[int]:
        """Create list of water tanks and add to canvas."""
        water_tank_points: List[int] = []
        for tank in self.simulator.water_tanks:
            self.create_point_from_elm(tank, water_tank_points, rad=2)
        return water_tank_points

    def create_checkboxes(self) -> Dict[str, Tuple[tk.IntVar, tk.Checkbutton, List[int]]]:
        """Create check boxes for interating with GUI."""
        return_dict = {}

        toggle_uav_bases = tk.IntVar()
        uav_base_checkbox = tk.Checkbutton(
            self.window, text="Show UAV Bases", variable=toggle_uav_bases, onvalue=1, offvalue=0
        )
        return_dict["uav bases"] = (toggle_uav_bases, uav_base_checkbox, self.uav_base_points)

        toggle_uavs = tk.IntVar()
        uav_checkbox = tk.Checkbutton(
            self.window, text="Show UAVs", variable=toggle_uavs, onvalue=1, offvalue=0
        )
        return_dict["uavs"] = (toggle_uavs, uav_checkbox, self.uav_points)

        toggle_uav_paths = tk.IntVar()
        uav_path_checkbox = tk.Checkbutton(
            self.window, text="Show UAV Paths", variable=toggle_uav_paths, onvalue=1, offvalue=0
        )
        return_dict["uav paths"] = (toggle_uav_paths, uav_path_checkbox, self.uav_paths)

        toggle_water_bombers = tk.IntVar()
        water_bomber_checkbox = tk.Checkbutton(
            self.window,
            text="Show Water Bombers",
            variable=toggle_water_bombers,
            onvalue=1,
            offvalue=0,
        )
        return_dict["wbs"] = (toggle_water_bombers, water_bomber_checkbox, self.water_bomber_points)

        toggle_wb_bases = tk.IntVar()
        wb_base_checkbox = tk.Checkbutton(
            self.window,
            text="Show Water Bomber Bases",
            variable=toggle_wb_bases,
            onvalue=1,
            offvalue=0,
        )
        return_dict["wb bases"] = (toggle_wb_bases, wb_base_checkbox, self.water_bomber_base_points)

        toggle_wb_paths = tk.IntVar()
        wb_path_checkbox = tk.Checkbutton(
            self.window,
            text="Show Water Bomber Paths",
            variable=toggle_wb_paths,
            onvalue=1,
            offvalue=0,
        )
        return_dict["wb paths"] = (toggle_wb_paths, wb_path_checkbox, self.water_bomber_paths)

        toggle_water_tanks = tk.IntVar()
        water_tank_checkbox = tk.Checkbutton(
            self.window, text="Show Water Tanks", variable=toggle_water_tanks, onvalue=1, offvalue=0
        )
        return_dict["water tanks"] = (
            toggle_water_tanks,
            water_tank_checkbox,
            self.water_tank_points,
        )

        toggle_lightning = tk.IntVar()
        lightning_checkbox = tk.Checkbutton(
            self.window, text="Show Lightning", variable=toggle_lightning, onvalue=1, offvalue=0
        )
        return_dict["lightning"] = (toggle_lightning, lightning_checkbox, self.lightning_points)

        toggle_ignitions = tk.IntVar()
        ignition_checkbox = tk.Checkbutton(
            self.window, text="Show Ignitions", variable=toggle_ignitions, onvalue=1, offvalue=0
        )
        return_dict["ignitions"] = (toggle_ignitions, ignition_checkbox, self.ignition_points)

        return return_dict

    def create_point_from_elm(
        self, element: Location, list_name: List[int], rad: int = 5
    ) -> None:  # center coordinates, radius
        """Create a point given an element extending Location."""
        x, y = element.to_coordinates()
        point = self.canvas.create_oval(  # type: ignore
            x - rad, y - rad, x + rad, y + rad, fill=type_to_colour(element)
        )
        list_name.append(point)

    def connect_points(self, p_1: Location, p_2: Location, list_name: List[int]) -> None:
        """Connect two points with a line."""
        line = self.canvas.create_line(  # type: ignore
            p_1.to_coordinates(), p_2.to_coordinates(), fill=type_to_colour(p_1), width=1
        )
        list_name.append(line)

    def hide(self, points_list: List[int]) -> None:
        """Hide list of points from canvas_name."""
        for point in points_list:
            self.canvas.itemconfigure(point, state="hidden")

    def show(self, points_list: List[int]) -> None:
        """Hide list of points from canvas_name."""
        for point in points_list:
            self.canvas.itemconfigure(point, state="normal")

    def update(self, checkbox_dict: Dict[str, Tuple[tk.IntVar, tk.Checkbutton, List[int]]]) -> None:
        """Update whether a set of points is displayed on the canvas."""
        for key in checkbox_dict:
            if checkbox_dict[key][0].get() == 0:  # type: ignore
                self.hide(checkbox_dict[key][2])
            else:
                self.show(checkbox_dict[key][2])


def type_to_colour(element: Location) -> str:
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


def start_gui(simulation: Simulator) -> None:
    """Start GUI of simulation."""
    GUI(simulation)


WIDTH = 800
HEIGHT = 600
ZOOM = 7
LATITUDE = -36.25
LONGITUDE = 147.9


class MapUI(tk.Tk):
    """Tkinter GUI for displaying a movable map."""

    def __init__(self) -> None:
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

        self.coords = (0, 0)
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

    def add_zoom_button(self, text: str, change: int) -> Button:
        """Add zoom button.

        Args:
            text (str): text
            change (int): change
        """
        button = tk.Button(
            self.canvas, text=text, width=1, command=lambda: self.change_zoom(change)
        )
        return button

    def change_zoom(self, change: int) -> None:
        """Change map zoom.

        Args:
            change (int): change
        """
        new_zoom = self.zoom + change
        if 0 < new_zoom < 20:
            self.zoom = new_zoom
            self.map_image.change_zoom(self.zoom)
            self.restart()

    def drag(self, event: Event) -> None:
        """Process mouse drag.

        Args:
            event: Mouse drag event
        """
        self.map_image.move(self.coords[0] - event.x, self.coords[1] - event.y)  # type: ignore
        self.redraw()
        self.coords = event.x, event.y  # type: ignore

    def click(self, event: Event) -> None:
        """Process click.

        Args:
            event: Click event
        """
        self.coords = event.x, event.y  # type: ignore

    def reload(self) -> None:
        """Reload."""
        self["cursor"] = ""
        self.redraw()

    def restart(self) -> None:
        """Restart."""
        self["cursor"] = "watch"
        self.after(1, self.reload)

    def redraw(self) -> None:
        """Redraw display."""
        self.image = self.map_image.get_image()
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.label["image"] = self.tk_image
        self.label.place(x=0, y=0, width=WIDTH, height=HEIGHT)

        x = int(self.canvas["width"]) - 50
        y = int(self.canvas["height"]) - 80

        self.zoom_in_button.place(x=x, y=y)
        self.zoom_out_button.place(x=x, y=y + 30)


def start_map_gui() -> None:
    """Start a basic GUI version of the drone simulation."""
    MapUI().mainloop()
