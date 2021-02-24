"""GUI Module for bushfire drone simulation."""

import tkinter as tk
from pathlib import Path
from tkinter import Button, Canvas, DoubleVar, Event, Scale
from tkinter.constants import BOTH, HORIZONTAL, X
from typing import Dict, List, Sequence, Tuple

from PIL import ImageTk

from bushfire_drone_simulation.gui.gui_data import GUIData
from bushfire_drone_simulation.gui.gui_objects import GUIObject
from bushfire_drone_simulation.gui.map_image import MapImage
from bushfire_drone_simulation.simulator import Simulator

WIDTH = 1000
HEIGHT = 600
ZOOM = 7
LATITUDE = -36.25
LONGITUDE = 147.9


class GUI:
    """GUI class for bushfire drone simulation."""

    def __init__(self, gui_data: GUIData) -> None:
        """Run GUI from simulator."""
        self.gui_data = gui_data
        self.width, self.height = WIDTH, HEIGHT

        self.window = tk.Tk()
        self.window.title("ANU Bushfire Initiative Drone Simulation")
        title = tk.Label(self.window, text="ANU Bushfire Initiative Drone Simulation")
        title.pack()
        self.canvas: Canvas = tk.Canvas(self.window, width=self.width, height=self.height)
        self.canvas.pack(fill=BOTH, expand=True)

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
            to=int(self.gui_data.max_time / 3600 + 1.0),
            label="Start Time (hrs)",
            resolution=0.01,
            length=self.width,
            sliderlength=20,
            tickinterval=1,
            command=self.start_slider_update,
        )
        self.end_scale = Scale(
            self.window,
            variable=self.end_time,
            orient=HORIZONTAL,
            from_=0,
            to=int(self.gui_data.max_time / 3600 + 1.0),
            label="End Time (hrs)",
            resolution=0.01,
            length=self.width,
            sliderlength=20,
            tickinterval=1,
            command=self.end_slider_update,
        )
        self.end_scale.set(int(self.gui_data.max_time / 3600 + 1.0))  # type: ignore
        self.start_scale.pack(fill=X)
        self.end_scale.pack(fill=X)

        self.coords = (0, 0)
        self.image = None
        self.tk_image = None

        self.restart()
        self.checkbox_dict = self.create_checkboxes()

        y = 2
        for key in self.checkbox_dict:
            self.checkbox_dict[key][1].select()  # type: ignore
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
            "uav_bases": {"text": "Show UAV Bases", "list": self.gui_data.uav_bases},
            "wb_bases": {"text": "Show Water Bomber Bases", "list": self.gui_data.wb_bases},
            "uav_lines": {"text": "Show UAV Paths", "list": self.gui_data.uav_lines},
            "wb_lines": {"text": "Show WB Paths", "list": self.gui_data.wb_lines},
            "lightning": {"text": "Show Lightning", "list": self.gui_data.lightning},
            "ignitions": {"text": "Show Ignitions", "list": self.gui_data.ignitions},
            "uavs": {"text": "Show UAVs", "list": self.gui_data.uavs},
            "water_bombers": {"text": "Show Water Bombers", "list": self.gui_data.water_bombers},
        }

        for checkbox_name in checkboxes_to_create:
            toggle = tk.IntVar()
            checkbox = tk.Checkbutton(
                self.window,
                text=checkboxes_to_create[checkbox_name]["text"],  # type: ignore
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
            if self.checkbox_dict[key][0].get() == 0:
                for obj in self.checkbox_dict[key][3]:
                    obj.hide(self.canvas)
            else:
                for obj in self.checkbox_dict[key][3]:
                    obj.show_given_time(
                        self.canvas,
                        self.start_time.get() * 60 * 60,
                        self.end_time.get() * 60 * 60,
                    )
                    obj.update(self.canvas)

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

    def drag(self, event: Event) -> None:  # type: ignore
        """Process mouse drag.

        Args:
            event: Mouse drag event
        """
        self.map_image.move(self.coords[0] - event.x, self.coords[1] - event.y)
        self.restart()
        self.coords = event.x, event.y

    def click(self, event: Event) -> None:  # type: ignore
        """Process click.

        Args:
            event: Click event
        """
        self.coords = event.x, event.y
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

    def resize(  # pylint: disable=unused-argument
        self, event: Event  # type: ignore
    ) -> None:
        """Resize canvas."""
        if (
            int(self.canvas.winfo_height() != self.height)
            or int(self.canvas.winfo_width()) != self.width
        ):
            self.height = int(self.canvas.winfo_height())
            self.width = int(self.canvas.winfo_width())
            self.window.after(1, self.reload)
            self.map_image.set_size(self.width, self.height)

    def start_slider_update(self, time: str) -> None:  # pylint: disable = unused-argument
        """Update times given slider update.

        Args:
            time (str): time
        """
        if self.start_time.get() > self.end_time.get():
            self.end_time.set(self.start_time.get())
        self.update_objects()

    def end_slider_update(self, time: str) -> None:  # pylint: disable = unused-argument
        """Update times given slider update.

        Args:
            time (str): time
        """
        if self.start_time.get() > self.end_time.get():
            self.start_time.set(self.end_time.get())
        self.update_objects()


def start_gui(simulation: Simulator) -> None:
    """Start GUI of simulation."""
    GUI(GUIData.from_simulator(simulation))


def start_gui_from_file(path: Path, scenario_name: str) -> None:
    """Start GUI of simulation output."""
    GUI(GUIData.from_output(path, scenario_name))
