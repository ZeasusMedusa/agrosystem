import math
import numpy as np
from PIL import Image
import exif
import rasterio
from rasterio.merge import merge
from rasterio.transform import from_origin
import os
from pyproj import Geod
import pyexiv2
from osgeo import gdal


class GeoTIFFCreator:
    """Class for creating a GeoTIFF mosaic from a set of images with GPS data and relative altitude"""

    def __init__(self, image_paths, output_path, obj_counter, hfov_degrees=67):
        """Initialize GeoTIFFCreator

        Args:
            image_paths (list): List of image file paths (e.g. ['/path/to/image1.jpg', '/path/to/image2.jpg'])
            output_path (str): Path to output GeoTIFF file (e.g. /path/to/output.tif)
            hfov_degrees (float): Horizontal field of view in degrees

        Description:
            The GeoTIFFCreator class creates a GeoTIFF mosaic from a set of images with GPS data and relative altitude.
        """
        self.image_paths = image_paths
        self.output_path = output_path
        self.hfov = math.radians(hfov_degrees)
        self.geod = Geod(ellps="WGS84")
        self.obj_counter = obj_counter

    def calc_gps(self, obj_counter, geotiff_files):
        for geotiff_file in geotiff_files:
            geotiff_filename = os.path.basename(geotiff_file)
            geotiff_filename_no_ext = os.path.splitext(geotiff_filename)[0]

            for class_name in obj_counter:
                for i, obj in enumerate(obj_counter[class_name]["objects"]):
                    obj_filename = os.path.basename(obj.image_path)
                    obj_filename_no_ext = os.path.splitext(obj_filename)[0]

                    # Проверяем, соответствует ли geotiff_file изображению объекта
                    if geotiff_filename_no_ext == f"temp_{obj_filename_no_ext}":
                        x, y = (obj.box[2] + obj.box[0]) / 2, (obj.box[3] + obj.box[1]) / 2

                        lat, lon = self.pixel_to_coord(geotiff_file, x, y)

                        # Создаем новый экземпляр с обновленным GPS
                        new_obj = obj._replace(gps=(lat, lon))
                        # Обновляем объект в списке
                        obj_counter[class_name]["objects"][i] = new_obj

        return obj_counter


    def pixel_to_coord(self, geotiff_file, x, y):
        # Открыть GeoTIFF файл
        dataset = gdal.Open(geotiff_file)

        # Получить геопреобразование
        transform = dataset.GetGeoTransform()

        # Получить координаты
        x_coord = transform[0] + x * transform[1] + y * transform[2]
        y_coord = transform[3] + x * transform[4] + y * transform[5]

        return (y_coord, x_coord)
    def get_temp_tif_path(self, jpg_path):
        """Get temporary tif file path

        Args:
            jpg_path (str): Path to image file (e.g. /path/to/image.jpg)

        Returns:
            str: Temporary tif file path (e.g. temp_image.tif)

        Description:
            The get_temp_tif_path method returns a temporary tif file path for the given image file path.
        """
        base_name = os.path.basename(jpg_path)
        name_without_ext = os.path.splitext(base_name)[0]
        temp_output_path = f"temp_{name_without_ext}.tif"
        return temp_output_path

    def create_mosaic(self):
        """Create a GeoTIFF mosaic from a set of images with GPS data and relative altitude"""
        src_files_to_mosaic = []
        temp_files = []

        for jpg_path in self.image_paths:
            (
                center_lat,
                center_lon,
                pixel_width,
                pixel_height,
                image_width,
                image_height,
            ) = self.process_image(jpg_path)
            if center_lat is None or center_lon is None:
                continue

            temp_output_path = self.get_temp_tif_path(jpg_path)
            temp_files.append(temp_output_path)
            self.create_geotiff(
                jpg_path,
                temp_output_path,
                center_lat,
                center_lon,
                pixel_width,
                pixel_height,
                image_width,
                image_height,
            )
            src_files_to_mosaic.append(rasterio.open(temp_output_path))

        mosaic, out_trans = merge(src_files_to_mosaic)
        out_meta = src_files_to_mosaic[0].meta.copy()
        out_meta.update(
            {
                "driver": "GTiff",
                "height": mosaic.shape[1],
                "width": mosaic.shape[2],
                "transform": out_trans,
            }
        )

        with rasterio.open(self.output_path, "w", **out_meta) as dest:
            dest.write(mosaic)

        obj_counter = self.calc_gps(self.obj_counter, temp_files)

        for src in src_files_to_mosaic:
            src.close()
        for temp_file in temp_files:
            os.remove(temp_file)
        return self.output_path, obj_counter

    def process_image(self, img_path):
        """Process image to get GPS data and pixel size in degrees and image dimensions

        Args:
            img_path (str): Path to image file (e.g. /path/to/image.jpg)

        Returns:
            tuple: center_lat, center_lon, pixel_width, pixel_height, image_width, image_height

        Description:
            The process_image method processes the image to get GPS data and pixel size in degrees and image dimensions.
        """
        center_lat, center_lon = self.get_gps(img_path)
        h = self.get_relative_alt(img_path)
        if h is None:
            return None, None, None, None, None, None

        image = Image.open(img_path)
        image_dims = image.size
        pixel_width, pixel_height = self.calc_pixel_size_degrees(
            h, center_lat, center_lon, image_dims
        )
        return (
            center_lat,
            center_lon,
            pixel_width,
            pixel_height,
            image_dims[0],
            image_dims[1],
        )

    def get_gps(self, img_path):
        """Get GPS coordinates from image EXIF data

        Args:
            img_path (str): Path to image file (e.g. /path/to/image.jpg)

        Returns:
            tuple: latitude, longitude

        Description:
            The get_gps method gets GPS coordinates from image EXIF data.
        """
        try:
            with open(img_path, "rb") as f:
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
            print(f"Error getting GPS data from {img_path}: {e}")
            return None, None

    def get_relative_alt(self, img_path):
        """Get relative altitude from image XMP data

        Args:
            img_path (str): Path to image file (e.g. /path/to/image.jpg)

        Returns:
            float: Relative altitude

        Description:
            The get_relative_alt method gets relative altitude from image XMP data.
        """
        try:
            metadata = pyexiv2.Image(img_path)
            xmp_metadata = metadata.read_xmp()
            return float(xmp_metadata.get("Xmp.drone-dji.RelativeAltitude", 0))
        except Exception as e:
            print(f"Error getting altitude from {img_path}: {e}")
            return None


    def calc_pixel_size_meters(self, h, image_dims):
        """Calculate the size of a pixel in meters

        Args:
            h (float): Relative altitude
            image_dims (tuple): Image dimensions (width, height)

        Returns:
            tuple: Size of a pixel in meters (width, height)
        """
        # Расчет ширины области обзора на земле в метрах
        ground_width = 2 * math.tan(self.hfov / 2) * h

        # Аспектное соотношение изображения
        aspect_ratio = image_dims[0] / image_dims[1]

        # Расчет вертикального угла обзора (VFOV) на основе HFOV и аспектного соотношения
        vfov = 2 * math.atan(math.tan(self.hfov / 2) / aspect_ratio)

        # Расчет высоты области обзора на земле в метрах
        ground_height = 2 * math.tan(vfov / 2) * h

        # Расчет размера пикселя в метрах для ширины и высоты
        pixel_size_width = ground_width / image_dims[0]
        pixel_size_height = ground_height / image_dims[1]

        return pixel_size_width, pixel_size_height

    def calc_pixel_size_degrees(self, h, center_lat, center_lon, image_dims):
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
        pixel_size_width_meters, pixel_size_height_meters = self.calc_pixel_size_meters(h, image_dims)

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

    def create_geotiff(
        self,
        jpg_path,
        output_path,
        center_lat,
        center_lon,
        pixel_width,
        pixel_height,
        image_width,
        image_height,
    ):
        """Create GeoTIFF file from image

        Args:
            jpg_path (str): Path to image file (e.g. /path/to/image.jpg)
            output_path (str): Path to output GeoTIFF file (e.g. /path/to/output.tif)
            center_lat (float): Center latitude
            center_lon (float): Center longitude
            pixel_width (float): Pixel width in degrees
            pixel_height (float): Pixel height in degrees
            image_width (int): Image width
            image_height (int): Image height

        Description:
            The create_geotiff method creates a GeoTIFF file from the given image file.
        """
        img = Image.open(jpg_path)
        data = np.array(img)

        transform = from_origin(
            center_lon - pixel_width * image_width / 2,
            center_lat + pixel_height * image_height / 2,
            pixel_width,
            pixel_height,
        )

        with rasterio.open(
            output_path,
            "w",
            driver="GTiff",
            height=image_height,
            width=image_width,
            count=data.shape[2] if len(data.shape) > 2 else 1,
            dtype=data.dtype,
            crs="+proj=latlong",
            transform=transform,
        ) as dst:
            if data.shape[2] and len(data.shape) > 2:  # For RGB images
                for i in range(data.shape[2]):
                    dst.write(data[:, :, i], i + 1)
            else:  # For grayscale images
                dst.write(data, 1)
