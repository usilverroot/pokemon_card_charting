from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


CARD_WIDTH = 1002
CARD_HEIGHT = 1400
CARD_ASPECT_RATIO = CARD_WIDTH / CARD_HEIGHT


@dataclass
class CardScanResult:
    image: np.ndarray
    detected: bool
    method: str
    confidence: float
    corners: np.ndarray | None = None
    message: str = ""


def order_points(points):
    points = np.asarray(points, dtype="float32")

    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1)

    ordered = np.zeros((4, 2), dtype="float32")
    ordered[0] = points[np.argmin(sums)]
    ordered[2] = points[np.argmax(sums)]
    ordered[1] = points[np.argmin(diffs)]
    ordered[3] = points[np.argmax(diffs)]

    return ordered


def four_point_transform(image, points, width=CARD_WIDTH, height=CARD_HEIGHT):
    rect = order_points(points)
    destination = np.array(
        [
            [0, 0],
            [width - 1, 0],
            [width - 1, height - 1],
            [0, height - 1],
        ],
        dtype="float32",
    )

    matrix = cv2.getPerspectiveTransform(rect, destination)
    return cv2.warpPerspective(image, matrix, (width, height))


def resize_for_detection(image, max_side=1200):
    height, width = image.shape[:2]
    scale = max_side / max(height, width)

    if scale >= 1:
        return image.copy(), 1.0

    resized = cv2.resize(
        image,
        (int(width * scale), int(height * scale)),
        interpolation=cv2.INTER_AREA,
    )

    return resized, scale


def rectangle_points(x, y, width, height):
    return np.array(
        [
            [x, y],
            [x + width - 1, y],
            [x + width - 1, y + height - 1],
            [x, y + height - 1],
        ],
        dtype="float32",
    )


