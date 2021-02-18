"""GUI Module for bushfire drone simulation."""

import tkinter as tk
from abc import abstractmethod
from tkinter import Button, Canvas, DoubleVar, Event, Scale
from tkinter.constants import BOTH, HORIZONTAL, X
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from PIL import ImageTk

from bushfire_drone_simulation.aircraft import Aircraft
from bushfire_drone_simulation.fire_utils import Location
from bushfire_drone_simulation.gui.map_image import MapImage
from bushfire_drone_simulation.simulator import Simulator

WIDTH = 1000
HEIGHT = 750
ZOOM = 7
LATITUDE = -36.25
LONGITUDE = 147.9

EPSILON: float = 0.0000001


class GUIObject:
    """GUIObject.

    This class defines the functions that all GUI objects must implement.
    """

    def __init__(self) -> None:
        """__init__."""
        self.to_coordinates: Callable[[Location], Tuple[int, int]] = lambda l: (0, 0)
        self.canvas_object: int = -1
        self.cur_shown = True
        self.tags = ["all"]

    @abstractmethod
    def place_on_canvas(
        self, canvas: Canvas, to_coordinates: Callable[[Location], Tuple[int, int]]
    ) -> None:
        """Place object on canvas."""

    def hide(self, canvas: Canvas) -> None:
        """Hide line."""
        if self.cur_shown:
            canvas.itemconfigure(self.canvas_object, state="hidden")
            self.cur_shown = False

    def show(self, canvas: Canvas) -> None:
        """Show line."""
        if not self.cur_shown:
            canvas.itemconfigure(self.canvas_object, state="normal")
            self.cur_shown = True

    @abstractmethod
    def show_given_time(self, canvas: Canvas, start_time: float, end_time: float) -> None:
        """Show the object if it should be visible in the given timeframe."""

    @abstractmethod
    def update(self, canvas: Canvas) -> None:
        """Update the position etc. of the object."""


class GUIPoint(GUIObject):
    """GUI Point.

    This class defines a GUI Point (AKA a circle).
    """

    def __init__(self, location: Location, radius: int = 4, colour: str = "yellow"):
        """__init__.

        Args:
            location (Location): location of point (Global coordinates)
            canvas (Canvas): canvas on which point belongs
            to_coordinates (Callable[[float, float], Tuple[int, int]]): Function converting location
                to coordinates on the canvas.
            radius (int): radius of point
        """
        super().__init__()
        self.location = location
        self.radius = radius
        self.colour = colour
        self.x, self.y = 0, 0
        self.tags.append("point")

    def place_on_canvas(
        self, canvas: Canvas, to_coordinates: Callable[[Location], Tuple[int, int]]
    ) -> None:
        """Place point on canvas.

        Args:
            canvas (Canvas): canvas
            to_coordinates (Callable[[float, float], Tuple[int,int]]): to_coordinates
        """
        self.to_coordinates = to_coordinates
        self.x, self.y = to_coordinates(self.location)
        self.canvas_object = canvas.create_oval(  # type: ignore
            self.x - self.radius,
            self.y - self.radius,
            self.x + self.radius,
            self.y + self.radius,
            fill=self.colour,
            tags=self.tags,
        )

    def update(self, canvas: Canvas) -> None:
        """Update position of the point."""
        x, y = self.to_coordinates(self.location)
        canvas.move(self.canvas_object, x - self.x, y - self.y)  # type: ignore
        self.x, self.y = x, y

    def show_given_time(self, canvas: Canvas, start_time: float, end_time: float) -> None:
        """Show point at the given time.

        This implementation will always show the point.

        Args:
            canvas (Canvas): canvas
            start_time (float): start_time
            end_time (float): end_time
        """
        self.show(canvas)


