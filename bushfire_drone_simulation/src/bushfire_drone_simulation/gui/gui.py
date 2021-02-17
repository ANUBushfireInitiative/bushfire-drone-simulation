"""GUI Module for bushfire drone simulation."""

import tkinter as tk
from abc import abstractmethod
from tkinter import Button, Canvas, Event
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from PIL import ImageTk

from bushfire_drone_simulation.aircraft import UAV, WaterBomber
from bushfire_drone_simulation.fire_utils import Location, WaterTank
from bushfire_drone_simulation.gui.map_image import MapImage
from bushfire_drone_simulation.lightning import Lightning
from bushfire_drone_simulation.simulator import Simulator

WIDTH = 800
HEIGHT = 600
ZOOM = 7
LATITUDE = -36.25
LONGITUDE = 147.9

EPSILON: float = 0.0000001


class GUIObject:
    """GUIObject.

    This class defines the functions that all GUI objects must implement.
    """

    def get_coordinates(self) -> List[int]:
        """Get the coordinates of the object."""
        if isinstance(self, (GUIPoint, GUILine)):
            return self.get_coordinates()
        raise NotImplementedError

    @abstractmethod
    def show(self, canvas: Canvas) -> None:
        """Show the object."""

    def hide(self, canvas: Canvas) -> None:
        """Hide the object."""

    @abstractmethod
    def update(self, canvas: Canvas, coordinates: Optional[List[int]] = None) -> None:
        """Update the position etc. of the object."""


class GUIPoint(GUIObject):
    """GUI Point.

    This class defines a GUI Point (AKA a circle).
    """

    def __init__(
        self,
        location: Location,
        canvas: Canvas,
        to_coordinates: Callable[[float, float], Tuple[int, int]],
        radius: int = 5,
    ):
        """__init__.

        Args:
            location (Location): location of point (Global coordinates)
            canvas (Canvas): canvas on which point belongs
            to_coordinates (Callable[[float, float], Tuple[int, int]]): Function converting location
                to coordinates on the canvas.
            radius (int): radius of point
        """
        self.radius = radius
        self.to_coordinates = to_coordinates
        self.x, self.y = to_coordinates(location.lat, location.lon)
        self.point = canvas.create_oval(  # type: ignore
            self.x - radius,
            self.y - radius,
            self.x + radius,
            self.y + radius,
            fill=type_to_colour(location),
        )
        self.lat = location.lat
        self.lon = location.lon
        self.cur_shown = True

    def get_coordinates(self) -> List[int]:
        """Get the coordinates of the object."""
        return list(self.to_coordinates(self.lat, self.lon))

    def update(self, canvas: Canvas, coordinates: Optional[List[int]] = None) -> None:
        """Update position of the point."""
        if coordinates is None:
            x, y = self.to_coordinates(self.lat, self.lon)
        else:
            x, y = coordinates[0], coordinates[1]
        canvas.move(self.point, x - self.x, y - self.y)  # type: ignore
        self.x, self.y = x, y

    def hide(self, canvas: Canvas) -> None:
        """Hide point."""
        if self.cur_shown:
            canvas.itemconfigure(self.point, state="hidden")
            self.cur_shown = False

    def show(self, canvas: Canvas) -> None:
        """Show point."""
        if not self.cur_shown:
            canvas.itemconfigure(self.point, state="normal")
            self.cur_shown = True


class GUILine(GUIObject):
    """GUI object representing a line between two global coordinates."""

    def __init__(
        self,
        p_1: Location,
        p_2: Location,
        canvas: Canvas,
        to_coordinates: Callable[[float, float], Tuple[int, int]],
    ):
        """__init__.

        Args:
            p_1 (Location): Global coordinates of start of line.
            p_2 (Location): Global coordinates of end of line.
            canvas (Canvas): canvas on which line belongs
            to_coordinates (Callable[[float, float], Tuple[int, int]]): Function converting global
                coordinates to pixel coordinates.
        """
        self.to_coordinates = to_coordinates
        self.p_1, self.p_2 = p_1, p_2
        c_1 = self.to_coordinates(self.p_1.lat, self.p_1.lon)
        c_2 = self.to_coordinates(self.p_2.lat, self.p_2.lon)
        self.line = canvas.create_line(c_1, c_2, fill=type_to_colour(p_1), width=1)  # type: ignore
        self.cur_shown = True

    def get_coordinates(self) -> List[int]:
        """Get the coordinates of the object."""
        c_1 = self.to_coordinates(self.p_1.lat, self.p_1.lon)
        c_2 = self.to_coordinates(self.p_2.lat, self.p_2.lon)
        return list(c_1 + c_2)

    def update(self, canvas: Canvas, coordinates: Optional[List[int]] = None) -> None:
        """Update position of line."""
        if coordinates is None:
            c_1 = self.to_coordinates(self.p_1.lat, self.p_1.lon)
            c_2 = self.to_coordinates(self.p_2.lat, self.p_2.lon)
            coordinates = list(c_1 + c_2)
        canvas.coords(self.line, coordinates)  # type: ignore

    def hide(self, canvas: Canvas) -> None:
        """Hide line."""
        if self.cur_shown:
            canvas.itemconfigure(self.line, state="hidden")
            self.cur_shown = False

    def show(self, canvas: Canvas) -> None:
        """Show line."""
        if not self.cur_shown:
            canvas.itemconfigure(self.line, state="normal")
            self.cur_shown = True


