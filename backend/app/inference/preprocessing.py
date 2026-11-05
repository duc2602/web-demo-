"""Prepare phone photos of documents for image-restoration inference."""

import cv2
import numpy as np

MAX_DETECTION_DIMENSION = 1000


def _order_corners(points: np.ndarray) -> np.ndarray:
    points = points.reshape(4, 2).astype(np.float32)
    sums = points.sum(axis=1)
    differences = np.diff(points, axis=1).reshape(4)
    return np.array(
        [
            points[np.argmin(sums)],
            points[np.argmin(differences)],
            points[np.argmax(sums)],
            points[np.argmax(differences)],
        ],
        dtype=np.float32,
    )


def _find_document_corners(image_rgb: np.ndarray) -> np.ndarray | None:
    height, width = image_rgb.shape[:2]
    scale = min(1.0, MAX_DETECTION_DIMENSION / max(height, width))
    if scale < 1:
        detection_image = cv2.resize(
            image_rgb,
            (round(width * scale), round(height * scale)),
            interpolation=cv2.INTER_AREA,
        )
    else:
        detection_image = image_rgb
    scale_x = detection_image.shape[1] / width
    scale_y = detection_image.shape[0] / height

    gray = cv2.cvtColor(detection_image, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = detection_image.shape[0] * detection_image.shape[1]

    for contour in sorted(contours, key=cv2.contourArea, reverse=True):
        if cv2.contourArea(contour) < image_area * 0.1:
            break
        perimeter = cv2.arcLength(contour, True)
        corners = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(corners) == 4 and cv2.isContourConvex(corners):
            corners = _order_corners(corners)
            corners[:, 0] /= scale_x
            corners[:, 1] /= scale_y
            return corners
    return None


def _find_documents(image_rgb: np.ndarray) -> list[np.ndarray]:
    height, width = image_rgb.shape[:2]
    scale = min(1.0, MAX_DETECTION_DIMENSION / max(height, width))
    if scale < 1:
        detection_image = cv2.resize(
            image_rgb,
            (round(width * scale), round(height * scale)),
            interpolation=cv2.INTER_AREA,
        )
    else:
        detection_image = image_rgb
    scale_x = detection_image.shape[1] / width
    scale_y = detection_image.shape[0] / height
    gray = cv2.cvtColor(detection_image, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    minimum_area = detection_image.shape[0] * detection_image.shape[1] * 0.02

    candidates: list[tuple[float, np.ndarray, tuple[int, int, int, int]]] = []
    for contour in sorted(contours, key=cv2.contourArea, reverse=True):
        area = cv2.contourArea(contour)
        if area < minimum_area:
            break
        perimeter = cv2.arcLength(contour, True)
        corners = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(corners) != 4 or not cv2.isContourConvex(corners):
            continue
        ordered = _order_corners(corners)
        x, y, box_width, box_height = cv2.boundingRect(ordered)
        box = (x, y, box_width, box_height)
        duplicate = False
        for _, _, accepted_box in candidates:
            left = max(box[0], accepted_box[0])
            top = max(box[1], accepted_box[1])
            right = min(box[0] + box[2], accepted_box[0] + accepted_box[2])
            bottom = min(box[1] + box[3], accepted_box[1] + accepted_box[3])
            intersection = max(0, right - left) * max(0, bottom - top)
            smaller_area = min(box[2] * box[3], accepted_box[2] * accepted_box[3])
            if smaller_area and intersection / smaller_area > 0.7:
                duplicate = True
                break
        if not duplicate:
            ordered[:, 0] /= scale_x
            ordered[:, 1] /= scale_y
            candidates.append((area, ordered, box))

    if not candidates:
        return []

    candidates.sort(key=lambda item: (item[2][1], item[2][0]))
    return [corners for _, corners, _ in candidates]


def _rectify_document(image_rgb: np.ndarray, corners: np.ndarray) -> np.ndarray:
    top_left, top_right, bottom_right, bottom_left = corners
    width = max(
        round(np.linalg.norm(bottom_right - bottom_left)),
        round(np.linalg.norm(top_right - top_left)),
    )
    height = max(
        round(np.linalg.norm(top_right - bottom_right)),
        round(np.linalg.norm(top_left - bottom_left)),
    )
    width = max(width, 1)
    height = max(height, 1)
    destination = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    transform = cv2.getPerspectiveTransform(corners, destination)
    return cv2.warpPerspective(image_rgb, transform, (width, height))


def _remove_shadows(image_rgb: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
    background = cv2.dilate(gray, np.ones((5, 5), dtype=np.uint8))
    background = cv2.GaussianBlur(background, (21, 21), 0)
    background_float = background.astype(np.float32)
    target_brightness = min(float(np.percentile(background_float, 90)), 245.0)
    normalized = np.clip(
        gray.astype(np.float32) + target_brightness - background_float,
        0,
        255,
    ).astype(np.uint8)
    return cv2.cvtColor(normalized, cv2.COLOR_GRAY2RGB)


def preprocess_phone_photo(image_rgb: np.ndarray) -> np.ndarray:
    """Rectify a detected page and flatten its lighting; return RGB uint8.

    If no clear page boundary is found, leave the original photo unchanged.
    """
    if image_rgb.dtype != np.uint8 or image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
        raise ValueError("Phone-photo preprocessing expects an HWC uint8 RGB image.")

    corners = _find_document_corners(image_rgb)
    if corners is None:
        return image_rgb.copy()
    return _remove_shadows(_rectify_document(image_rgb, corners))


def preprocess_phone_photos(image_rgb: np.ndarray) -> list[np.ndarray]:
    """Return normalized detected pages, or the unchanged image if none are clear."""
    if image_rgb.dtype != np.uint8 or image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
        raise ValueError("Phone-photo preprocessing expects an HWC uint8 RGB image.")
    pages = _find_documents(image_rgb)
    if not pages:
        return [image_rgb.copy()]
    return [_remove_shadows(_rectify_document(image_rgb, corners)) for corners in pages]