class GUILine(GUIObject):
    """GUI object representing a line between two global coordinates."""

    def __init__(self, p_1: Location, p_2: Location, width: int = 1, colour: str = "black"):
        """__init__.

        Args:
            p_1 (Location): Global coordinates of start of line.
            p_2 (Location): Global coordinates of end of line.
            canvas (Canvas): canvas on which line belongs
            to_coordinates (Callable[[float, float], Tuple[int, int]]): Function converting global
                coordinates to pixel coordinates.
        """
        self.p_1 = p_1
        self.p_2 = p_2
        self.width = width
        self.colour = colour
        self.tags.append("line")

    def place_on_canvas(
        self, canvas: Canvas, to_coordinates: Callable[[Location], Tuple[int, int]]
    ) -> None:
        """Place line on canvas.

        Args:
            canvas (Canvas): canvas
            to_coordinates (Callable[[float, float], Tuple[int,int]]): to_coordinates
        """
        self.to_coordinates = to_coordinates
        c_1 = self.to_coordinates(self.p_1)
        c_2 = self.to_coordinates(self.p_2)
        self.canvas_object = canvas.create_line(
            c_1, c_2, fill=self.colour, width=self.width, tags=self.tags
        )  # type: ignore

    def update(self, canvas: Canvas) -> None:
        """Update position of line."""
        c_1 = self.to_coordinates(self.p_1)
        c_2 = self.to_coordinates(self.p_2)
        coordinates = list(c_1 + c_2)
        canvas.coords(self.canvas_object, coordinates)  # type: ignore

    def show_given_time(self, canvas: Canvas, start_time: float, end_time: float) -> None:
        """Show line at the given time.

        This implementation will always show the point.

        Args:
            canvas (Canvas): canvas
            start_time (float): start_time
            end_time (float): end_time
        """
        self.show(canvas)


class GUILightning(GUIPoint):
    """Point lightning object for GUI."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        location: Location,
        idx: int,
        spawn_time: float,
        inspection_time: Optional[float],
        suppressed_time: Optional[float],
        ignited: bool,
    ):
        """__init__.

        Args:
            location (Location): location
            spawn_time (float): spawn_time
            inspection_time (Optional[float]): inspection_time
            suppressed_time (Optional[float]): suppressed_time
        """
        super().__init__(location, colour="red" if ignited else "yellow")
        self.idx = idx
        self.ignited = ignited
        self.spawn_time = spawn_time
        self.inspection_time = inspection_time
        self.suppressed_time = suppressed_time
        self.tags.append("lightning")
        self.tags.append(f"lightning {self.idx}")

    def place_on_canvas(
        self, canvas: Canvas, to_coordinates: Callable[[Location], Tuple[int, int]]
    ) -> None:
        """place_on_canvas.

        Args:
            canvas (Canvas): canvas
            to_coordinates (Callable[[Location], Tuple[int, int]]): to_coordinates
        """
        super().place_on_canvas(canvas, to_coordinates)
        canvas.tag_bind(f"lightning {self.idx}", "<Button-1>", self.clicked_lightning)

    def clicked_lightning(self, *args):  # type: ignore # pylint: disable=unused-argument
        """clicked_lightning.

        Args:
            args:
        """
        print("You clicked lightning:", self.idx)

    def show_given_time(self, canvas: Canvas, start_time: float, end_time: float) -> None:
        """Show lightning state at given time.

        Args:
            canvas (Canvas): canvas
            start_time (float): start_time
            end_time (float): end_time
        """
        if self.ignited:
            assert self.suppressed_time is not None
            if self.suppressed_time < start_time:
                self.hide(canvas)
                return
        else:
            assert self.inspection_time is not None
            if self.inspection_time < start_time:
                self.hide(canvas)
                return
        if self.spawn_time > end_time:
            self.hide(canvas)
        else:
            assert self.inspection_time is not None
            if self.ignited and self.inspection_time < end_time:
                if self.inspection_time < start_time:
                    canvas.itemconfig(self.canvas_object, fill="#FFCCCB")
                else:
                    canvas.itemconfig(self.canvas_object, fill="red")
            else:
                if self.spawn_time < start_time:
                    canvas.itemconfig(self.canvas_object, fill="#FFFFDD")
                else:
                    canvas.itemconfig(self.canvas_object, fill="yellow")
            self.show(canvas)


class GUIAircraft(GUIObject):
    """GUIAircraft."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        locations: List[Location],
        times: List[float],
        allocated_at_time: List[bool],
        point_colour: str,
        line_colour: str = "black",
    ) -> None:
        """__init__.

        Args:
            locations (List[Location]): locations
            times (List[float]): times
            allocated_at_time (List[bool]): allocated_at_time
            point_colour (str): point_colour
            line_colour (str): line_colour
        """
        super().__init__()

    def place_on_canvas(
        self, canvas: Canvas, to_coordinates: Callable[[Location], Tuple[int, int]]
    ) -> None:
        """place_on_canvas.

        Args:
            canvas (Canvas): canvas
            to_coordinates (Callable[[Location], Tuple[int, int]]): to_coordinates
        """

    def show_given_time(self, canvas: Canvas, start_time: float, end_time: float) -> None:
        """show_given_time.

        Args:
            canvas (Canvas): canvas
            start_time (float): start_time
            end_time (float): end_time
        """

    def update(self, canvas: Canvas) -> None:
        """update.

        Args:
            canvas (Canvas): canvas
        """


