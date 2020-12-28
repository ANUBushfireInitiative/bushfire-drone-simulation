"""GUI Module for bushfire drone simulation."""

import tkinter

import geotiler
from PIL import ImageTk

from bushfire_drone_simulation.aircraft import UAV, WaterBomber
from bushfire_drone_simulation.fire_utils import Location, WaterTank
from bushfire_drone_simulation.lightning import Lightning


def create_point_from_elm(canvas_name, element: Location, rad=5):  # center coordinates, radius
    """Create a point given an element extending Location."""
    x, y = element.to_coordinates()
    # print(type(x))
    # print(type(rad))
    canvas_name.create_oval(x - rad, y - rad, x + rad, y + rad, fill=type_to_colour(element))


def connect_points(canvas_name, p_1: Location, p_2: Location):
    """Connect two points with a line."""
    canvas_name.create_line(
        p_1.to_coordinates(), p_2.to_coordinates(), fill=type_to_colour(p_1), width=2
    )
    # Could be type_to_colour(p1) in future


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


def start_gui(coordinator, lightning):
    """Start a basic GUI version of the drone simulation."""
    window = tkinter.Tk()

    window.title("ANU Bushfire Initiative Drone Simulation")
    canvas = tkinter.Canvas(window, width=800, height=800)
    for strike in lightning:
        create_point_from_elm(canvas, strike)
    for tank in coordinator.water_tanks:
        create_point_from_elm(canvas, tank)
    for uav in coordinator.uavs:
        for (idx, past_loc) in enumerate(uav.past_locations):
            if idx != 0:
                connect_points(canvas, past_loc, uav.past_locations[idx - 1])
        create_point_from_elm(canvas, uav, rad=3)
    for base in coordinator.uav_bases:
        create_point_from_elm(canvas, base, rad=2)
    for water_bomber_type in coordinator.water_bombers_dict:
        for base in coordinator.water_bomber_bases_dict[water_bomber_type]:
            create_point_from_elm(canvas, base, rad=2)
        for water_bomber in coordinator.water_bombers_dict[water_bomber_type]:
            for (idx, past_loc) in enumerate(water_bomber.past_locations):
                if idx != 0:
                    connect_points(canvas, past_loc, water_bomber.past_locations[idx - 1])
                create_point_from_elm(canvas, water_bomber, rad=3)

    canvas.pack()

    title = tkinter.Label(window, text="ANU Bushfire Initiative Drone Simulation")
    title.pack()

    window.mainloop()


def start_map_gui():
    """Start a basic GUI version of the drone simulation."""
    window = tkinter.Tk()

    window.title("ANU Bushfire Initiative Drone Simulation")
    canvas = tkinter.Canvas(window, width=800, height=800)
    canvas.pack()

    title = tkinter.Label(window, text="ANU Bushfire Initiative Drone Simulation")
    title.pack()

    print(window.winfo_screenwidth(), title.winfo_width(), "!!!!!!!!!!!!!!!!!!!")
    map_object = geotiler.Map(extent=(149, -35, 150, -36), size=(800, 800))
    print(map_object.extent)
    image = geotiler.render_map(map_object)
    image.save("map.png")
    map_image = ImageTk.PhotoImage(image)
    canvas.create_image(0, 0, anchor="nw", image=map_image)

    window.mainloop()
