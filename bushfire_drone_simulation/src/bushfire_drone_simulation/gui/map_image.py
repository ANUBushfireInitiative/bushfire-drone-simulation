"""Class for downloading and rendering a OSM map image."""

import os
from pathlib import Path
from typing import Any, Dict, Tuple

import geotiler
import PIL.Image
from geotiler.cache import caching_downloader
from geotiler.tile.io import fetch_tiles

cache_folder = Path(os.path.dirname(os.path.realpath(__file__))) / "map_tile_cache"
cache_folder.mkdir(parents=True, exist_ok=True)

session_cache: Dict[str, Any] = {}  # TODO(fix types) #pylint: disable=fixme


def get_from_cache(url: str):
    """Get image from cache.

    Returns None if image is not in the cache.

    Args:
        url (str): Image URL
    """
    url = url[9:].replace("/", "")
    if url in session_cache:
        return session_cache[url]
    if (cache_folder / url).is_file():
        image = open(cache_folder / url, "rb").read()
        session_cache[url] = image
        return image
    return None


def put_in_cache(url: str, image: bytes):
    """Put image in cache.

    Args:
        url (str): Image URL
        image (PIL.Image): Image
    """
    if image is not None:
        url = url[9:].replace("/", "")
        if url not in session_cache:
            session_cache[url] = image
        if not (cache_folder / url).is_file():
            image_file = open(cache_folder / url, "wb")
            image_file.write(image)
            image_file.close()


def downloader(tiles, num_workers: int):
    """Tile downloader.

    Args:
        tiles: Tiles to download
        num_workers (int): num_workers
    """
    return caching_downloader(get_from_cache, put_in_cache, fetch_tiles, tiles, num_workers)


def render_map(geotiler_map: geotiler.Map) -> PIL.Image.Image:
    """Render a geotiler map as an image.

    Args:
        geotiler_map:
    """
    return geotiler.render_map(geotiler_map, downloader=downloader)


class MapImage:
    """Class for downloading and rendering a OSM map image."""

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

        self.display_lat = latitude
        self.display_lon = longitude
        self.lat = latitude
        self.lon = longitude
        self.reload_required = True

        self.zoom = zoom

        self.display_image = PIL.Image.new("RGB", (width, height))

        self.left = 0
        self.top = 0

        self._fetch_image()

        self._update_image()

    def get_image(self):
        """Return map image to be displayed."""
        return self.display_image

    def _fetch_and_update(self):
        """_fetch_and_update."""
        self._fetch_image()
        self._update_image()

    def _fetch_image(self):
        """_fetch_image."""
        geotiler_map = geotiler.Map(
            center=(self.display_lon, self.display_lat),
            zoom=self.zoom,
            size=(self.width * 2, self.height * 2),
        )
        self.lat = self.display_lat
        self.lon = self.display_lon
        self.extent = geotiler_map.extent
        self.reload_required = False
        self.big_image: PIL.Image.Image = render_map(geotiler_map)
        self.left = int((self.big_image.size[0] - self.width) / 2)
        self.top = int((self.big_image.size[1] - self.height) / 2)

    def _update_image(self):
        """_update_image."""
        self.display_image.paste(self.big_image, (-self.left, -self.top))

    def move(self, dx: int, dy: int):
        """move.

        Args:
            dx (int): dx
            dy (int): dy
        """
        self.top = self._constrain(self.top, dy, self.big_image.height - self.height)
        self.left = self._constrain(self.left, dx, self.big_image.width - self.width)
        self.display_lat = (self.top + int(self.height / 2)) * (self.extent[1] - self.extent[3]) / (
            self.big_image.height
        ) + self.extent[3]
        self.display_lon = (self.left + int(self.width / 2)) * (self.extent[2] - self.extent[0]) / (
            self.big_image.width
        ) + self.extent[0]
        if self.reload_required:
            self._fetch_and_update()
        else:
            self._update_image()

    def change_zoom(self, zoom: int):
        """change_zoom.

        Args:
            zoom (int): zoom
        """
        self.zoom = zoom
        self._fetch_and_update()

    def _constrain(self, old: int, change: int, max_value: int):
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