class GUIData:
    """Object for holding GUI data."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        lightning: List[GUILightning],
        ignitions: List[GUILightning],
        uavs: List[GUIAircraft],
        water_bombers: List[GUIAircraft],
        uav_bases: List[GUIPoint],
        wb_bases: List[GUIPoint],
        watertanks: List[GUIPoint],
    ):
        """Initialize a GUI data object.

        Args:
            lightning (List[GUILightning]): lightning
            ignitions (List[GUILightning]): ignitions
            uavs (List[GUIAircraft]): uavs
            water_bombers (List[GUIAircraft]): wbs
            uav_bases (List[GUIPoint]): uav_bases
            wb_bases (List[GUIPoint]): wb_bases
            watertanks (List[GUIPoint]): watertanks
        """
        self.lightning = lightning
        self.ignitions = ignitions
        self.uavs = uavs
        self.water_bombers = water_bombers
        self.uav_bases = uav_bases
        self.wb_bases = wb_bases
        self.watertanks = watertanks

    @classmethod
    def from_simulator(cls, simulation: Simulator) -> "GUIData":
        """Create GUI data from a simulator object.

        Args:
            simulation (Simulator): simulation
        """
        lightning = extract_simulation_lightning(simulation, ignited=False)
        ignitions: List[GUILightning] = extract_simulation_lightning(simulation, ignited=True)
        uavs: List[GUIAircraft] = extract_simulation_aircraft(simulation, "uav")
        water_bombers: List[GUIAircraft] = extract_simulation_aircraft(simulation, "wb")
        uav_bases: List[GUIPoint] = extract_simulation_uav_bases(simulation)
        wb_bases: List[GUIPoint] = extract_simulation_wb_bases(simulation)
        watertanks: List[GUIPoint] = extract_simulation_water_tanks(simulation)
        return cls(lightning, ignitions, uavs, water_bombers, uav_bases, wb_bases, watertanks)


def extract_simulation_lightning(simulation: Simulator, ignited: bool) -> List[GUILightning]:
    """extract_simulation_lightning.

    Args:
        simulation (Simulator): simulation

    Returns:
        List[GUILightning]:
    """
    to_return: List[GUILightning] = []
    for strike in simulation.lightning_strikes:
        if strike.ignition == ignited:
            to_return.append(
                GUILightning(
                    Location(strike.lat, strike.lon),
                    strike.id_no,
                    strike.spawn_time,
                    strike.inspected_time,
                    strike.suppressed_time,
                    strike.ignition,
                )
            )
    return to_return


def extract_simulation_aircraft(simulation: Simulator, aircraft_type: str) -> List[GUIAircraft]:
    """Extract uavs from simulator.

    Args:
        simulation (Simulator): simulation

    Returns:
        List[GUIAircraft]:
    """
    to_return: List[GUIAircraft] = []
    assert aircraft_type in ["uav", "wb"]
    aircraft_list: Sequence[Aircraft] = (  # type: ignore
        simulation.water_bombers if aircraft_type == "wb" else simulation.uavs
    )
    for aircraft in aircraft_list:
        to_return.append(GUIAircraft([], [], [], "orange" if aircraft_type == "wb" else "green"))
    return to_return


def extract_simulation_uav_bases(simulation: Simulator) -> List[GUIPoint]:
    """Extract uav bases from simulator.

    Args:
        simulation (Simulator): simulation

    Returns:
        List[GUIPoint]:
    """
    to_return: List[GUIPoint] = []
    for uav_base in simulation.uav_bases:
        to_return.append(GUIPoint(Location(uav_base.lat, uav_base.lon), radius=2, colour="grey"))
    return to_return


def extract_simulation_wb_bases(simulation: Simulator) -> List[GUIPoint]:
    """Extract water bomber bases from simulator.

    Args:
        simulation (Simulator): simulation

    Returns:
        List[GUIPoint]:
    """
    to_return: List[GUIPoint] = []
    for wb_base in simulation.water_bomber_bases_list:
        to_return.append(GUIPoint(Location(wb_base.lat, wb_base.lon), radius=3, colour="black"))
    return to_return


def extract_simulation_water_tanks(simulation: Simulator) -> List[GUIPoint]:
    """Extract water tanks from simulator.

    Args:
        simulation (Simulator): simulation

    Returns:
        List[GUIPoint]:
    """
    to_return: List[GUIPoint] = []
    for water_tank in simulation.water_tanks:
        to_return.append(
            GUIPoint(Location(water_tank.lat, water_tank.lon), radius=2, colour="blue")
        )
    return to_return


class GUI:
    """GUI class for bushfire drone simulation."""

    def __init__(self, simulator: Simulator, gui_data: GUIData) -> None:
        """Run GUI from simulator."""
        self.gui_data = gui_data
        self.width, self.height = WIDTH, HEIGHT

        self.window = tk.Tk()
        self.window.title("ANU Bushfire Initiative Drone Simulation")
        title = tk.Label(self.window, text="ANU Bushfire Initiative Drone Simulation")
        title.pack()
        self.canvas: Canvas = tk.Canvas(self.window, width=self.width, height=self.height)
        self.canvas.pack(fill=BOTH, expand=True)
        self.simulator = simulator

        self.canvas.bind("<B1-Motion>", self.drag)
        self.window.bind("<Button-1>", self.click)
        self.window.bind("<Configure>", self.resize)

        self.label = tk.Label(self.canvas)
        self.zoom = ZOOM
        self.map_image = MapImage((self.width, self.height), LATITUDE, LONGITUDE, self.zoom)

        self.zoom_in_button = self.add_zoom_button("+", +1)
        self.zoom_out_button = self.add_zoom_button("-", -1)
        self.start_time = DoubleVar()
        self.end_time = DoubleVar()
        self.start_scale = Scale(
            self.window,
            variable=self.start_time,
            orient=HORIZONTAL,
            from_=0,
            to=24,
            label="Start Time (hrs)",
            resolution=0.01,
            length=self.width,
            sliderlength=20,
            tickinterval=1,
            command=self.slider_update,
        )
        self.end_scale = Scale(
            self.window,
            variable=self.end_time,
            orient=HORIZONTAL,
            from_=0,
            to=24,
            label="End Time (hrs)",
            resolution=0.01,
            length=self.width,
            sliderlength=20,
            tickinterval=1,
            command=self.slider_update,
        )
        self.end_scale.set(24)  # type: ignore
        self.start_scale.pack(fill=X, expand=True)
        self.end_scale.pack(fill=X, expand=True)

        self.coords = (0, 0)
        self.image = None
        self.tk_image = None

        self.restart()

        self.checkbox_dict = self.create_checkboxes()

        y = 2
        for key in self.checkbox_dict:
            self.checkbox_dict[key][1].select()  # type: ignore
            # self.canvas.create_window(10, 10, anchor="w", window=checkbox_dict[key][1])
            self.checkbox_dict[key][1].place(x=20, y=y)
            y += 20
            for obj in self.checkbox_dict[key][3]:
                obj.place_on_canvas(self.canvas, self.map_image.get_coordinates)

        self.update_objects()

        self.window.mainloop()

    def create_checkboxes(
        self,
    ) -> Dict[str, Tuple[tk.IntVar, tk.Checkbutton, str, Sequence[GUIObject]]]:
        """Create check boxes for interating with GUI."""
        return_dict: Dict[str, Tuple[tk.IntVar, tk.Checkbutton, str, Sequence[GUIObject]]] = {}

        checkboxes_to_create = {
            "water_tanks": {"text": "Show Water Tanks", "list": self.gui_data.watertanks},
            "wb_bases": {"text": "Show Water Bomber Bases", "list": self.gui_data.wb_bases},
            "uav_bases": {"text": "Show UAV Bases", "list": self.gui_data.uav_bases},
            "uavs": {"text": "Show UAVs", "list": self.gui_data.uavs},
            "water_bombers": {"text": "Show Water Bombers", "list": self.gui_data.water_bombers},
            "lightning": {"text": "Show Lightning", "list": self.gui_data.lightning},
            "ignitions": {"text": "Show Ignitions", "list": self.gui_data.ignitions},
        }

        for checkbox_name in checkboxes_to_create:
            toggle = tk.IntVar()
            checkbox = tk.Checkbutton(
                self.window,
                text=checkboxes_to_create[checkbox_name]["text"],
                variable=toggle,
                onvalue=1,
                offvalue=0,
            )
            obj_list: List[GUIObject] = checkboxes_to_create[checkbox_name]["list"]  # type: ignore
            return_dict[checkbox_name] = (toggle, checkbox, checkbox_name, obj_list)

        return return_dict

    def update_objects(self) -> None:
        """Update whether a set of points is displayed on the canvas."""
        for key in self.checkbox_dict:
            if self.checkbox_dict[key][0].get() == 0:  # type: ignore
                for obj in self.checkbox_dict[key][3]:
                    obj.hide(self.canvas)
            else:
                for obj in self.checkbox_dict[key][3]:
                    obj.update(self.canvas)
                    obj.show_given_time(
                        self.canvas,
                        self.start_time.get() * 60 * 60,  # type: ignore
                        self.end_time.get() * 60 * 60,  # type: ignore
                    )

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
        self.image = self.map_image.get_image()
        self.tk_image = ImageTk.PhotoImage(self.image)
        map_object = self.canvas.create_image(
            self.width / 2, self.height / 2, image=self.tk_image
        )  # type:ignore

        self.zoom_in_button.place(x=self.width - 50, y=self.height - 80)
        self.zoom_out_button.place(x=self.width - 50, y=self.height - 50)

        self.canvas.lower(map_object)
        self.update_objects()
        # profiler.disable()
        # stats = pstats.Stats(profiler).sort_stats('cumtime')
        # stats.print_stats()

    def resize(self, event: Event) -> None:  # pylint: disable=unused-argument
        """Resize canvas."""
        if (
            int(self.canvas.winfo_height() != self.height)  # type: ignore
            or int(self.canvas.winfo_width()) != self.width  # type: ignore
        ):
            self.height = int(self.canvas.winfo_height())  # type: ignore
            self.width = int(self.canvas.winfo_width())  # type: ignore
            self.window.after(1, self.reload)
            self.map_image.set_size(self.width, self.height)

    def slider_update(self, time: str) -> None:
        """Update times given slider update.

        Args:
            time (str): time
        """
        if self.start_time.get() > self.end_time.get():  # type: ignore
            self.end_time.set(self.start_time.get())  # type: ignore
        self.update_objects()


def start_gui(simulation: Simulator) -> None:
    """Start GUI of simulation."""
    GUI(simulation, GUIData.from_simulator(simulation))
