"""Class for downloading and rendering a OSM map image."""

from typing import Tuple

import PIL.Image
from PIL.Image import Image

from bushfire_drone_simulation.fire_utils import Location
from bushfire_drone_simulation.gui.map_downloader import MapDownloader


class MapImage:
    """Class for rendering subset of a downloaded map image."""

    def __init__(self, dimensions: Tuple[int, int], latitude: float, longitude: float, zoom: int):
        """__init__.

        Args:
            height (int): height
            width (int): width
            latitude (float): latitude
            longitude (float): longitude
            zoom (int): zoom
        """
        width = dimensions[0]
        height = dimensions[1]
        self.height = height
        self.width = width

        self.display_loc = Location(latitude, longitude)
        self.lat = latitude
        self.lon = longitude
        self.reload_required = True

        self.zoom = zoom

        self.display_image = PIL.Image.new("RGB", (width, height))
        self.big_image = PIL.Image.new("RGB", (0, 0))
        self.map_downloader = MapDownloader()

        self.left = 0
        self.top = 0

        self._fetch_and_update()

    def set_size(self, width: int, height: int) -> None:
        """Set size of map image.

        Args:
            width (int): width
            height (int): height
        """
        self.width = width
        self.height = height
        self.display_image = PIL.Image.new("RGB", (width, height))
        self._fetch_and_update()

    def get_image(self) -> Image:  # type: ignore[no-any-unimported]
        """Return map image to be displayed."""
        return self.display_image

    def _fetch_and_update(self) -> None:
        """_fetch_and_update."""
        self._fetch_image()
        self._update_image()

    def _fetch_image(self) -> None:
        """_fetch_image."""
        self.big_image = self.map_downloader.download_map(
            self.zoom,
            self.display_loc,
            self.width + 250,
            self.height + 250,
        )
        self.lat = self.display_loc.lat
        self.lon = self.display_loc.lon
        self.reload_required = False
        middle = self.map_downloader.get_pixel_from_location(self.display_loc)
        self.left = middle.x - int(self.width / 2)
        self.top = middle.y - int(self.height / 2)

    def get_coordinates(self, location: Location) -> Tuple[int, int]:
        """Get pixel coordinates on the map image from a latitude and longitude.

        Args:
            latitude (float): latitude
            longitude (float): longitude

        Returns:
            Tuple[int, int]: Pixel coordinates
        """
        big_coord = self.map_downloader.get_pixel_from_location(location)
        return big_coord.x - self.left, big_coord.y - self.top

    def _update_image(self) -> None:
        """_update_image."""
        self.display_image.paste(self.big_image, (-self.left, -self.top))

    def move(self, dx: int, dy: int) -> None:
        """move.

        Args:
            dx (int): dx
            dy (int): dy
        """
        self.top = self._constrain(self.top, dy, self.big_image.height - self.height)
        self.left = self._constrain(self.left, dx, self.big_image.width - self.width)
        extent = self.map_downloader.get_extent()
        self.display_loc.lat = (self.top + int(self.height / 2)) * (
            extent[1].lat - extent[0].lat
        ) / (self.big_image.height) + extent[0].lat
        self.display_loc.lon = (self.left + int(self.width / 2)) * (
            extent[1].lon - extent[0].lon
        ) / (self.big_image.width) + extent[0].lon
        if self.reload_required:
            self._fetch_and_update()
        else:
            self._update_image()

    def change_zoom(self, zoom: int) -> None:
        """change_zoom.

        Args:
            zoom (int): zoom
        """
        self.zoom = zoom
        self._fetch_and_update()

    def _constrain(self, old: int, change: int, max_value: int) -> int:
        """_constrain.

        Args:
            old (int): old
            change (int): change
            max_value (int): max_value
        """
        new = old + change
        if 0 < new < max_value:
            return new
        self.reload_required = True
        return old
