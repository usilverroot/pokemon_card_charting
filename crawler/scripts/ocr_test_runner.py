import argparse
import json
import re
from pathlib import Path

import cv2
import easyocr
import numpy as np


RARITIES = ["SAR", "ACE", "UR", "SR", "RR", "AR", "R", "U", "C"]


def prepare_bottom_variants(crop):
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    equalized = cv2.equalizeHist(gray)

    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
    clahe_gray = clahe.apply(gray)

    adaptive = cv2.adaptiveThreshold(
        clahe_gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        9,
    )
    inverted = cv2.bitwise_not(adaptive)

    return {
        "gray": equalized,
        "clahe": clahe_gray,
        "adaptive": adaptive,
        "inverted": inverted,
    }


def crop_bottom_info(warped, output_dir):
    height, width = warped.shape[:2]

    x1 = int(width * 0.02)
    x2 = int(width * 0.98)
    y1 = int(height * 0.91)
    y2 = int(height * 0.99)

    crop = warped[y1:y2, x1:x2]
    crop = cv2.resize(crop, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    variants = prepare_bottom_variants(crop)

    for name, image in variants.items():
        cv2.imwrite(str(output_dir / f"bottom_info_{name}.jpeg"), image)

    cv2.imwrite(str(output_dir / "bottom_info.jpeg"), variants["gray"])

    return variants


def crop_name_area(warped, output_path):
    height, width = warped.shape[:2]

    x1 = int(width * 0.0)
    x2 = int(width * 0.92)
    y1 = int(height * 0.015)
    y2 = int(height * 0.16)

    crop = warped[y1:y2, x1:x2]
    crop = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    cv2.imwrite(str(output_path), gray)

    return gray


def crop_energy_symbol_area(warped, output_path):
    height, width = warped.shape[:2]

    x1 = int(width * 0.22)
    x2 = int(width * 0.78)
    y1 = int(height * 0.30)
    y2 = int(height * 0.72)

    crop = warped[y1:y2, x1:x2]
    cv2.imwrite(str(output_path), crop)

    return crop


def run_ocr(image, reader):
    return reader.readtext(image, detail=0, paragraph=False)


def unique_lines(lines):
    seen = set()
    unique = []

    for line in lines:
        key = line.strip()
        if not key or key in seen:
            continue

        seen.add(key)
        unique.append(line)

    return unique


def normalize_bottom_line(line):
    text = line.upper()
    text = text.replace("O", "0")
    text = text.replace("|", "1")
    text = text.replace("J", "1")
    text = text.replace("’", "'")
    text = text.replace("`", "'")
    text = re.sub(r"[^0-9A-Z/:'\\.-]", "", text)
    return text


def parse_bottom_info(ocr_lines):
    joined = normalize_bottom_line("".join(ocr_lines))
    normalized_candidates = [(line, normalize_bottom_line(line)) for line in ocr_lines]
    normalized_candidates.append((" ".join(ocr_lines), joined))

    rarity_group = "|".join(RARITIES)
    patterns = [
        rf"(\d{{1,3}})([/:'\\.-])(\d{{3}}|[A-Z]{{1,6}}-?[A-Z0-9]{{0,4}})({rarity_group})?",
        rf"(\d{{1,3}})()(\d{{3}})({rarity_group})",
    ]
    parsed_candidates = []

    for raw_line, normalized in normalized_candidates:
        for pattern in patterns:
            for match in re.finditer(pattern, normalized):
                end = match.end()
                trailing = normalized[end:]

                if trailing and trailing[0].isdigit():
                    continue

                number = match.group(1).zfill(3)
                separator = match.group(2)
                suffix = match.group(3)
                rarity = match.group(4) or ""

                if number == "000":
                    continue

                if suffix.isdigit():
                    suffix = suffix.zfill(3)

                score = 0
                score += 4 if separator else 1
                score += 3 if rarity else 0
                score += 2 if suffix.isdigit() and len(suffix) == 3 else 0
                score += 1 if len(number) == 3 else 0
                score -= 2 if "2026" in normalized or "POK" in normalized else 0
                score -= 1 if trailing and trailing[0].isalpha() else 0

                parsed_candidates.append(
                    (
                        score,
                        {
                            "number": number,
                            "suffix": suffix,
                            "rarity": rarity,
                            "target_line": raw_line,
                            "normalized_line": normalized,
                        },
                    )
                )

    if parsed_candidates:
        parsed_candidates.sort(key=lambda item: item[0], reverse=True)
        return parsed_candidates[0][1]

    return {
        "number": "",
        "suffix": "",
        "rarity": "",
        "target_line": "",
        "normalized_line": "",
    }


def clean_name_text(text):
    for word in ["HP", "EX", "ex", "V", "기본", "1진화", "2진화", "카드", "종류", "포켓몬"]:
        text = text.replace(word, "")

    text = re.sub(r"[^가-힣a-zA-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def classify_energy_type_by_color(crop):
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    h = hsv[:, :, 0]
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    mask = (s > 40) & (v > 80)

    if mask.mean() < 0.05:
        return "", None

    mean_hue = float(h[mask].mean())

    if 90 <= mean_hue <= 115:
        return "물", mean_hue
    if 35 <= mean_hue <= 85:
        return "풀", mean_hue
    if 20 <= mean_hue <= 35:
        return "번개", mean_hue
    if mean_hue < 15 or mean_hue >= 170:
        return "불꽃", mean_hue
    if 125 <= mean_hue <= 160:
        return "초", mean_hue
    if 10 <= mean_hue <= 25:
        return "격투", mean_hue

    return "", mean_hue


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    image_path = Path(args.image)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    warped = cv2.imread(str(image_path))
    if warped is None:
        raise FileNotFoundError(f"이미지를 읽을 수 없습니다: {image_path}")

    name_path = output_dir / "name_area.jpeg"
    energy_path = output_dir / "energy_symbol.jpeg"

    bottom_variants = crop_bottom_info(warped, output_dir)
    name_area = crop_name_area(warped, name_path)
    energy_symbol = crop_energy_symbol_area(warped, energy_path)

    ko_reader = easyocr.Reader(["ko", "en"])
    bottom_variant_lines = {}
    all_bottom_lines = []

    for variant_name, bottom_image in bottom_variants.items():
        lines = run_ocr(bottom_image, ko_reader)
        bottom_variant_lines[variant_name] = lines
        all_bottom_lines.extend(lines)

    bottom_lines = unique_lines(all_bottom_lines)
    name_lines = run_ocr(name_area, ko_reader)
    parsed = parse_bottom_info(bottom_lines)

    energy_type, mean_hue = classify_energy_type_by_color(energy_symbol)

    result = {
        "bottom_lines": bottom_lines,
        "bottom_variant_lines": bottom_variant_lines,
        "name_lines": name_lines,
        "parsed": parsed,
        "name_text": clean_name_text(" ".join(name_lines)),
        "energy": {
            "type": energy_type,
            "name": f"기본 {energy_type} 에너지" if energy_type else "",
            "mean_hue": mean_hue,
        },
        "crops": {
            "bottom": "ocr_bottom",
            "bottom_gray": "ocr_bottom_gray",
            "bottom_clahe": "ocr_bottom_clahe",
            "bottom_adaptive": "ocr_bottom_adaptive",
            "bottom_inverted": "ocr_bottom_inverted",
            "name": "ocr_name",
            "energy": "ocr_energy",
        },
    }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
