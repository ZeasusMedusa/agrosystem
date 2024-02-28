import cv2
from ultralytics import YOLO
from collections import defaultdict, namedtuple

# Используем namedtuple для определения структуры данных объекта с его характеристиками.
ObjectDetails = namedtuple(
    "ObjectDetails", ["class_name", "track_id", "box", "gps", "image_path"]
)


def process_images(images_path, model_path):
    """
    Processes all images in the specified directory using the YOLO model,
    supporting a variety of case-insensitive image formats.

    Parameters:
        - directory_path: str - Path to the directory with images.
        - model_path: str - Path to the model file (.pt) to use.

    Returns:
        - dict: A dictionary with objects, including the number of unique tracking identifiers per class and box details.
    """
    model = YOLO(model_path)
    unique_objects = defaultdict(set)

    for frame in images_path:
        results = model.track(frame, persist=True)
        for cls, track_id, box in zip(
            results[
                0
            ].boxes.cls,  # Class ID предполагаем, что это свойство результатов модели
            results[0]
            .boxes.id.int()
            .cpu()
            .tolist(),  # Track ID предполагаем, что это свойство результатов модели
            results[
                0
            ].boxes.xyxy,  # Bounding Box предполагаем, что это свойство результатов модели
        ):
            # Преобразуем bounding box к тьюплу для возможности сохранения в set
            box_tuple = tuple(box.cpu().tolist())
            class_name = results[0].names[int(cls)]
            # Создаем объект с деталями для сохранения в set
            object_details = ObjectDetails(
                class_name=class_name,
                track_id=track_id,
                box=box_tuple,
                gps=(0, 0),
                image_path=frame,
            )
            unique_objects[class_name].add(object_details)

    # Подготавливаем и возвращаем результат
    result = {
        class_name: {
            "count": len(
                set(obj.track_id for obj in track_ids)
            ),  # Количество уникальных track_id
            "objects": list(track_ids),  # Список уникальных объектов с их деталями
        }
        for class_name, track_ids in unique_objects.items()
    }

    return result


def process_video(video_path, model_path):
    """
    Processes video using the specified YOLO model to track objects.

    Parameters:
        - video_path: str - The path to the video file.
        - model_path: str - Path to the model file (.pt) to use.

    Returns:
        - dict: A dictionary with the number of unique tracking IDs for each class.
    """
    model = YOLO(model_path)
    cap = cv2.VideoCapture(video_path)
    unique_track_ids_by_class = defaultdict(set)

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        results = model.track(frame, persist=True)
        for cls, track_id in zip(
            results[0].boxes.cls, results[0].boxes.id.int().cpu().tolist()
        ):
            class_name = results[0].names[int(cls)]
            unique_track_ids_by_class[class_name].add(track_id)

    cap.release()
    return {
        class_name: len(track_ids)
        for class_name, track_ids in unique_track_ids_by_class.items()
    }


# def get_keypoints(img_path1, img_path2, model_path):
#     """
#     Obtaining keypoints for two images using the YOLO model.

#     Parameters:
#         - img_path1: str - Path to the first image.
#         - img_path2: str - Path to the second image.
#         - model_path: str - Path to the model file (.pt) to use.

#     Returns:
#         - dict: A dictionary with keys representing unique tracking identifiers, and values,
#                 representing the coordinates of the objects in the two images.
#     """
#     model = YOLO(model_path)
#     res1 = model.track(img_path1, persist=True)
#     res2 = model.track(img_path2, persist=True)
#     boxes1 = res1[0].boxes.cpu()
#     track_ids1 = res1[0].boxes.id.int().cpu().tolist()

#     boxes2 = res2[0].boxes.cpu()
#     track_ids2 = res2[0].boxes.id.int().cpu().tolist()

#     points1 = dict(zip(track_ids1, boxes1))
#     points2 = dict(zip(track_ids2, boxes2))

#     common_track_ids = set(track_ids1) & set(track_ids2)

#     result_dict = {}
#     for track_id in common_track_ids:
#         result_dict[track_id] = [
#             points1[track_id].xywh[0],
#             points2[track_id].xywh[0],
#             res1[0].names[int(points1[track_id].cls)],
#         ]

#     return result_dict
