"""Map downloader."""

import math
import os
from io import BytesIO
from pathlib import Path
from typing import Dict, Optional, Tuple

import grequests
from PIL import Image as img
from PIL.Image import Image

from bushfire_drone_simulation.fire_utils import Coordinate, Location

TILE_RESOLUTION = 256

cache_folder = Path(os.path.dirname(os.path.realpath(__file__))) / "map_tile_cache"
cache_folder.mkdir(parents=True, exist_ok=True)

session_cache: Dict[str, Image] = {}  # type: ignore


def url_to_filename(url: str) -> str:
    """Convert a tile url to a filename.

    Args:
        url (str): url

    Returns:
        str: Filename
    """
    return url[8:].replace("/", "-").split("?")[0]


def check_in_cache(url: str) -> bool:
    """Check if a tile is in the cache."""
    url = url_to_filename(url)
    return url in session_cache or (cache_folder / url).is_file()


def get_from_cache(url: str) -> Optional[Image]:  # type: ignore
    """Get image from cache.

    Returns None if image is not in the cache.

    Args:
        url (str): Image URL
    """
    url = url_to_filename(url)
    if url in session_cache:
        return session_cache[url]
    if (cache_folder / url).is_file():
        image = img.open(cache_folder / url)
        session_cache[url] = image
        return image
    return None


def put_in_cache(url: str, image: Image) -> None:  # type: ignore
    """Put image in cache.

    Args:
        url (str): Image URL
        image (PIL.Image): Image
    """
    url = url_to_filename(url)
    if url not in session_cache:
        session_cache[url] = image
    if not (cache_folder / url).is_file():
        image.save(cache_folder / url)


def get_pixel_coordinates(
    lat: float, lon: float, zoom: int, tile_resolution: int = TILE_RESOLUTION
) -> Tuple[int, int]:
    """Get pixel coordinates from within a tile.

    Args:
        lat (float): lat
        lon (float): lon
        zoom (int): zoom
        tile_resolution (int): tile_resolution

    Returns:
        Tuple[int, int]: Pixel coordinates in tile
    """
    x = (lon + 180.0) / 360.0 * (2**zoom)
    y = (
        1.0 - math.log(math.tan(math.radians(lat)) + (1 / math.cos(math.radians(lat)))) / math.pi
    ) * (2 ** (zoom - 1))
    return (
        int(x * tile_resolution) - int(x) * tile_resolution,
        int(y * tile_resolution) - int(y) * tile_resolution,
    )


def get_tile_coordinates(lat: float, lon: float, zoom: int) -> Tuple[int, int]:
    """Get tile coordinates for a given latitude, longitude and zoom.

    Args:
        lat (float): lat
        lon (float): lon
        zoom (int): zoom

    Returns:
        Tuple[int, int]: Tile coordinates
    """
    x = int((lon + 180.0) / 360.0 * (2**zoom))
    y = int(
        (1.0 - math.log(math.tan(math.radians(lat)) + (1 / math.cos(math.radians(lat)))) / math.pi)
        * (2 ** (zoom - 1))
    )
    return (x, y)


def get_lat_lon_from_tile(x: float, y: float, zoom: int) -> Tuple[float, float]:
    """Get latitude/longitude location from tile coordinates.

    Args:
        x (float): x
        y (float): y
        zoom (int): zoom

    Returns:
        Tuple[float, float]: Lat/lon of upper left corner of specified tile
    """
    lon = x / (2**zoom) * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - y / (2 ** (zoom - 1))))))
    return (lat, lon)


def tile_url(
    x: int,
    y: int,
    zoom: int,
    url_format: str = (
        "https://tile.thunderforest.com/landscape/{0}/{1}/{2}.png"
        "?apikey=a23b2993d681459ab05e842441583e4b"
    ),
) -> str:
    """Convert tile coordinates to url.

    Args:
        x (int): x
        y (int): y
        zoom (int): zoom
        url_format (str): url_format

    Returns:
        str: Url
    """
    x = x % (2**zoom)
    y = y % (2**zoom)
    return url_format.format(zoom, x, y)


