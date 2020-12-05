"""GUI Module for bushfire drone simulation."""

import tkinter


def start_gui():
    """Start a basic GUI version of the drone simulation."""
    window = tkinter.Tk()

    window.title("ANU Bushfire Initiative Drone Simulation")

    title = tkinter.Label(window, text="ANU Bushfire Initiative Drone Simulation")
    title.pack()

    window.mainloop()