def guided_frame_region(image):
    height, width = image.shape[:2]
    current_ratio = width / height

    if abs(current_ratio - CARD_ASPECT_RATIO) <= 0.08:
        return image.copy(), rectangle_points(0, 0, width, height)

    crop_height = int(height * 0.76)
    crop_width = int(crop_height * CARD_ASPECT_RATIO)

    if crop_width > int(width * 0.92):
        crop_width = int(width * 0.92)
        crop_height = int(crop_width / CARD_ASPECT_RATIO)

    crop_width = min(crop_width, width)
    crop_height = min(crop_height, height)

    x1 = max((width - crop_width) // 2, 0)
    y1 = max(int((height - crop_height) * 0.47), 0)
    y1 = min(y1, height - crop_height)

    return (
        image[y1:y1 + crop_height, x1:x1 + crop_width],
        rectangle_points(x1, y1, crop_width, crop_height),
    )


def card_quad_score(points, image_shape):
    points = order_points(points)
    image_height, image_width = image_shape[:2]
    image_area = image_height * image_width
    area = cv2.contourArea(points)

    if area <= image_area * 0.28:
        return 0

    border_margin = max(8, int(min(image_width, image_height) * 0.025))
    touches_frame = (
        points[:, 0].min() <= border_margin
        or points[:, 1].min() <= border_margin
        or points[:, 0].max() >= image_width - border_margin
        or points[:, 1].max() >= image_height - border_margin
    )

    if touches_frame:
        return 0

    top = np.linalg.norm(points[1] - points[0])
    right = np.linalg.norm(points[2] - points[1])
    bottom = np.linalg.norm(points[2] - points[3])
    left = np.linalg.norm(points[3] - points[0])

    avg_width = (top + bottom) / 2
    avg_height = (left + right) / 2

    if avg_width <= 0 or avg_height <= 0 or avg_width > avg_height * 1.08:
        return 0

    ratio = avg_width / avg_height
    ratio_penalty = abs(ratio - CARD_ASPECT_RATIO)

    if ratio_penalty > 0.20:
        return 0

    center = points.mean(axis=0)
    image_center = np.array([image_width / 2, image_height / 2], dtype="float32")
    center_distance = np.linalg.norm((center - image_center) / image_center)
    center_score = max(0.0, 1.0 - center_distance)
    ratio_score = max(0.0, 1.0 - ratio_penalty / 0.20)
    area_score = min(area / image_area, 1.0)

    return area_score * 0.45 + ratio_score * 0.40 + center_score * 0.15


def expand_points(points, image_shape, margin=0.0):
    points = order_points(points)
    center = points.mean(axis=0)
    expanded = center + (points - center) * (1.0 + margin)
    height, width = image_shape[:2]
    expanded[:, 0] = np.clip(expanded[:, 0], 0, width - 1)
    expanded[:, 1] = np.clip(expanded[:, 1], 0, height - 1)

    return order_points(expanded)


def estimate_horizontal_skew(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(gray, 45, 140)

    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=85,
        minLineLength=int(image.shape[1] * 0.22),
        maxLineGap=18,
    )

    if lines is None:
        return 0.0, 0

    angles = []

    for line in lines[:, 0]:
        x1, y1, x2, y2 = line
        dx = x2 - x1
        dy = y2 - y1

        if dx == 0:
            continue

        angle = np.degrees(np.arctan2(dy, dx))
        length = np.hypot(dx, dy)

        if abs(angle) <= 4.0 and length >= image.shape[1] * 0.22:
            angles.append(angle)

    if len(angles) < 4:
        return 0.0, len(angles)

    median = float(np.median(angles))
    inliers = [angle for angle in angles if abs(angle - median) <= 1.2]

    if len(inliers) < 4:
        return 0.0, len(angles)

    return float(np.median(inliers)), len(inliers)


def rotate_keep_size(image, angle):
    if abs(angle) < 0.2:
        return image

    height, width = image.shape[:2]
    center = (width / 2, height / 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

    return cv2.warpAffine(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def gently_deskew_by_horizontal_lines(image):
    angle, count = estimate_horizontal_skew(image)

    if count < 4 or abs(angle) < 0.2 or abs(angle) > 2.0:
        return image, 0.0, count

    return rotate_keep_size(image, angle), angle, count


def contour_quad_candidates(mask, image_shape):
    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    for contour in contours:
        if cv2.contourArea(contour) < image_shape[0] * image_shape[1] * 0.08:
            continue

        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.025 * perimeter, True)

        if len(approx) == 4 and cv2.isContourConvex(approx):
            points = approx.reshape(4, 2).astype("float32")
            score = card_quad_score(points, image_shape)

            if score:
                yield score, points

        rect = cv2.minAreaRect(contour)
        points = cv2.boxPoints(rect).astype("float32")
        score = card_quad_score(points, image_shape) * 0.96

        if score:
            yield score, points


def edge_transition_mask(image):
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    channels = cv2.split(cv2.GaussianBlur(lab, (5, 5), 0))
    gradient = np.zeros(image.shape[:2], dtype="float32")

    for channel in channels:
        grad_x = cv2.Sobel(channel, cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(channel, cv2.CV_32F, 0, 1, ksize=3)
        gradient = np.maximum(gradient, cv2.magnitude(grad_x, grad_y))

    gradient = cv2.normalize(gradient, None, 0, 255, cv2.NORM_MINMAX).astype("uint8")
    _, strong_edges = cv2.threshold(
        gradient,
        max(36, int(np.percentile(gradient, 83))),
        255,
        cv2.THRESH_BINARY,
    )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    canny = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 45, 140)
    mask = cv2.bitwise_or(strong_edges, canny)

    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 23))
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (23, 3))
    vertical = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, vertical_kernel, iterations=1)
    horizontal = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, horizontal_kernel, iterations=1)
    mask = cv2.bitwise_or(vertical, horizontal)
    mask = cv2.dilate(mask, None, iterations=1)

    return mask


