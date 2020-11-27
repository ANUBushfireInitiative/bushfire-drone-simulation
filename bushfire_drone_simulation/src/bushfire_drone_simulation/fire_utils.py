"""Various classes and functions useful to the bushfire_drone_simulation application."""

# class Point:  # pylint: disable=too-few-public-methods
#     """Point class holding a pair of x-y coordinates."""

#     def __init__(self, x: int, y: int):
#         """Initialise point coordinates."""
#         self.x = x
#         self.y = y


class Location:  # pylint: disable=too-few-public-methods
    """Location class storing postion in worldwide latitude and longitude coordinates."""

    def __init__(self, latitude: float, longitude: float):
        """Initialise location from latitude and longitude coordinates."""
        self.lat = latitude
        self.lon = longitude

    @classmethod
    def from_coordinates(cls, x: int, y: int):
        """Initialise location from pixel coordinates."""
        location = cls(x, y)
        # FIXME(not converting coordinates to lat lon)  # pylint: disable=fixme
        return location
