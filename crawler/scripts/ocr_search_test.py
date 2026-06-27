import re
from difflib import SequenceMatcher
from pathlib import Path

import cv2
import easyocr
import requests

from card_scan import scan_card


API_BASE_URL = "http://127.0.0.1:8000"

IMAGE_PATH = Path("data/test_images/wap2.jpeg")

OUTPUT_DIR = Path("data/test_images/debug")
WARPED_PATH = OUTPUT_DIR / "warped_card.jpeg"
BOTTOM_INFO_PATH = OUTPUT_DIR / "bottom_info.jpeg"
NAME_AREA_PATH = OUTPUT_DIR / "name_area.jpeg"
ENERGY_SYMBOL_PATH = OUTPUT_DIR / "energy_symbol.jpeg"


def load_and_normalize_card(image_path):
    image = cv2.imread(str(image_path))

    if image is None:
        raise FileNotFoundError(f"이미지를 읽을 수 없습니다: {image_path}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    scan_result = scan_card(image, debug_dir=OUTPUT_DIR)
    normalized = scan_result.image
    cv2.imwrite(str(WARPED_PATH), normalized)

    print(
        "scan result:",
        scan_result.method,
        "detected=",
        scan_result.detected,
        "confidence=",
        round(scan_result.confidence, 3),
    )

    return normalized


def crop_bottom_info(warped):
    height, width = warped.shape[:2]

    x1 = int(width * 0.02)
    x2 = int(width * 0.98)
    y1 = int(height * 0.95)
    y2 = int(height)

    crop = warped[y1:y2, x1:x2]

    crop = cv2.resize(
        crop,
        None,
        fx=4,
        fy=4,
        interpolation=cv2.INTER_CUBIC,
    )

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    cv2.imwrite(str(BOTTOM_INFO_PATH), gray)

    return gray


def crop_name_area(warped):
    height, width = warped.shape[:2]

    x1 = int(width * 0.0)
    x2 = int(width * 0.8)
    y1 = int(height * 0.00001)
    y2 = int(height * 0.1)

    crop = warped[y1:y2, x1:x2]

    crop = cv2.resize(
        crop,
        None,
        fx=3,
        fy=3,
        interpolation=cv2.INTER_CUBIC,
    )

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    cv2.imwrite(str(NAME_AREA_PATH), gray)

    return gray


def crop_energy_symbol_area(warped):
    height, width = warped.shape[:2]

    x1 = int(width * 0.22)
    x2 = int(width * 0.78)
    y1 = int(height * 0.30)
    y2 = int(height * 0.72)

    crop = warped[y1:y2, x1:x2]
    cv2.imwrite(str(ENERGY_SYMBOL_PATH), crop)

    return crop


def run_ocr(image, reader):
    return reader.readtext(
        image,
        detail=0,
        paragraph=False,
    )


def normalize_number_text(text):
    text = text.upper()
    text = text.replace("O", "0")
    text = text.replace("|", "1")
    text = text.replace(" ", "")
    return text

RARITIES = ["SAR", "ACE", "UR", "SR", "RR", "AR", "R", "U", "C"]


def normalize_bottom_line(line):
    line = line.upper()
    line = line.replace("J", "1")
    line = line.replace("O", "0")
    line = line.replace("|", "1")
    line = line.replace(" ", "")
    return line


def parse_bottom_info(ocr_lines):
    for line in ocr_lines:
        normalized = normalize_bottom_line(line)

        match = re.search(
            r"(\d{1,3})/(\d{3}|[A-Z]+-?[A-Z]*)(SAR|ACE|UR|SR|RR|AR|R|U|C)?",
            normalized,
        )

        if not match:
            continue

        number = match.group(1).zfill(3)
        suffix = match.group(2)
        rarity = match.group(3) or ""

        if number == "000":
            continue

        if suffix.isdigit():
            suffix = suffix.zfill(3)

        return number, suffix, rarity, line

    return "", "", "", ""

   
def clean_name_text(text):
    remove_words = [
        "HP",
        "EX",
        "ex",
        "V",
        "기본",
        "1진화",
        "2진화",
        "카드",
        "종류",
        "포켓몬",
    ]

    for word in remove_words:
        text = text.replace(word, "")

    text = re.sub(r"[^가-힣a-zA-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def select_best_candidate_by_name(candidates, name_lines):
    joined_text = clean_name_text(" ".join(name_lines))

    best_card = None
    best_score = 0

    for card in candidates:
        card_name = card["name"]

        scores = [similarity(joined_text, card_name)]

        for line in name_lines:
            cleaned_line = clean_name_text(line)
            if cleaned_line:
                scores.append(similarity(cleaned_line, card_name))

        score = max(scores)

        if score > best_score:
            best_score = score
            best_card = card

    return best_card, best_score, joined_text


def classify_energy_type_by_color(crop):
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

    h = hsv[:, :, 0]
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]

    mask = (s > 40) & (v > 80)

    if mask.mean() < 0.05:
        return ""

    mean_hue = h[mask].mean()

    print("energy mean_hue:", mean_hue)

    if 90 <= mean_hue <= 115:
        return "물"

    if 35 <= mean_hue <= 85:
        return "풀"

    if 20 <= mean_hue <= 35:
        return "번개"

    if mean_hue < 15 or mean_hue >= 170:
        return "불꽃"

    if 125 <= mean_hue <= 160:
        return "초"

    if 10 <= mean_hue <= 25:
        return "격투"

    return ""


def build_energy_name(energy_type):
    if not energy_type:
        return ""

    return f"기본 {energy_type} 에너지"


def search_candidates(
    number="",
    suffix="",
    rarity="",
    name="",
    card_group="",
):
    params = {
        "number": number,
        "suffix": suffix,
        "rarity": rarity,
        "name": name,
        "card_group": card_group,
    }

    params = {key: value for key, value in params.items() if value}

    response = requests.get(
        f"{API_BASE_URL}/cards/recognize-candidates",
        params=params,
        timeout=10,
    )

    return response.json()


def print_card(card):
    print(
        card["card_id"],
        card["name"],
        card["card_number"],
        card["set_code"],
        card["rarity"],
        card["recognition_key"],
    )


def handle_general_card(warped, number, suffix, rarity, ko_reader):
    print("\n일반 카드 검색 모드")

    data = search_candidates(
        number=number,
        suffix=suffix,
        rarity=rarity,
    )

    candidates = data["results"]

    print("\n=== 1차 API RESULT: number/suffix/rarity ===")
    print("count:", data["count"])

    for card in candidates[:10]:
        print_card(card)

    if len(candidates) == 0:
        print("\n후보 없음")
        return

    if len(candidates) == 1:
        print("\n=== FINAL SELECTED CARD ===")
        print_card(candidates[0])
        return

    print("\n후보가 2장 이상이라 상단 이름 OCR로 자동 선택 시도")

    name_area = crop_name_area(warped)
    print(f"이름 영역 crop 저장 완료: {NAME_AREA_PATH}")

    name_lines = run_ocr(name_area, ko_reader)

    print("\n=== OCR LINES FROM NAME AREA ===")
    for line in name_lines:
        print(line)

    best_card, best_score, ocr_name_text = select_best_candidate_by_name(
        candidates,
        name_lines,
    )

    print("\n=== NAME MATCH RESULT ===")
    print("ocr_name_text:", ocr_name_text)
    print("best_score:", best_score)

    if best_card and best_score >= 0.35:
        print("\n=== FINAL SELECTED CARD ===")
        print_card(best_card)
    else:
        print("\n자동 확정 실패")
        print("후보를 사용자에게 보여줘야 함")


def handle_energy_card(warped):
    print("\n번호 없음: 에너지 카드 분류 모드")

    energy_symbol = crop_energy_symbol_area(warped)
    print(f"에너지 심볼 crop 저장 완료: {ENERGY_SYMBOL_PATH}")

    energy_type = classify_energy_type_by_color(energy_symbol)
    energy_name = build_energy_name(energy_type)

    print("\n=== PARSED ENERGY ===")
    print("energy_type:", energy_type)
    print("energy_name:", energy_name)

    if not energy_name:
        print("에너지 타입 분류 실패")
        return

    data = search_candidates(
        name=energy_name,
        card_group="energy",
    )

    print("\n=== API RESULT ===")
    print("count:", data["count"])

    for card in data["results"][:10]:
        print_card(card)

    if data["count"] == 1:
        print("\n=== FINAL SELECTED CARD ===")
        print_card(data["results"][0])
    else:
        print("\n에너지 후보를 사용자에게 보여줘야 함")


def main():
    if not IMAGE_PATH.exists():
        print(f"이미지 파일 없음: {IMAGE_PATH}")
        return

    print("OCR Reader 로딩 중...")
    en_reader = easyocr.Reader(["en"])
    ko_reader = easyocr.Reader(["ko", "en"])

    warped = load_and_normalize_card(IMAGE_PATH)
    print(f"\n보정 카드 저장 완료: {WARPED_PATH}")

    bottom_info = crop_bottom_info(warped)
    print(f"하단 정보 crop 저장 완료: {BOTTOM_INFO_PATH}")

    bottom_lines = run_ocr(bottom_info, ko_reader)

    print("\n=== OCR LINES FROM BOTTOM INFO ===")
    for line in bottom_lines:
        print(line)

    number, suffix, rarity, target_line = parse_bottom_info(bottom_lines)

    print("\n=== PARSED BOTTOM OCR ===")
    print("target_line:", target_line)
    print("number:", number)
    print("suffix:", suffix)
    print("rarity:", rarity)

    if number and suffix:
        handle_general_card(
            warped=warped,
            number=number,
            suffix=suffix,
            rarity=rarity,
            ko_reader=ko_reader,
        )
    else:
        handle_energy_card(warped)


if __name__ == "__main__":
    main()