def foreground_card_mask(image):
    height, width = image.shape[:2]
    inset_x = max(4, int(width * 0.03))
    inset_y = max(4, int(height * 0.03))

    if inset_x * 2 >= width or inset_y * 2 >= height:
        return None

    mask = np.zeros((height, width), np.uint8)
    rect = (inset_x, inset_y, width - inset_x * 2, height - inset_y * 2)
    bg_model = np.zeros((1, 65), np.float64)
    fg_model = np.zeros((1, 65), np.float64)

    try:
        cv2.grabCut(image, mask, rect, bg_model, fg_model, 4, cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        return None

    foreground = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0)
    foreground = foreground.astype("uint8")
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17))
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, kernel, iterations=2)
    foreground = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, kernel, iterations=1)

    return foreground


def find_card_corners_in_frame(frame):
    resized, scale = resize_for_detection(frame, max_side=1000)
    candidates = []

    transition_mask = edge_transition_mask(resized)
    candidates.extend(contour_quad_candidates(transition_mask, resized.shape))

    foreground_mask = foreground_card_mask(resized)
    if foreground_mask is not None:
        candidates.extend(contour_quad_candidates(foreground_mask, resized.shape))

    if not candidates:
        return None, 0

    score, points = max(candidates, key=lambda item: item[0])
    points = order_points(points / scale)

    return points, score


def points_score(points, image_shape):
    points = np.asarray(points, dtype="float32")
    image_height, image_width = image_shape[:2]
    image_area = image_height * image_width
    area = cv2.contourArea(points)

    if area <= image_area * 0.10:
        return 0

    border_margin = max(6, int(min(image_width, image_height) * 0.01))
    touches_border = (
        points[:, 0].min() <= border_margin
        or points[:, 1].min() <= border_margin
        or points[:, 0].max() >= image_width - border_margin
        or points[:, 1].max() >= image_height - border_margin
    )

    if touches_border:
        return 0

    rect = order_points(points)

    top = np.linalg.norm(rect[1] - rect[0])
    right = np.linalg.norm(rect[2] - rect[1])
    bottom = np.linalg.norm(rect[2] - rect[3])
    left = np.linalg.norm(rect[3] - rect[0])

    avg_width = (top + bottom) / 2
    avg_height = (left + right) / 2

    if avg_width == 0 or avg_height == 0:
        return 0

    ratio = min(avg_width, avg_height) / max(avg_width, avg_height)
    expected_ratio = min(CARD_ASPECT_RATIO, 1 / CARD_ASPECT_RATIO)
    ratio_penalty = abs(ratio - expected_ratio)

    if ratio_penalty > 0.18:
        return 0

    area_score = min(area / image_area, 1.0)
    ratio_score = max(0.0, 1.0 - ratio_penalty / 0.18)

    return area_score * 0.65 + ratio_score * 0.35


def contour_candidates(contour, image_shape):
    perimeter = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
    image_area = image_shape[0] * image_shape[1]

    if len(approx) == 4 and cv2.isContourConvex(approx):
        points = approx.reshape(4, 2).astype("float32")
        score = points_score(points, image_shape)

        if score:
            yield score, points

    if cv2.contourArea(contour) > image_area * 0.12:
        rect = cv2.minAreaRect(contour)
        points = cv2.boxPoints(rect).astype("float32")
        score = points_score(points, image_shape) * 0.92

        if score:
            yield score, points


