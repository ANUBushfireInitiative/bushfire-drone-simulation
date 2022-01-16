"""Classes for GUI objects."""
from abc import abstractmethod
from tkinter import Canvas
from typing import Callable, List, Optional, Tuple

from bushfire_drone_simulation.aircraft import UpdateEvent
from bushfire_drone_simulation.fire_utils import Location
from bushfire_drone_simulation.uav import UAV
from bushfire_drone_simulation.units import DURATION_FACTORS
from bushfire_drone_simulation.water_bomber import WaterBomber

EPSILON: float = 0.0000001


class GUIObject:
    """GUIObject.

    This class defines the functions that all GUI objects must implement.
    """

    def __init__(self) -> None:
        """__init__."""
        self.to_coordinates: Callable[[Location], Tuple[float, float]] = lambda _: (0, 0)
        self.canvas_object: int = -1
        self.cur_shown = True
        self.tags: Tuple[str, ...] = ("object",)

    @abstractmethod
    def place_on_canvas(
        self, canvas: Canvas, to_coordinates: Callable[[Location], Tuple[float, float]]
    ) -> None:
        """Place object on canvas."""
        assert self.canvas_object == -1

    def remove_from_canvas(self, canvas: Canvas) -> None:
        """Place object on canvas."""
        canvas.delete(self.canvas_object)
        self.canvas_object = -1

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
            to_coordinates (Callable[[float, float], Tuple[float, float]]): Function converting
                location to coordinates on the canvas.
            radius (int): radius of point
        """
        super().__init__()
        self.location = location
        self.radius = radius
        self.colour = colour
        self.x, self.y = 0.0, 0.0
        self.tags += ("point",)

    def place_on_canvas(
        self, canvas: Canvas, to_coordinates: Callable[[Location], Tuple[float, float]]
    ) -> None:
        """Place point on canvas.

        Args:
            canvas (Canvas): canvas
            to_coordinates (Callable[[float, float], Tuple[int,int]]): to_coordinates
        """
        super().place_on_canvas(canvas, to_coordinates)
        self.to_coordinates = to_coordinates
        self.x, self.y = to_coordinates(self.location)
        self.canvas_object = canvas.create_oval(
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

    def __init__(
        self, event1: UpdateEvent, event2: UpdateEvent, width: int = 1, colour: str = "black"
    ):
        """__init__.

        Args:
            p_1 (Location): Global coordinates of start of line.
            p_2 (Location): Global coordinates of end of line.
            canvas (Canvas): canvas on which line belongs
            to_coordinates (Callable[[float, float], Tuple[float, float]]): Function converting
                global coordinates to pixel coordinates.
        """
        super().__init__()
        self.event1 = event1
        self.event2 = event2
        self.width = width
        self.colour = colour
        self.tags += ("line",)
        self.cur_loc_1: Location = event1
        self.cur_loc_2: Location = event2

    def place_on_canvas(
        self, canvas: Canvas, to_coordinates: Callable[[Location], Tuple[float, float]]
    ) -> None:
        """Place line on canvas.

        Args:
            canvas (Canvas): canvas
            to_coordinates (Callable[[float, float], Tuple[float,float]]): to_coordinates
        """
        super().place_on_canvas(canvas, to_coordinates)
        self.to_coordinates = to_coordinates
        c_1 = self.to_coordinates(self.cur_loc_1)
        c_2 = self.to_coordinates(self.cur_loc_2)
        self.canvas_object = canvas.create_line(
            *c_1, *c_2, fill=self.colour, width=self.width, tags=self.tags
        )

    def update(self, canvas: Canvas) -> None:
        """Update position of line."""
        if self.cur_shown:
            c_1 = self.to_coordinates(self.cur_loc_1)
            c_2 = self.to_coordinates(self.cur_loc_2)
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
        if start_time >= self.event2.time or end_time <= self.event1.time:
            self.hide(canvas)
        else:
            if self.event1.time < start_time:
                percentage = (start_time - self.event1.time) / (self.event2.time - self.event1.time)
                self.cur_loc_1 = self.event1.intermediate_point(self.event2, percentage)
            else:
                self.cur_loc_1 = self.event1
            if self.event2.time > end_time:
                percentage = (self.event2.time - end_time) / (self.event2.time - self.event1.time)
                self.cur_loc_2 = self.event2.intermediate_point(self.event1, percentage)
            else:
                self.cur_loc_2 = self.event2
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
        self.tags += ("lightning",)
        self.tags += (f"lightning {self.idx}",)

    def inspection_time_hr(self) -> Optional[float]:
        """Get the inspection time in hours."""
        if self.inspection_time is None:
            return None
        return (self.inspection_time - self.spawn_time) / DURATION_FACTORS["hr"]

    def suppression_time_hr(self) -> Optional[float]:
        """Get the suppression time in hours."""
        if self.suppressed_time is None:
            return None
        return (self.suppressed_time - self.spawn_time) / DURATION_FACTORS["hr"]

    def place_on_canvas(
        self, canvas: Canvas, to_coordinates: Callable[[Location], Tuple[float, float]]
    ) -> None:
        """place_on_canvas.

        Args:
            canvas (Canvas): canvas
            to_coordinates (Callable[[Location], Tuple[float, float]]): to_coordinates
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
        events: List[UpdateEvent],
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
        self.aircraft_point = GUIPoint(events[-1], radius=3, colour=point_colour)
        self.aircraft_lines: List[GUILine] = []
        last_event = events[0]
        for i, event in enumerate(events):
            if i == 0:
                continue
            if i == len(events) - 1:
                if event.lat - last_event.lat != 0 or event.lon - last_event.lon != 0:
                    self.aircraft_lines.append(GUILine(last_event, event, colour=line_colour))
            else:
                dx1 = event.lon - last_event.lon
                dy1 = event.lat - last_event.lat
                dx2 = events[i + 1].lon - event.lon
                dy2 = events[i + 1].lat - event.lat
                if dx1 == 0 and dy1 == 0:
                    last_event = event
                elif dx2 == 0 and dy2 == 0:
                    self.aircraft_lines.append(GUILine(last_event, event, colour=line_colour))
                    last_event = event  #
                elif abs(dx2 * dy1 - dx1 * dy2) > EPSILON:
                    self.aircraft_lines.append(GUILine(last_event, event, colour=line_colour))
                    last_event = event
        self.events = events
        super().__init__()

    def place_on_canvas(
        self, canvas: Canvas, to_coordinates: Callable[[Location], Tuple[float, float]]
    ) -> None:
        """Place aircraft on canvas.

        Args:
            canvas (Canvas): canvas
            to_coordinates (Callable[[Location], Tuple[float, float]]): to_coordinates
        """
        super().place_on_canvas(canvas, to_coordinates)
        self.aircraft_point.place_on_canvas(canvas, to_coordinates)

    def show_given_time(self, canvas: Canvas, start_time: float, end_time: float) -> None:
        """Show aircraft at given time.

        Args:
            canvas (Canvas): canvas
            start_time (float): start_time
            end_time (float): end_time
        """
        if end_time >= self.events[-1].time:
            self.aircraft_point.location = self.events[-1]
        for i, event in enumerate(self.events):
            if event.time >= end_time:
                if i == 0:
                    self.hide(canvas)
                else:
                    if event.lat == self.events[i - 1].lat and event.lon == self.events[i - 1].lon:
                        self.aircraft_point.location = event
                    else:
                        percentage = (end_time - self.events[i - 1].time) / (
                            event.time - self.events[i - 1].time
                        )
                        self.aircraft_point.location = self.events[i - 1].intermediate_point(
                            event, percentage
                        )
                    self.aircraft_point.update(canvas)
                break

        self.aircraft_point.show_given_time(canvas, start_time, end_time)

    def hide(self, canvas: Canvas) -> None:
        """Hide Aircraft.

        Args:
            canvas (Canvas): canvas
        """
        self.aircraft_point.hide(canvas)

    def update(self, canvas: Canvas) -> None:
        """Update aircraft.

        Args:
            canvas (Canvas): canvas
        """
        self.aircraft_point.update(canvas)


class GUIWaterBomber(GUIAircraft, WaterBomber):
    """GUI Water bomber class."""

    def __init__(
        self,
        events: List[UpdateEvent],
    ) -> None:
        """Initialise GUI water bomber."""
        super().__init__(events, "orange", "black")


class GUIUav(GUIAircraft, UAV):
    """GUI UAV class."""

    def __init__(
        self,
        events: List[UpdateEvent],
    ) -> None:
        """Initialise GUI UAV."""
        super().__init__(events, "green", "black")
