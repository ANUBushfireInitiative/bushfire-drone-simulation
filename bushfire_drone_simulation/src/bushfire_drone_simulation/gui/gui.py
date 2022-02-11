"""GUI Module for bushfire drone simulation."""

import os
import sys
import tkinter as tk
import tkinter.filedialog
import webbrowser
from functools import partial
from io import BytesIO
from pathlib import Path
from tkinter import Canvas, DoubleVar, Event, Frame, Menu, Scale, Text, ttk
from tkinter.constants import BOTH, DISABLED, HORIZONTAL, INSERT, X
from typing import Dict, Optional

import _tkinter
import cv2
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.pyplot import close
from PIL import Image as img
from PIL import ImageDraw, ImageFont, ImageTk

from bushfire_drone_simulation.fire_utils import Coordinate
from bushfire_drone_simulation.gui.gui_data import GUIData
from bushfire_drone_simulation.gui.map_downloader import cache_folder
from bushfire_drone_simulation.gui.map_image import MapImage
from bushfire_drone_simulation.gui.popup import GuiPopup
from bushfire_drone_simulation.gui.tk_hyperlink_manager import HyperlinkManager
from bushfire_drone_simulation.parameters import JSONParameters
from bushfire_drone_simulation.plots import (
    inspection_time_histogram,
    risk_rating_plot,
    risk_rating_plot_over_time,
    suppression_time_histogram,
    suppressions_per_bomber_plot,
    water_tank_plot,
)
from bushfire_drone_simulation.simulator import run_simulations

WIDTH = 400
HEIGHT = 200
ZOOM = 7
LATITUDE = -36.25
LONGITUDE = 147.9


