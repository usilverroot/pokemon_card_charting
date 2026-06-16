"""
포켓몬코리아 카드 목록 + 상세 페이지 파싱 테스트

현재 목표:
1. 카드 목록 API에서 카드 30개 가져오기
2. 첫 번째 카드 상세 페이지 접근
3. 카드명, 번호, HP, 타입, 이미지 URL 파싱
"""

import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup

import pandas as pd

BASE_URL = "https://pokemoncard.co.kr"
IMAGE_BASE_URL = "https://cards.image.pokemonkorea.co.kr"
API_URL = f"{BASE_URL}/v2/ajax2_dev2"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://pokemoncard.co.kr/cards",
}


def get_card_list():
    payload = {
        "action": "get_more_cards",
        "limit": "0",
        "GoodsName": "",
        "CardTypeNum": "1",
        "CardType": "기본",
        "CardMonType": "풀,불꽃,물,번개,초,격투,악,강철,페어리,드래곤,무색,all",
        "Weakness": "풀,불꽃,물,번개,초,격투,악,강철,페어리,드래곤,무색,all",
        "Resistance": "풀,불꽃,물,번개,초,격투,악,강철,페어리,드래곤,무색,all",
        "TechErg": "풀,불꽃,물,번개,초,격투,악,강철,페어리,드래곤,무색,all",
        "ability_label1": "",
        "hp": "0,999",
        "retreat": "0,5",
        "order": "DESC",
        "orderby": "order_num",
    }

    response = requests.post(
        API_URL,
        headers=HEADERS,
        data=payload,
        timeout=10,
    )

    print("list status code:", response.status_code)

    json_start = response.text.find("{")
    clean_text = response.text[json_start:]

    data = json.loads(clean_text)

    result = data.get("result", {})
    print("card count:", len(result))

    return result


def save_html(card_id, html):
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)

    path = raw_dir / f"detail_{card_id}.html"
    path.write_text(html, encoding="utf-8")

    return path


def parse_card_detail(card_id):
    detail_url = f"{BASE_URL}/cards/detail/{card_id}"

    response = requests.get(
        detail_url,
        headers=HEADERS,
        timeout=10,
    )

    print("detail status code:", response.status_code)

    save_path = save_html(card_id, response.text)
    print("detail html saved:", save_path)

    soup = BeautifulSoup(response.text, "lxml")

    image_tag = soup.select_one("img.feature_image")
    image_url = image_tag.get("src") if image_tag else None

    card_number_tag = soup.select_one("span.p_num")
    card_number = (
        card_number_tag.get_text(" ", strip=True)
        if card_number_tag
        else None
    )

    name_tag = soup.select_one("span.card-hp.title")
    name = (
        name_tag.get_text(" ", strip=True)
        if name_tag
        else None
    )

    hp_tag = soup.select_one("span.hp_num")
    hp = (
        hp_tag.get_text(" ", strip=True)
        if hp_tag
        else None
    )

    type_tag = soup.select_one(".header img.type_b")
    card_type = (
        type_tag.get("title")
        if type_tag
        else None
    )

    category_tag = soup.select_one("div.pokemon-info")
    category = (
        category_tag.get_text(" ", strip=True)
        if category_tag
        else None
    )

    illustrator_tag = soup.select_one("p.illustrator")
    illustrator = (
        illustrator_tag.get_text(" ", strip=True)
        if illustrator_tag
        else None
    )

    parsed_card = {
        "card_id": card_id,
        "name": name,
        "card_number": card_number,
        "hp": hp,
        "type": card_type,
        "category": category,
        "illustrator": illustrator,
        "image_url": image_url,
        "detail_url": detail_url,
    }

    return parsed_card


def main():
    card_list = get_card_list()

    if not card_list:
        print("카드 목록이 비어 있습니다.")
        return

    cards = []

    for item in card_list.values():

        card_id = item["CardNum"]

        print(f"\n수집중: {card_id}")

        try:
            parsed_card = parse_card_detail(card_id)
            cards.append(parsed_card)

        except Exception as e:
            print(f"에러 발생: {card_id}")
            print(e)

    print(f"\n총 수집 카드 수: {len(cards)}")

    for card in cards[:3]:
        print(json.dumps(card, ensure_ascii=False, indent=2))

    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(cards)

    csv_path = output_dir / "cards_sample.csv"

    df.to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"\nCSV 저장 완료: {csv_path}")


if __name__ == "__main__":
    main()