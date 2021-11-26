"""GUI Module for bushfire drone simulation."""

import tkinter as tk
import tkinter.filedialog
from pathlib import Path
from tkinter import Canvas, DoubleVar, Event, Menu, Scale, ttk
from tkinter.constants import BOTH, HORIZONTAL, X
from typing import Dict, Optional

from PIL import ImageTk

from bushfire_drone_simulation.gui.gui_data import GUIData
from bushfire_drone_simulation.gui.map_image import MapImage
from bushfire_drone_simulation.simulator import Simulator

WIDTH = 1000
HEIGHT = 400
ZOOM = 7
LATITUDE = -36.25
LONGITUDE = 147.9


class GUI:
    """GUI class for bushfire drone simulation."""

    def open_file(self) -> None:
        """Create open file dialog."""
        dlg = tkinter.filedialog.Open(filetypes=[("CSV Files", "*.csv"), ("All files", "*")])
        filename = Path(dlg.show())
        try:
            temp_gui_data = GUIData.from_output(filename.parent, filename.name.split("_")[0])
            self.canvas.delete("object")
            self.gui_data = temp_gui_data
            self.initialise_display()
        except FileNotFoundError:
            print(f"File not found {filename}")

    def save_file(self) -> None:
        """Create save file dialog."""
        dlg = tkinter.filedialog.Directory()
        folder = Path(dlg.show())
        self.gui_data.save_to(Path(folder))

    def new_simulation(self) -> None:
        """Create new simulation dialog."""
        self.gui_data = GUIData([], [], [], [], [], [], [])

    def __init__(self, gui_data: GUIData) -> None:
        """Run GUI from simulator."""
        self.gui_data = gui_data
        self.width, self.height = WIDTH, HEIGHT

        self.window = tk.Tk()
        self.window.title("ANU Bushfire Initiative Drone Simulation")
        self.canvas: Canvas = tk.Canvas(self.window, width=self.width, height=self.height)
        self.canvas.pack(fill=BOTH, expand=True)

        self.canvas.bind("<B1-Motion>", self.drag)
        self.window.bind("<Button-1>", self.click)
        self.window.bind("<Configure>", self.resize)

        menubar = Menu(self.window)
        filemenu: Menu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="New Simulation", command=self.new_simulation)
        filemenu.add_command(label="Open", command=self.open_file)
        filemenu.add_command(label="Save", command=self.save_file)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.window.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        self.viewmenu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=self.viewmenu)
        self.window.config(menu=menubar)

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
        self.checkbox_dict = self.create_viewmenu()
        self.initialise_display()
        self.update_objects()
        self.window.mainloop()

    def initialise_display(self) -> None:
        """Initialize display by adding objects and updating scale."""
        for name in self.gui_data.dict.keys():
            for obj in self.gui_data[name]:
                obj.place_on_canvas(self.canvas, self.map_image.get_coordinates)
        self.end_scale["to"] = int(self.gui_data.max_time / 3600 + 1.0)
        self.start_scale["to"] = int(self.gui_data.max_time / 3600 + 1.0)
        self.update_objects()

    def create_viewmenu(
        self,
    ) -> Dict[str, tk.BooleanVar]:
        """Create view menu for interacting with GUI."""
        return_dict: Dict[str, tk.BooleanVar] = {}
        name_map = {
            "water_tanks": "Show Water Tanks",
            "uav_bases": "Show UAV Bases",
            "wb_bases": "Show Water Bomber Bases",
            "uav_lines": "Show UAV Paths",
            "wb_lines": "Show WB Paths",
            "lightning": "Show Lightning",
            "ignitions": "Show Ignitions",
            "uavs": "Show UAVs",
            "water_bombers": "Show Water Bombers",
        }

        for object_type in self.gui_data.dict.keys():
            toggle = tk.BooleanVar()
            toggle.set(True)
            self.viewmenu.add_checkbutton(
                label=name_map[object_type],
                onvalue=1,
                offvalue=0,
                variable=toggle,
                command=self.update_objects,
            )
            return_dict[object_type] = toggle
        return return_dict

    def update_objects(self) -> None:
        """Update whether a set of points is displayed on the canvas."""
        for name, toggle in self.checkbox_dict.items():
            if not toggle.get():
                for obj in self.gui_data[name]:
                    obj.hide(self.canvas)
            else:
                for obj in self.gui_data[name]:
                    obj.show_given_time(
                        self.canvas,
                        self.start_time.get() * 60 * 60,
                        self.end_time.get() * 60 * 60,
                    )
                    obj.update(self.canvas)

    def add_zoom_button(self, text: str, change: int) -> ttk.Button:
        """Add zoom button.

        Args:
            text (str): text
            change (int): change
        """
        button = ttk.Button(
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
        map_object = self.canvas.create_image(self.width / 2, self.height / 2, image=self.tk_image)

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


def start_gui(simulation: Optional[Simulator] = None) -> None:
    """Start GUI of simulation."""
    if simulation is None:
        GUI(GUIData([], [], [], [], [], [], []))
    else:
        GUI(GUIData.from_simulator(simulation))


def start_gui_from_file(path: Path, scenario_name: str) -> None:
    """Start GUI of simulation output."""
    GUI(GUIData.from_output(path, scenario_name))