class GUI:
    """GUI class for bushfire drone simulation."""

    def __init__(self, parameters_filename: Optional[Path] = None, mainloop: bool = True) -> None:
        """Run GUI."""
        self.content = False
        self.width, self.height = WIDTH, HEIGHT
        self.params: Optional[JSONParameters] = None
        self.gui_data = GUIData([], [], [], [], [], [], [], [])

        self.window = tk.Tk()
        self.window.title("ANU Bushfire Initiative Drone Simulation")
        self.canvas: Canvas = tk.Canvas(
            self.window, width=self.width, height=self.height, borderwidth=0, highlightthickness=0
        )
        self.canvas.pack(fill=BOTH, expand=True)

        self.canvas.bind("<B1-Motion>", self._drag)
        self.window.bind("<Button-1>", self._click)
        self.window.bind("<Configure>", self.resize)

        self._create_menu()

        self.label = tk.Label(self.canvas)
        self.zoom = ZOOM
        self.map_image = MapImage((self.width, self.height), LATITUDE, LONGITUDE, self.zoom)

        self.zoom_in_button = self.add_zoom_button("+", +1)
        self.zoom_out_button = self.add_zoom_button("-", -1)
        self._add_scales()

        self.coords = (0, 0)
        self.image = None
        self.tk_image = None

        self.copyright_frame = Frame(width=400, height=20)
        self.copyright_text = Text(
            self.copyright_frame, height=1, font=("Helvetica", 8), bg=self.window.cget("bg")
        )
        self.copyright_text.tag_configure("right", justify="right")
        hyperlink = HyperlinkManager(self.copyright_text)
        self.copyright_text.insert(INSERT, "Maps © ")
        self.copyright_text.insert(
            INSERT,
            "Thunderforest",
            hyperlink.add(partial(webbrowser.open, "http://www.thunderforest.com")),
        )
        self.copyright_text.insert(INSERT, ", Map data © ")
        self.copyright_text.insert(
            INSERT,
            "OpenStreetMap contributors",
            hyperlink.add(partial(webbrowser.open, "http://www.openstreetmap.org/copyright")),
        )
        self.copyright_text.tag_add("right", "1.0", "end")
        self.copyright_text.config(state=DISABLED, highlightthickness=0, borderwidth=0)
        self.copyright_text.place(x=0, y=0, width=395)

        self.checkbox_dict = self.create_viewmenu()
        if parameters_filename is not None:
            self.open_file(parameters_filename)
        self.restart()
        if mainloop:
            self.window.mainloop()

    def _create_menu(self) -> None:
        """Create gui menu bar."""
        self.menu_bar = Menu(self.window)
        file_menu: Menu = Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="New Simulation", command=self.new_simulation)
        file_menu.add_command(label="Open", command=self.open_file_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.window.quit)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        self.view_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="View", menu=self.view_menu)
        self.scenario_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Scenario", menu=self.scenario_menu)
        self.plot_menu = Menu(self.menu_bar, tearoff=0)
        self.plot_menu.add_command(
            label="Inspection times", command=lambda: self.show_plot("inspection_time_histogram")
        )
        self.plot_menu.add_command(
            label="Suppression times", command=lambda: self.show_plot("suppression_time_histogram")
        )
        self.plot_menu.add_command(
            label="Suppressions per water bomber",
            command=lambda: self.show_plot("suppressions_per_water_bomber"),
        )
        self.plot_menu.add_command(
            label="Water tank capacities", command=lambda: self.show_plot("water_tank_capacities")
        )
        self.plot_menu.add_command(
            label="Risk rating", command=lambda: self.show_plot("risk_rating")
        )
        self.plot_menu.add_command(
            label="Risk rating over time",
            command=lambda: self.show_plot("risk_rating_over_time"),
        )
        self.menu_bar.add_cascade(label="Plots", menu=self.plot_menu)
        self.tools_menu = Menu(self.menu_bar, tearoff=0)
        self.tools_menu.add_command(label="Clear Cache", command=self.clear_cache)
        self.tools_menu.add_command(label="Change map dimensions", command=self._size_dialog)
        self.tools_menu.add_command(label="Screenshot", command=self._screenshot_dialog)
        self.tools_menu.add_command(label="Video", command=self._video_dialog)
        self.menu_bar.add_cascade(label="Tools", menu=self.tools_menu)
        self.window.config(menu=self.menu_bar)

    def _screenshot_dialog(self) -> None:
        filename = tkinter.filedialog.asksaveasfilename(
            initialfile="Screenshot.png", filetypes=[("PNG", "*.png")]
        )
        self.screenshot().save(filename)

    def _video_dialog(self) -> None:
        popup = GuiPopup(self.window, 300, 150)
        popup.grid_columnconfigure(0, weight=1)
        popup.grid_columnconfigure(1, weight=1)
        tk.Label(popup, text="Select video settings").grid(row=0, column=0, columnspan=2)
        start_box = tk.Entry(popup)
        start_box.insert(0, str(self.start_time.get()))
        end_box = tk.Entry(popup)
        end_box.insert(0, str(self.end_time.get()))
        resolution_box = tk.Entry(popup)
        resolution_box.insert(0, str(0.01))
        tail_box = tk.Entry(popup)
        tail_box.insert(0, str(0.2))
        start_time = self.start_time.get()
        end_time = self.end_time.get()

        def record_video() -> None:
            filename = tkinter.filedialog.asksaveasfilename(
                initialfile="Video.mp4", filetypes=[("MP4", "*.mp4")]
            )
            self.video(
                filename,
                float(start_box.get()),
                float(end_box.get()),
                float(resolution_box.get()),
                float(tail_box.get()),
            )
            self.start_time.set(start_time)
            self.end_time.set(end_time)
            self.update_objects()
            popup.close()

        tk.Label(popup, text="Start time (hr):").grid(row=1, column=0)
        start_box.grid(row=1, column=1)
        tk.Label(popup, text="End time (hr):").grid(row=2, column=0)
        end_box.grid(row=2, column=1)
        tk.Label(popup, text="Frame time (hr):").grid(row=3, column=0)
        resolution_box.grid(row=3, column=1)
        tk.Label(popup, text="Tail time (hr):").grid(row=4, column=0)
        tail_box.grid(row=4, column=1)
        ttk.Button(popup, text="Record video", command=record_video).grid(
            row=5, column=0, columnspan=2
        )

    def _add_scales(self) -> None:
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
            command=self._start_slider_update,
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
            command=self._end_slider_update,
        )
        self.end_scale.set(int(self.gui_data.max_time / 3600 + 1.0))  # type: ignore
        self.start_scale.pack(fill=X)
        self.end_scale.pack(fill=X)

    def screenshot(self) -> img.Image:  # type: ignore
        """Take a screenshot of the canvas and return as image.

        Args:
            filename (Path): filename

        Returns:
            None:
        """
        self.canvas.update()
        postscript: str = self.canvas.postscript(  # type: ignore
            colormode="color",
            width=self.width,
            height=self.height,
            pagewidth=self.width * 5,
            pageheight=self.height * 5,
        )
        try:
            image = img.open(BytesIO(postscript.encode("utf-8"))).resize((self.width, self.height))
        except FileNotFoundError:
            print(
                "Error creating screenshot. This may be because you do not have ghostscript "
                "installed. If you do not, please install it."
            )
            sys.exit()
        draw = ImageDraw.Draw(image)
        with open(Path(__file__).parent.parent / "fonts" / "OpenSans-Regular.ttf", "rb") as font_fl:
            font = ImageFont.truetype(
                font_fl,
                size=10,
            )
        copyright_text = "Maps © www.thunderforest.com, Data © www.osm.org/copyright"
        width, height = font.getsize(copyright_text)
        draw.text(
            (self.width - width - 5, self.height - height - 2),
            copyright_text,
            (0, 0, 0),
            font=font,
        )
        return image

    def video(  # pylint: disable=too-many-arguments
        self, filename: str, start_time: float, end_time: float, frame_time: float, tail_time: float
    ) -> None:
        """Record a video.

        Args:
            filename (str): filename
            start_time (float): start_time
            end_time (float): end_time
            frame_time (float): frame_time
        """
        frames = []
        for frame_end_time in np.arange(start_time, end_time, frame_time):
            self.start_time.set(max(0, frame_end_time - tail_time))
            self.end_time.set(frame_end_time)
            self.update_objects()
            self.window.update()
            frames.append(self.screenshot())

        video = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*"mp4v"), 30, frames[0].size)
        for frame in frames:
            video.write(cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR))
        cv2.destroyAllWindows()
        video.release()

    def clear_cache(self) -> None:
        """Remove all cached map tiles."""
        popup = GuiPopup(self.window, 250, 100)
        tk.Label(popup, text="Deleting cached tiles").pack()
        progress_var = tk.DoubleVar()
        ttk.Progressbar(
            popup, variable=progress_var, maximum=len(list(cache_folder.glob("*"))), length=200
        ).pack()
        for cache_img in cache_folder.glob("*"):
            popup.update()
            os.remove(cache_img)
            progress_var.set(progress_var.get() + 1)
        popup.close()

    def show_plot(self, plot_type: str) -> None:
        """Show plot."""
        popup = GuiPopup(self.window, 600, 400)
        popup.title("Dashboard")
        fig = Figure(figsize=(1, 1), dpi=100, tight_layout=True)
        axs = fig.add_subplot(111)

        if plot_type == "inspection_time_histogram":
            inspection_times = list(
                filter(
                    None,
                    [lightning.inspection_time_hr() for lightning in self.gui_data.all_lightning],
                )
            )
            inspection_time_histogram(axs, inspection_times)
        elif plot_type == "suppression_time_histogram":
            suppression_times = list(
                filter(
                    None,
                    [lightning.suppression_time_hr() for lightning in self.gui_data.all_lightning],
                )
            )
            suppression_time_histogram(axs, suppression_times)
        elif plot_type == "suppressions_per_water_bomber":
            suppressions_per_bomber_plot(axs, self.gui_data.water_bombers)
        elif plot_type == "water_tank_capacities":
            water_tank_plot(axs, self.gui_data.watertanks)
        elif plot_type == "risk_rating":
            risk_rating_plot(axs, self.gui_data.all_lightning)
        elif plot_type == "risk_rating_over_time":
            risk_rating_plot_over_time(fig, axs, self.gui_data.all_lightning)

        canvas = FigureCanvasTkAgg(fig, popup)
        canvas.draw()
        toolbar = NavigationToolbar2Tk(canvas, popup)
        toolbar.pack()
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True)
        toolbar.update()
        popup.on_close = lambda: close(fig)  # type: ignore

    def _size_dialog(self) -> None:
        """Change size of map."""
        popup = GuiPopup(self.window, 250, 100)
        popup.grid_columnconfigure(0, weight=1)
        popup.grid_columnconfigure(1, weight=1)
        tk.Label(popup, text="Select map size").grid(row=0, column=0, columnspan=2)
        width_box = tk.Entry(popup)
        width_box.insert(0, str(self.width))
        height_box = tk.Entry(popup)
        height_box.insert(0, str(self.height))

        def set_size() -> None:
            self.width = int(width_box.get())
            self.height = int(height_box.get())
            self.canvas.config(width=self.width, height=self.height)
            popup.close()
            self.redraw()

        tk.Label(popup, text="Width:").grid(row=1, column=0)
        width_box.grid(row=1, column=1)
        tk.Label(popup, text="Height:").grid(row=2, column=0)
        height_box.grid(row=2, column=1)
        ttk.Button(popup, text="Set dimensions", command=set_size).grid(
            row=3, column=0, columnspan=2
        )

    def open_file_dialog(self) -> None:
        """Create open file dialog."""
        dlg = tkinter.filedialog.Open(
            filetypes=[("GUI JSON Files", "*gui.json"), ("All files", "*")],
            title="Please select the parameters json file to open",
        )
        filename = Path(dlg.show())
        self.open_file(filename)

    def open_file(self, parameters_file: Path) -> None:
        """Open parameters file."""
        self.params = JSONParameters(parameters_file)
        self.set_scenario(0)

    def set_scenario(self, scenario: int) -> None:
        """Swap GUI to another scenario.

        Args:
            scenario (int): Index of scenario
        """
        assert self.params is not None
        try:
            temp_gui_data = GUIData.from_output(self.params, scenario)
            self.destroy_display()
            self.gui_data = temp_gui_data
            self.initialise_display()
        except FileNotFoundError as err:
            print(err)
        except TypeError as err:
            print(err)

    def new_simulation(self) -> None:
        """Create new simulation dialog."""
        dlg = tkinter.filedialog.Open(
            filetypes=[("JSON Files", "*.json"), ("All files", "*")],
            title=(
                "Please select the parameter json file (parameters.json) you wish to use for"
                "the simulation"
            ),
        )
        filename = Path(dlg.show())
        # popup_height = 100
        # popup_width = 250
        # popup = tk.Toplevel()
        # popup.grab_set()  # type: ignore
        # popup_x = self.window.winfo_x() + (self.window.winfo_width() - popup_width) // 2
        # popup_y = self.window.winfo_y() + (self.window.winfo_height() - popup_height) // 2
        # popup.geometry(f"{popup_width}x{popup_height}+{popup_x}+{popup_y}")
        params = JSONParameters(filename)
        params.create_output_folder(
            confirmation=lambda m: tkinter.messagebox.askyesno(  # type: ignore
                "Confirmation",
                m,
            ),
        )
        run_simulations(params, use_parallel=True)
        self.open_file(params.gui_filename)
        # temp_gui_data = GUIData.from_simulator(simulators[0])
        # temp_gui_data = GUIData.from_output(filename.parent, "1")
        # self.canvas.delete("object")
        # self.gui_data = temp_gui_data
        # self.initialise_display()
        # popup.grab_release()  # type: ignore
        # popup.destroy()

    def destroy_display(self) -> None:
        """Destroy display by removing objects and scenarios."""
        self.content = False
        self.canvas.delete("object")
        self.scenario_menu.delete(0, 100)

    def initialise_display(self) -> None:
        """Initialize display by adding objects and updating scale."""
        for _, objs in self.gui_data.dict.items():
            for obj in objs:
                obj.place_on_canvas(self.canvas, self.map_image.get_coordinates)
        self.content = True
        self.end_scale["to"] = int(self.gui_data.max_time / 3600 + 1.0)
        self.start_scale["to"] = int(self.gui_data.max_time / 3600 + 1.0)
        if self.params is not None:
            for i in range(len(self.params.scenarios)):
                name = self.params.scenario_name(i)
                self.scenario_menu.add_command(
                    label=name,
                    command=partial(self.set_scenario, i),
                )
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
            "targets": "Show Targets",
        }

        for object_type in self.gui_data.dict:
            toggle = tk.BooleanVar()
            toggle.set(True)
            self.view_menu.add_checkbutton(
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
        if self.content:
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

    def _drag(self, event: Event) -> None:  # type: ignore
        """Process mouse drag.

        Args:
            event: Mouse drag event
        """
        self.map_image.move(self.coords[0] - event.x, self.coords[1] - event.y)
        self.restart()
        self.coords = event.x, event.y

    def _click(self, event: Event) -> None:  # type: ignore
        """Process click.

        Args:
            event: Click event
        """
        self.coords = event.x, event.y
        loc = self.map_image.get_lat_long(Coordinate(*self.coords))
        print(f"Latitude: {loc.lat} Longitude: {loc.lon}")
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
        self.tk_image = ImageTk.PhotoImage(self.image, master=self.window)
        map_object = self.canvas.create_image(
            self.width // 2, self.height // 2, image=self.tk_image
        )

        self.zoom_in_button.place(x=self.width - 30, y=self.height - 70)
        self.zoom_out_button.place(x=self.width - 30, y=self.height - 40)
        self.copyright_frame.place(x=self.width - 400, y=self.height)

        self.canvas.lower(map_object)
        self.update_objects()
        # profiler.disable()
        # stats = pstats.Stats(profiler).sort_stats('cumtime')
        # stats.print_stats()

    def resize(self, _: Event) -> None:  # type: ignore
        """Resize canvas."""
        if (
            int(self.canvas.winfo_height() != self.height)
            or int(self.canvas.winfo_width()) != self.width
        ):
            self.height = int(self.canvas.winfo_height())
            self.width = int(self.canvas.winfo_width())
            self.window.after(1, self.reload)
            self.map_image.set_size(self.width, self.height)

    def _start_slider_update(self, _: str) -> None:
        """Update times given slider update."""
        if self.start_time.get() > self.end_time.get():
            self.end_time.set(self.start_time.get())
        self.update_objects()

    def _end_slider_update(self, _: str) -> None:
        """Update times given slider update."""
        if self.start_time.get() > self.end_time.get():
            self.start_time.set(self.end_time.get())
        self.update_objects()

    def run_events(self) -> None:
        """Run all current events."""
        while self.window.dooneevent(_tkinter.ALL_EVENTS | _tkinter.DONT_WAIT):
            pass
