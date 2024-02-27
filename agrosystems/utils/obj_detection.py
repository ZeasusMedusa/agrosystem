from ultralytics import YOLO


def detect_objects(image_path, model_path):
    """
    Performs object detection in the image using the YOLOv8 model and returns the coordinates,
    bounding boxes, center coordinates, and class of each detected object.

    Parameters:
        - image_path: str - The path to the image to be detected.
        - model_path: str - The path to the YOLOv8 model file (.pt).

    Returns:
        - detections: list of dictionaries with the center coordinates (x, y), class, confidence and bounding box (bbox) of each detected object.
    """
    # Model loading
    model = YOLO(model_path)

    # Image loading and processing
    results = model.predict(image_path)[0]

    # Extracting detection results from the results object
    detections = []
    for box in results.boxes.cpu():
        x1, y1, x2, y2 = box.xyxy.tolist()[0]
        conf = box.conf.tolist()[0]
        cls = int(box.cls)
        class_name = results.names[cls]
        x = x1 + (x2 - x1) / 2
        y = y1 + (y2 - y1) / 2
        detections.append(
            {
                "class": class_name,
                "confidence": conf,
                "bbox": (int(x1), int(y1), int(x2), int(y2)),
                "xy": (int(x), int(y)),  # Center coordinates
            }
        )

    return detections
