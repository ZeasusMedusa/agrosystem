import math
from PIL import Image
import exif
import pyexiv2
from rasterio.transform import from_origin
from pyproj import Geod

class ImageGPSCoordinateCalculator:
    """Class for calculating GPS coordinates from image coordinates"""

    def __init__(self, img_path, hfov_degrees=67):
        """Initialize ImageGPSCoordinateCalculator

        Args:
            img_path (str): Path to the image file (e.g. '/path/to/image.jpg')
            hfov_degrees (float): Horizontal field of view in degrees
        """
        self.img_path = img_path
        self.hfov = math.radians(hfov_degrees)  # Преобразуем угол в радианы
        self.geod = Geod(ellps="WGS84")

        # Используем ранее определенные методы для получения этих значений
        self.center_lat, self.center_lon = self.get_gps()
        self.h = self.get_relative_alt()
        self.image = Image.open(img_path)
        self.image_dims = self.image.size

    def get_gps_coordinate(self, x, y):
        """Get GPS coordinates from image coordinates

        Args:
            x (int): X-coordinate of the point on the image
            y (int): Y-coordinate of the point on the image

        Returns:
            lat (float): Latitude
            lon (float): Longitude

        Description:
            The method calculates the GPS coordinates of the point on the image
            based on the image center GPS coordinates, flight altitude and camera rotation angle
        """
        # Расчет размера пикселя в метрах на изображении
        pixel_size_width, pixel_size_height = self.calc_pixel_size_degrees(self.h, self.center_lat, self.center_lon)
        transform = from_origin(
            self.center_lon - pixel_size_width * self.image_dims[0] / 2,
            self.center_lat + pixel_size_height * self.image_dims[1] / 2,
            pixel_size_width,
            pixel_size_height,
        )
        new_lat, new_lon = self.pixel_to_gps(x, y, transform)

        return new_lat, new_lon

    def calc_pixel_size_meters(self):
        """Calculate the size of a pixel in meters

        Returns:
            pixel_size_width (float): Size of a pixel in meters (width)
            pixel_size_height (float): Size of a pixel in meters (height)

        Description:
            The method calculates the size of a pixel in meters based on the image dimensions,
            flight altitude and camera field of view.
        """
        # Расчет ширины области обзора на земле в метрах
        ground_width = 2 * math.tan(self.hfov / 2) * self.h

        # Аспектное соотношение изображения
        aspect_ratio = self.image_dims[0] / self.image_dims[1]

        # Расчет вертикального угла обзора (VFOV) на основе HFOV и аспектного соотношения
        vfov = 2 * math.atan(math.tan(self.hfov / 2) / aspect_ratio)

        # Расчет высоты области обзора на земле в метрах
        ground_height = 2 * math.tan(vfov / 2) * self.h

        # Расчет размера пикселя в метрах для ширины и высоты
        pixel_size_width = ground_width / self.image_dims[0]
        pixel_size_height = ground_height / self.image_dims[1]

        return pixel_size_width, pixel_size_height

    def calc_pixel_size_degrees(self, h, center_lat, center_lon):
        """Calculate the size of a pixel in degrees

        Args:
            h (float): Relative altitude
            center_lat (float): Center latitude
            center_lon (float): Center longitude
            image_dims (tuple): Image dimensions (width, height)

        Returns:
            tuple: Size of a pixel in degrees (width, height)
        """
        # Рассчитываем размер пикселя в метрах
        pixel_size_width_meters, pixel_size_height_meters = self.calc_pixel_size_meters()

        # Преобразуем размер пикселя из метров в градусы
        _, _, distance_w = self.geod.inv(
            center_lon, center_lat, center_lon + 0.001, center_lat
        )
        _, _, distance_h = self.geod.inv(
            center_lon, center_lat, center_lon, center_lat + 0.001
        )
        meters_per_degree_lon = distance_w / 0.001
        meters_per_degree_lat = distance_h / 0.001

        pixel_size_width_degrees = pixel_size_width_meters / meters_per_degree_lon
        pixel_size_height_degrees = pixel_size_height_meters / meters_per_degree_lat

        return pixel_size_width_degrees, pixel_size_height_degrees

    def pixel_to_gps(self, x, y, transform):
        """
        Преобразование пиксельных координат (x, y) в географические координаты (широта, долгота).

        Args:
            x (int): X-координата пикселя.
            y (int): Y-координата пикселя.
            transform (Affine): Трансформация, используемая для преобразования координат.

        Returns:
            tuple: Координаты (широта, долгота) для пикселя.
        """

        # Применяем трансформацию для получения географических координат
        lon, lat = transform * (x, y)
        return lat, lon


    def get_gps(self):
        """Get GPS coordinates from image EXIF data

        Args:
            img_path (str): Path to image file (e.g. /path/to/image.jpg)

        Returns:
            tuple: latitude, longitude

        Description:
            The get_gps method gets GPS coordinates from image EXIF data.
        """
        try:
            with open(self.img_path, "rb") as f:
                my_image = exif.Image(f)
                lat = (
                    my_image.gps_latitude[0]
                    + my_image.gps_latitude[1] / 60
                    + my_image.gps_latitude[2] / 3600
                )
                lon = (
                    my_image.gps_longitude[0]
                    + my_image.gps_longitude[1] / 60
                    + my_image.gps_longitude[2] / 3600
                )
            return lat, lon
        except Exception as e:
            print(f"Error getting GPS data from {self.img_path}: {e}")
            return None, None

    def get_relative_alt(self):
        """Get relative altitude from image XMP data

        Args:
            img_path (str): Path to image file (e.g. /path/to/image.jpg)

        Returns:
            float: Relative altitude

        Description:
            The get_relative_alt method gets relative altitude from image XMP data.
        """
        try:
            metadata = pyexiv2.Image(self.img_path)
            xmp_metadata = metadata.read_xmp()
            return float(xmp_metadata.get("Xmp.drone-dji.RelativeAltitude", 0))
        except Exception as e:
            print(f"Error getting altitude from {self.img_path}: {e}")
            return None