class MapDownloader:
    """Class to manage downloading collection of map tiles to form a map."""

    def __init__(self) -> None:
        """Initialise map downloader."""
        self.zoom = 0
        self.min_tile_x, self.min_tile_y = 0, 0
        self.max_tile_x, self.max_tile_y = 0, 0

    def download_map(  # type: ignore
        self, zoom: int, centre: Location, min_width: int, min_height: int
    ) -> Image:
        """Download a map.

        Args:
            zoom (int): Zoom level
            centre (Location): Latitude and longitude of map "centre"
            min_width (int): Minimum width of map
            min_height (int): Minimum height of map

        Returns:
            Image: Downloaded map
        """
        self.zoom = zoom

        centre_tile_coordinates = get_tile_coordinates(centre.lat, centre.lon, zoom)
        centre_pixel = get_pixel_coordinates(centre.lat, centre.lon, zoom)
        self.min_tile_x = centre_tile_coordinates[0] - math.ceil(
            ((min_width / 2) - centre_pixel[0]) / TILE_RESOLUTION
        )
        self.min_tile_y = centre_tile_coordinates[1] - math.ceil(
            ((min_height / 2) - centre_pixel[1]) / TILE_RESOLUTION
        )
        self.max_tile_x = (
            centre_tile_coordinates[0]
            + 1
            + math.ceil(((min_width / 2) + centre_pixel[0] - TILE_RESOLUTION) / TILE_RESOLUTION)
        )
        self.max_tile_y = (
            centre_tile_coordinates[1]
            + 1
            + math.ceil(((min_height / 2) + centre_pixel[1] - TILE_RESOLUTION) / TILE_RESOLUTION)
        )

        width = (self.max_tile_x - self.min_tile_x) * TILE_RESOLUTION
        height = (self.max_tile_y - self.min_tile_y) * TILE_RESOLUTION
        big_image = img.new("RGB", (width, height))
        requests = []
        for tile_x in range(self.min_tile_x, self.max_tile_x):
            for tile_y in range(self.min_tile_y, self.max_tile_y):
                url = tile_url(tile_x, tile_y, zoom)
                if not check_in_cache(url):
                    requests.append(grequests.get(url, timeout=1))

        images = grequests.map(requests)

        i = 0
        for tile_x in range(self.min_tile_x, self.max_tile_x):
            for tile_y in range(self.min_tile_y, self.max_tile_y):
                url = tile_url(tile_x, tile_y, zoom)
                tile_img = get_from_cache(url)
                if tile_img is None:
                    if images[i] is None:
                        tile_img = img.new(
                            "RGB", (TILE_RESOLUTION, TILE_RESOLUTION), (255, 255, 255)
                        )
                    else:
                        tile_img = img.open(BytesIO(images[i].content))
                        put_in_cache(url, tile_img)
                    i += 1
                big_image.paste(
                    tile_img,
                    box=(
                        (tile_x - self.min_tile_x) * TILE_RESOLUTION,
                        (tile_y - self.min_tile_y) * TILE_RESOLUTION,
                    ),
                )

        return big_image

    def get_location_from_pixel(self, pixel: Coordinate) -> Location:
        """Get latitude and longitude of specific pixel in downloaded map.

        Args:
            pixel (Coordinate): Pixel coordinates

        Returns:
            Location: Latitude and longitude of pixel in map
        """
        lat, lon = get_lat_lon_from_tile(
            pixel.x / TILE_RESOLUTION + self.min_tile_x,
            pixel.y / TILE_RESOLUTION + self.min_tile_y,
            self.zoom,
        )
        return Location(lat, lon)

    def get_pixel_from_location(self, loc: Location) -> Coordinate:
        """Get pixel coordinates on map of specific lat/lon.

        Args:
            loc (Location): Latitude and longitude

        Returns:
            Coordinate: Pixel coordinates of location on map
        """
        x, y = get_pixel_coordinates(loc.lat, loc.lon, self.zoom)
        tile_x, tile_y = get_tile_coordinates(loc.lat, loc.lon, self.zoom)
        return Coordinate(
            x + TILE_RESOLUTION * (tile_x - self.min_tile_x),
            y + TILE_RESOLUTION * (tile_y - self.min_tile_y),
        )

    def get_extent(self) -> Tuple[Location, Location]:
        """Get lat/lon extent of downloaded map.

        Returns:
            Tuple[Location, Location]: Lat/lon of upper left and lower right map corner
        """
        return (
            Location(*get_lat_lon_from_tile(self.min_tile_x, self.min_tile_y, self.zoom)),
            Location(*get_lat_lon_from_tile(self.max_tile_x, self.max_tile_y, self.zoom)),
        )
