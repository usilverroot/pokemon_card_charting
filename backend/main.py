import json
import re
import subprocess
import sys
import tempfile
from difflib import SequenceMatcher
from pathlib import Path

import cv2
from fastapi import FastAPI, File, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
import psycopg2
from psycopg2.extras import RealDictCursor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CRAWLER_SCRIPTS_DIR = PROJECT_ROOT / "crawler" / "scripts"
CRAWLER_VENV_PYTHON = PROJECT_ROOT / "crawler" / ".venv" / "bin" / "python"
if str(CRAWLER_SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(CRAWLER_SCRIPTS_DIR))

from card_scan import draw_debug_overlay, scan_card


LAST_SCAN_DIR = PROJECT_ROOT / "backend" / "debug" / "last_scan"
LAST_SCAN_OCR_DIR = LAST_SCAN_DIR / "ocr"


class UTF8JSONResponse(Response):
    media_type = "application/json; charset=utf-8"

    def render(self, content) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")

app = FastAPI(default_response_class=UTF8JSONResponse)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    "dbname": "pokemon_card_db",
    "user": "a123",
    "host": "localhost",
    "port": 5432,
}


def get_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_client_encoding("UTF8")
    return conn


def fetch_recognition_candidates(
    name="",
    number="",
    suffix="",
    rarity="",
    set_code="",
    limit=30,
):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT
            card_id,
            card_group,
            name,
            card_number,
            card_number_main,
            card_number_suffix,
            rarity,
            set_code,
            recognition_key,
            hp,
            card_type,
            category,
            illustrator,
            image_url,
            detail_url
        FROM cards
        WHERE
            (%s = '' OR name ILIKE %s)
            AND (%s = '' OR card_number_main = %s)
            AND (%s = '' OR card_number_suffix = %s)
            AND (%s = '' OR rarity = %s)
            AND (%s = '' OR set_code = %s)
        ORDER BY
            set_code,
            card_number_main,
            rarity
        LIMIT %s;
        """,
        (
            name,
            f"%{name}%",
            number,
            number,
            suffix,
            suffix,
            rarity,
            rarity,
            set_code,
            set_code,
            limit,
        ),
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return rows


def run_ocr_test_on_normalized_image(image_path):
    runner_path = CRAWLER_SCRIPTS_DIR / "ocr_test_runner.py"
    python_path = CRAWLER_VENV_PYTHON if CRAWLER_VENV_PYTHON.exists() else Path(sys.executable)

    completed = subprocess.run(
        [
            str(python_path),
            str(runner_path),
            "--image",
            str(image_path),
            "--output-dir",
            str(LAST_SCAN_OCR_DIR),
        ],
        cwd=str(PROJECT_ROOT / "crawler"),
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )

    if completed.returncode != 0:
        return {
            "ok": False,
            "message": "OCR 테스트 실행 중 오류가 발생했습니다.",
            "stderr": completed.stderr[-1200:],
            "stdout": completed.stdout[-1200:],
        }

    output_lines = [line for line in completed.stdout.splitlines() if line.strip()]

    if not output_lines:
        return {
            "ok": False,
            "message": "OCR 테스트 결과가 비어 있습니다.",
            "stderr": completed.stderr[-1200:],
        }

    try:
        result = json.loads(output_lines[-1])
    except json.JSONDecodeError:
        return {
            "ok": False,
            "message": "OCR 테스트 결과를 JSON으로 읽을 수 없습니다.",
            "stdout": completed.stdout[-1200:],
            "stderr": completed.stderr[-1200:],
        }

    return {
        "ok": True,
        "result": result,
    }


def normalize_match_text(text):
    text = (text or "").lower()
    text = re.sub(r"[^0-9a-z가-힣]", "", text)

    for word in ["아이템", "트레이너", "트레이너스", "서포트", "기본", "진화", "포켓몬"]:
        text = text.replace(word, "")

    return text


def name_similarity(ocr_name_text, card_name):
    ocr_text = normalize_match_text(ocr_name_text)
    card_text = normalize_match_text(card_name)

    if not ocr_text or not card_text:
        return 0.0

    scores = [SequenceMatcher(None, ocr_text, card_text).ratio()]

    for size in range(2, min(len(ocr_text), 5) + 1):
        for index in range(0, len(ocr_text) - size + 1):
            piece = ocr_text[index:index + size]
            if piece and piece in card_text:
                scores.append(min(1.0, 0.55 + size * 0.08))

    return max(scores)


def rank_candidates_by_ocr_name(candidates, ocr_name_text):
    ranked = []

    for card in candidates:
        score = name_similarity(ocr_name_text, card.get("name", ""))
        ranked_card = dict(card)
        ranked_card["name_match_score"] = round(score, 3)
        ranked.append(ranked_card)

    return sorted(
        ranked,
        key=lambda card: (
            card.get("name_match_score", 0),
            card.get("rarity") or "",
            card.get("name") or "",
        ),
        reverse=True,
    )


@app.get("/")
def root():
    return {"message": "Pokemon Card API is running"}


@app.post("/recognition/scan")
async def scan_uploaded_card(file: UploadFile = File(...)):
    suffix = Path(file.filename or "upload.jpg").suffix or ".jpg"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(await file.read())
        temp_path = Path(temp_file.name)

    image = cv2.imread(str(temp_path))
    temp_path.unlink(missing_ok=True)

    if image is None:
        return {
            "ok": False,
            "message": "이미지를 읽을 수 없습니다.",
        }

    scan_result = scan_card(image)
    height, width = scan_result.image.shape[:2]
    LAST_SCAN_DIR.mkdir(parents=True, exist_ok=True)

    cv2.imwrite(str(LAST_SCAN_DIR / "input.jpeg"), image)
    cv2.imwrite(str(LAST_SCAN_DIR / "normalized.jpeg"), scan_result.image)
    cv2.imwrite(
        str(LAST_SCAN_DIR / "overlay.jpeg"),
        draw_debug_overlay(image, scan_result.corners),
    )

    return {
        "ok": True,
        "scan": {
            "detected": scan_result.detected,
            "method": scan_result.method,
            "confidence": round(float(scan_result.confidence), 3),
            "width": int(width),
            "height": int(height),
            "message": scan_result.message,
            "needs_retake": not scan_result.detected,
        },
        "debug_images": {
            "input": "/recognition/last-scan/input",
            "normalized": "/recognition/last-scan/normalized",
            "overlay": "/recognition/last-scan/overlay",
        },
        "next": "카드 보정 품질을 먼저 안정화한 뒤 OCR 후보 검색을 연결합니다.",
    }


@app.post("/recognition/scan-and-ocr-test")
async def scan_and_ocr_test_uploaded_card(file: UploadFile = File(...)):
    suffix = Path(file.filename or "upload.jpg").suffix or ".jpg"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(await file.read())
        temp_path = Path(temp_file.name)

    image = cv2.imread(str(temp_path))
    temp_path.unlink(missing_ok=True)

    if image is None:
        return {
            "ok": False,
            "message": "이미지를 읽을 수 없습니다.",
        }

    scan_result = scan_card(image)
    height, width = scan_result.image.shape[:2]
    LAST_SCAN_DIR.mkdir(parents=True, exist_ok=True)
    LAST_SCAN_OCR_DIR.mkdir(parents=True, exist_ok=True)

    cv2.imwrite(str(LAST_SCAN_DIR / "input.jpeg"), image)
    cv2.imwrite(str(LAST_SCAN_DIR / "normalized.jpeg"), scan_result.image)
    cv2.imwrite(
        str(LAST_SCAN_DIR / "overlay.jpeg"),
        draw_debug_overlay(image, scan_result.corners),
    )

    ocr_test = run_ocr_test_on_normalized_image(LAST_SCAN_DIR / "normalized.jpeg")

    if not ocr_test["ok"]:
        return {
            "ok": False,
            "message": ocr_test["message"],
            "scan": {
                "detected": scan_result.detected,
                "method": scan_result.method,
                "confidence": round(float(scan_result.confidence), 3),
                "width": int(width),
                "height": int(height),
                "message": scan_result.message,
                "needs_retake": not scan_result.detected,
            },
            "debug": {
                "stdout": ocr_test.get("stdout", ""),
                "stderr": ocr_test.get("stderr", ""),
            },
        }

    ocr_result = ocr_test["result"]
    parsed = ocr_result.get("parsed", {})
    number = parsed.get("number", "")
    suffix_text = parsed.get("suffix", "")
    rarity = parsed.get("rarity", "")
    energy_name = ocr_result.get("energy", {}).get("name", "")
    ocr_name_text = ocr_result.get("name_text", "")

    if number and suffix_text:
        candidates = fetch_recognition_candidates(
            number=number,
            suffix=suffix_text,
            rarity=rarity,
        )
        candidates = rank_candidates_by_ocr_name(candidates, ocr_name_text)
        lookup_mode = "number"
    elif energy_name:
        candidates = fetch_recognition_candidates(name=energy_name)
        candidates = rank_candidates_by_ocr_name(candidates, ocr_name_text)
        lookup_mode = "energy"
    else:
        candidates = []
        lookup_mode = "none"

    return {
        "ok": True,
        "scan": {
            "detected": scan_result.detected,
            "method": scan_result.method,
            "confidence": round(float(scan_result.confidence), 3),
            "width": int(width),
            "height": int(height),
            "message": scan_result.message,
            "needs_retake": not scan_result.detected,
        },
        "ocr": {
            "bottom_lines": ocr_result.get("bottom_lines", []),
            "bottom_variant_lines": ocr_result.get("bottom_variant_lines", {}),
            "name_lines": ocr_result.get("name_lines", []),
            "parsed": parsed,
            "name_text": ocr_name_text,
            "energy": ocr_result.get("energy", {}),
            "lookup_mode": lookup_mode,
        },
        "cards": {
            "count": len(candidates),
            "results": candidates,
        },
        "debug_images": {
            "input": "/recognition/last-scan/input",
            "normalized": "/recognition/last-scan/normalized",
            "overlay": "/recognition/last-scan/overlay",
            "ocr_bottom": "/recognition/last-scan/ocr-bottom",
            "ocr_bottom_gray": "/recognition/last-scan/ocr-bottom-gray",
            "ocr_bottom_clahe": "/recognition/last-scan/ocr-bottom-clahe",
            "ocr_bottom_adaptive": "/recognition/last-scan/ocr-bottom-adaptive",
            "ocr_bottom_inverted": "/recognition/last-scan/ocr-bottom-inverted",
            "ocr_name": "/recognition/last-scan/ocr-name",
            "ocr_energy": "/recognition/last-scan/ocr-energy",
        },
    }


@app.get("/recognition/last-scan/{image_name}")
def get_last_scan_image(image_name: str):
    allowed_files = {
        "input": LAST_SCAN_DIR / "input.jpeg",
        "normalized": LAST_SCAN_DIR / "normalized.jpeg",
        "overlay": LAST_SCAN_DIR / "overlay.jpeg",
        "ocr-bottom": LAST_SCAN_OCR_DIR / "bottom_info.jpeg",
        "ocr-bottom-gray": LAST_SCAN_OCR_DIR / "bottom_info_gray.jpeg",
        "ocr-bottom-clahe": LAST_SCAN_OCR_DIR / "bottom_info_clahe.jpeg",
        "ocr-bottom-adaptive": LAST_SCAN_OCR_DIR / "bottom_info_adaptive.jpeg",
        "ocr-bottom-inverted": LAST_SCAN_OCR_DIR / "bottom_info_inverted.jpeg",
        "ocr-name": LAST_SCAN_OCR_DIR / "name_area.jpeg",
        "ocr-energy": LAST_SCAN_OCR_DIR / "energy_symbol.jpeg",
    }
    path = allowed_files.get(image_name)

    if path is None or not path.exists():
        return {
            "ok": False,
            "message": "저장된 스캔 이미지가 없습니다. 앱에서 스캔 테스트를 한 번 더 눌러주세요.",
        }

    return FileResponse(path, media_type="image/jpeg")


@app.get("/cards/recognize-candidates")
def recognize_candidates(
    name: str = Query(default=""),
    number: str = Query(default=""),
    suffix: str = Query(default=""),
    rarity: str = Query(default=""),
    set_code: str = Query(default=""),
):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT
            card_id,
            card_group,
            name,
            card_number,
            card_number_main,
            card_number_suffix,
            rarity,
            set_code,
            recognition_key,
            hp,
            card_type,
            category,
            illustrator,
            image_url,
            detail_url
        FROM cards
        WHERE
            (%s = '' OR name ILIKE %s)
            AND (%s = '' OR card_number_main = %s)
            AND (%s = '' OR card_number_suffix = %s)
            AND (%s = '' OR rarity = %s)
            AND (%s = '' OR set_code = %s)
        ORDER BY
            set_code,
            card_number_main,
            rarity
        LIMIT 30;
        """,
        (
            name,
            f"%{name}%",
            number,
            number,
            suffix,
            suffix,
            rarity,
            rarity,
            set_code,
            set_code,
        ),
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return {
        "count": len(rows),
        "query": {
            "name": name,
            "number": number,
            "suffix": suffix,
            "rarity": rarity,
            "set_code": set_code,
        },
        "results": rows,
    }

@app.get("/cards")
def search_cards(name: str = Query(default="")):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT
            card_id,
            card_group,
            name,
            card_number,
            hp,
            card_type,
            category,
            illustrator,
            image_url,
            detail_url
        FROM cards
        WHERE name ILIKE %s
        ORDER BY name
        LIMIT 50;
        """,
        (f"%{name}%",),
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return {
        "count": len(rows),
        "results": rows,
    }


@app.get("/cards/{card_id}")
def get_card(card_id: str):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT
            card_id,
            card_group,
            name,
            card_number,
            hp,
            card_type,
            category,
            illustrator,
            image_url,
            detail_url
        FROM cards
        WHERE card_id = %s;
        """,
        (card_id,),
    )

    row = cur.fetchone()

    cur.close()
    conn.close()

    if row is None:
        return {"message": "card not found"}

    return row
