import time
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests


CSV_PATH = Path("data/processed/cards_all_sample.csv")
IMAGE_DIR = Path("data/images")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
}


def get_image_extension(image_url):
    """
    이미지 URL에서 확장자를 추출한다.
    예: .../M-P_041.png?w=512 -> .png
    """
    path = urlparse(image_url).path
    suffix = Path(path).suffix

    if suffix:
        return suffix

    return ".png"


def download_image(card_id, image_url):
    """
    카드 이미지 1장을 다운로드한다.
    저장 파일명은 card_id 기준으로 한다.
    """
    if not image_url:
        return False

    extension = get_image_extension(image_url)
    save_path = IMAGE_DIR / f"{card_id}{extension}"

    # 이미 다운로드된 파일이면 다시 받지 않음
    if save_path.exists():
        print(f"이미 존재: {save_path}")
        return True

    response = requests.get(
        image_url,
        headers=HEADERS,
        timeout=15,
    )

    if response.status_code != 200:
        print(f"다운로드 실패: {card_id}, status={response.status_code}")
        return False

    save_path.write_bytes(response.content)

    print(f"저장 완료: {save_path}")
    return True


def main():
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(CSV_PATH)

    success_count = 0
    fail_count = 0
    failed_cards = []

    for _, row in df.iterrows():
        card_id = str(row["card_id"]).strip()
        image_url = str(row["image_url"]).strip()

        try:
            success = download_image(card_id, image_url)

            if success:
                success_count += 1
            else:
                fail_count += 1
                failed_cards.append(card_id)

            time.sleep(0.2)

        except Exception as e:
            fail_count += 1
            failed_cards.append(card_id)

            print(f"에러 발생: {card_id}")
            print(e)

    print("\n=== 다운로드 결과 ===")
    print(f"성공: {success_count}")
    print(f"실패: {fail_count}")
    print(f"실패 카드: {failed_cards}")


if __name__ == "__main__":
    main()