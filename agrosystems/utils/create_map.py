from .gps_calculate import ImageGPSCoordinateCalculator
from .map_creator import GeoTIFFCreator
from .obj_counter import process_images


def start_processing(images_path, model_path, output_path="test.tif", hfov_degrees=67):
    try:
        obj_counter = process_images(images_path, model_path)
        # obj_counter = calc_gps(obj_counter)

        _, obj_counter = GeoTIFFCreator(images_path, output_path, obj_counter, hfov_degrees).create_mosaic()
        status = "Complete"
    except Exception:
        status = "Error"
        obj_counter = None
        output_path = None
    return obj_counter, output_path, status