class GUI:
    """GUI class for bushfire drone simulation."""

    def __init__(self, simulator: Simulator) -> None:
        """Run GUI from simulator."""
        self.window = tk.Tk()
        self.window.title("ANU Bushfire Initiative Drone Simulation")
        title = tk.Label(self.window, text="ANU Bushfire Initiative Drone Simulation")
        title.pack()
        self.canvas = tk.Canvas(self.window, width=WIDTH, height=HEIGHT)
        self.simulator = simulator

        self.window.bind("<B1-Motion>", self.drag)
        self.window.bind("<Button-1>", self.click)

        self.label = tk.Label(self.canvas)
        self.zoom = ZOOM
        self.map_image = MapImage((WIDTH, HEIGHT), LATITUDE, LONGITUDE, self.zoom)

        self.zoom_in_button = self.add_zoom_button("+", +1)
        self.zoom_out_button = self.add_zoom_button("-", -1)

        self.coords = (0, 0)
        self.image = None
        self.tk_image = None

        self.restart()

        self.lightning_points, self.ignition_points = self.create_lightning()
        self.uav_points, self.uav_paths, self.uav_base_points = self.create_uavs()
        self.water_tank_points = self.create_water_tanks()
        (
            self.water_bomber_base_points,
            self.water_bomber_points,
            self.water_bomber_paths,
        ) = self.create_water_bombers()

        self.checkbox_dict = self.create_checkboxes()

        y = 2
        for key in self.checkbox_dict:
            self.checkbox_dict[key][1].select()  # type: ignore
            # self.canvas.create_window(10, 10, anchor="w", window=checkbox_dict[key][1])
            self.checkbox_dict[key][1].place(x=20, y=y)
            y += 20

        self.update_objects()

        self.canvas.pack()
        self.window.mainloop()

    def create_lightning(self) -> Tuple[List[GUIPoint], List[GUIPoint]]:
        """Create lists of points of lightning and ignitions and add to canvas."""
        lightning_points: List[GUIPoint] = []
        ignition_points: List[GUIPoint] = []
        for strike in self.simulator.lightning_strikes:
            if strike.ignition:
                self.create_point_from_elm(strike, ignition_points)
            else:
                self.create_point_from_elm(strike, lightning_points)
        return lightning_points, ignition_points

    def create_uavs(self) -> Tuple[List[GUIPoint], List[GUILine], List[GUIPoint]]:
        """Create lists of uav points, paths and bases and add to canvas."""
        uav_points: List[GUIPoint] = []
        uav_paths: List[GUILine] = []
        for uav in self.simulator.uavs:
            last_point: Location = uav.past_locations[0]
            for idx, point in enumerate(uav.past_locations):
                if idx != 0:
                    if idx == len(uav.past_locations) - 1:
                        self.connect_points(point, last_point, uav_paths)
                    else:
                        dx1 = point.lon - last_point.lon
                        dy1 = point.lat - last_point.lat
                        dx2 = uav.past_locations[idx + 1].lon - point.lon
                        dy2 = uav.past_locations[idx + 1].lat - point.lat
                        if abs(dx2 * dy1 - dx1 * dy2) > EPSILON:
                            self.connect_points(point, last_point, uav_paths)
                            last_point = point

            self.create_point_from_elm(uav, uav_points, rad=4)
        uav_base_points: List[GUIPoint] = []
        for base in self.simulator.uav_bases:
            self.create_point_from_elm(base, uav_base_points, rad=2)
        return uav_points, uav_paths, uav_base_points

    def create_water_bombers(self) -> Tuple[List[GUIPoint], List[GUIPoint], List[GUILine]]:
        """Create lists of water bomber points, paths and bases and add to canvas."""
        water_bomber_base_points: List[GUIPoint] = []
        water_bomber_points: List[GUIPoint] = []
        water_bomber_paths: List[GUILine] = []
        for water_bomber_type in self.simulator.water_bomber_bases_dict:
            for base in self.simulator.water_bomber_bases_dict[water_bomber_type]:
                self.create_point_from_elm(base, water_bomber_base_points, rad=2)
        for water_bomber in self.simulator.water_bombers:
            last_point: Location = water_bomber.past_locations[0]
            for idx, point in enumerate(water_bomber.past_locations):
                if idx != 0:
                    if idx == len(water_bomber.past_locations) - 1:
                        self.connect_points(point, last_point, water_bomber_paths)
                    else:
                        dx1 = point.lon - last_point.lon
                        dy1 = point.lat - last_point.lat
                        dx2 = water_bomber.past_locations[idx + 1].lon - point.lon
                        dy2 = water_bomber.past_locations[idx + 1].lat - point.lat
                        if abs(dx2 * dy1 - dx1 * dy2) > EPSILON:
                            self.connect_points(point, last_point, water_bomber_paths)
                            last_point = point
            self.create_point_from_elm(water_bomber, water_bomber_points, rad=4)
        return water_bomber_base_points, water_bomber_points, water_bomber_paths

    def create_water_tanks(self) -> List[GUIPoint]:
        """Create list of water tanks and add to canvas."""
        water_tank_points: List[GUIPoint] = []
        for tank in self.simulator.water_tanks:
            self.create_point_from_elm(tank, water_tank_points, rad=2)
        return water_tank_points

    def create_checkboxes(self) -> Dict[str, Tuple[tk.IntVar, tk.Checkbutton, Sequence[GUIObject]]]:
        """Create check boxes for interating with GUI."""
        return_dict: Dict[str, Tuple[tk.IntVar, tk.Checkbutton, Sequence[GUIObject]]] = {}

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
        self, element: Location, list_name: List[GUIPoint], rad: int = 5
    ) -> None:  # center coordinates, radius
        """Create a point given an element extending Location."""
        point = GUIPoint(element, self.canvas, self.map_image.get_coordinates, radius=rad)
        list_name.append(point)

    def connect_points(self, p_1: Location, p_2: Location, list_name: List[GUILine]) -> None:
        """Connect two points with a line."""
        # line = self.canvas.create_line(  # type: ignore
        # self.map_image.get_coordinates(p_1.lat, p_1.lon),
        # self.map_image.get_coordinates(p_2.lat, p_2.lon),
        # fill=type_to_colour(p_1),
        # width=1,
        # )
        line = GUILine(p_1, p_2, self.canvas, self.map_image.get_coordinates)
        list_name.append(line)

    def update_objects(self) -> None:
        """Update whether a set of points is displayed on the canvas."""
        for key in self.checkbox_dict:
            if self.checkbox_dict[key][0].get() == 0:  # type: ignore
                for obj in self.checkbox_dict[key][2]:
                    obj.hide(self.canvas)
            else:
                for obj in self.checkbox_dict[key][2]:
                    obj.update(self.canvas)
                    obj.show(self.canvas)

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
        self.restart()
        self.coords = event.x, event.y  # type: ignore

    def click(self, event: Event) -> None:
        """Process click.

        Args:
            event: Click event
        """
        self.coords = event.x, event.y  # type: ignore
        self.redraw()

    def reload(self) -> None:
        """Reload."""
        self.redraw()
        self.window["cursor"] = ""

    def restart(self) -> None:
        """Restart."""
        self.window["cursor"] = "watch"
        self.window.after(1, self.reload)

    def redraw(self) -> None:
        """Redraw display."""
        # profiler = cProfile.Profile()
        # profiler.enable()
        width = int(self.canvas["width"])
        height = int(self.canvas["height"])

        self.image = self.map_image.get_image()
        self.tk_image = ImageTk.PhotoImage(self.image)
        map_object = self.canvas.create_image(
            width / 2, height / 2, image=self.tk_image
        )  # type:ignore

        self.zoom_in_button.place(x=width - 50, y=height - 80)
        self.zoom_out_button.place(x=width - 50, y=height - 50)

        self.canvas.lower(map_object)
        self.update_objects()
        # profiler.disable()
        # stats = pstats.Stats(profiler).sort_stats('cumtime')
        # stats.print_stats()


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


# class GUIInfo:
# def __init__(self, simulation: Simulator):
# self.lightning : List[]


def start_gui(simulation: Simulator) -> None:
    """Start GUI of simulation."""
    GUI(simulation)


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

        self.mainloop()

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
    MapUI()