def find_card_corners(image):
    resized, scale = resize_for_detection(image)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    candidates = []

    for low, high in ((30, 90), (50, 150), (75, 200)):
        edges = cv2.Canny(gray, low, high)
        edges = cv2.dilate(edges, None, iterations=1)
        edges = cv2.erode(edges, None, iterations=1)

        contours, _ = cv2.findContours(
            edges,
            cv2.RETR_LIST,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        for contour in contours:
            candidates.extend(contour_candidates(contour, resized.shape))

    if not candidates:
        return None, 0

    score, points = max(candidates, key=lambda item: item[0])
    points = points / scale

    return order_points(points), score


def fallback_guided_frame_crop(image):
    cropped, _ = guided_frame_region(image)

    return cv2.resize(
        cropped,
        (CARD_WIDTH, CARD_HEIGHT),
        interpolation=cv2.INTER_CUBIC,
    )


def fallback_center_crop(image):
    height, width = image.shape[:2]
    target_ratio = CARD_ASPECT_RATIO
    current_ratio = width / height

    if current_ratio > target_ratio:
        crop_height = height
        crop_width = int(height * target_ratio)
    else:
        crop_width = width
        crop_height = int(width / target_ratio)

    x1 = max((width - crop_width) // 2, 0)
    y1 = max((height - crop_height) // 2, 0)
    cropped = image[y1:y1 + crop_height, x1:x1 + crop_width]

    return cv2.resize(
        cropped,
        (CARD_WIDTH, CARD_HEIGHT),
        interpolation=cv2.INTER_CUBIC,
    )


def draw_debug_overlay(image, corners):
    overlay = image.copy()

    if corners is not None:
        points = corners.astype("int32").reshape((-1, 1, 2))
        cv2.polylines(overlay, [points], True, (0, 255, 0), 4)

        for index, point in enumerate(corners.astype("int32")):
            cv2.circle(overlay, tuple(point), 10, (0, 0, 255), -1)
            cv2.putText(
                overlay,
                str(index),
                tuple(point + 14),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2,
            )

    return overlay


def scan_card(image, debug_dir=None):
    height, width = image.shape[:2]

    if abs((width / height) - CARD_ASPECT_RATIO) <= 0.04:
        corners = rectangle_points(0, 0, width, height)
        normalized = four_point_transform(image, corners)
        normalized, skew_angle, skew_lines = gently_deskew_by_horizontal_lines(normalized)
        skew_message = (
            f" 내부 가로선 기준으로 {skew_angle:.2f}도 기울기를 보정했습니다."
            if skew_angle
            else ""
        )
        result = CardScanResult(
            image=normalized,
            detected=True,
            method="already_card_ratio",
            confidence=0.58,
            corners=corners,
            message=f"이미 카드 비율에 가까워 표준 크기로 정렬했습니다.{skew_message}",
        )
    else:
        result = None

    if result is not None:
        if debug_dir:
            debug_path = Path(debug_dir)
            debug_path.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(debug_path / "scan_input.jpeg"), image)
            cv2.imwrite(str(debug_path / "scan_normalized.jpeg"), result.image)
            cv2.imwrite(
                str(debug_path / "scan_overlay.jpeg"),
                draw_debug_overlay(image, result.corners),
            )

        return result

    frame, frame_points = guided_frame_region(image)
    frame_corners, confidence = find_card_corners_in_frame(frame)

    if frame_corners is not None:
        frame_origin = frame_points[0]
        corners = expand_points(
            frame_corners + frame_origin,
            image.shape,
            margin=0.012,
        )
        normalized = four_point_transform(image, corners)
        normalized, skew_angle, skew_lines = gently_deskew_by_horizontal_lines(normalized)
        skew_message = (
            f" 내부 가로선 기준으로 {skew_angle:.2f}도 기울기를 보정했습니다."
            if skew_angle
            else ""
        )
        result = CardScanResult(
            image=normalized,
            detected=True,
            method="frame_border_perspective",
            confidence=confidence,
            corners=corners,
            message=f"프레임 안의 카드 테두리 경계를 기준으로 투시 보정했습니다.{skew_message}",
        )
    else:
        normalized = fallback_guided_frame_crop(image)
        result = CardScanResult(
            image=normalized,
            detected=False,
            method="guided_frame_crop",
            confidence=0.25,
            corners=frame_points,
            message="카드 테두리 경계가 불안정해 화면 프레임 기준으로만 보정했습니다.",
        )

    if debug_dir:
        debug_path = Path(debug_dir)
        debug_path.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(debug_path / "scan_input.jpeg"), image)
        cv2.imwrite(str(debug_path / "scan_normalized.jpeg"), result.image)
        cv2.imwrite(
            str(debug_path / "scan_overlay.jpeg"),
            draw_debug_overlay(image, result.corners),
        )

    return result
