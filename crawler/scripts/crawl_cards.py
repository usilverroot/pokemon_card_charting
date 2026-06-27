"""
포켓몬코리아 카드 목록 + 상세 페이지 파싱 테스트

현재 목표:
1. 카드 목록 API에서 카드 30개 가져오기
2. 첫 번째 카드 상세 페이지 접근
3. 카드명, 번호, HP, 타입, 이미지 URL 파싱
"""

import json
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup


BASE_URL = "https://pokemoncard.co.kr"
API_URL = f"{BASE_URL}/v2/ajax2_dev2"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://pokemoncard.co.kr/cards",
}

CARD_GROUPS = [
    {
        "group": "pokemon",
        "card_type_num": "1",
        "card_type": "기본,1진화,2진화,기본 포켓몬 ex,고대,미래,V,포켓몬 GX,일격,연격,퓨전,프리즘스타,포켓몬 EX,M진화,BREAK진화,복원,메가진화 ex",
    },
    {
        "group": "trainers",
        "card_type_num": "2",
        "card_type": "아이템,포켓몬의 도구,서포,스타디움",
    },
    {
        "group": "energy",
        "card_type_num": "3",
        "card_type": "기본 에너지",
    },
]


def get_card_list(card_type_num, card_type, page):
    payload = {
        "action": "get_more_cards",
        "limit": str(page),
        "GoodsName": "",
        "CardTypeNum": card_type_num,
        "CardType": card_type,
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

    json_start = response.text.find("{")
    clean_text = response.text[json_start:]
    data = json.loads(clean_text)

    return data.get("result", {})


def save_html(card_id, html):
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)

    path = raw_dir / f"detail_{card_id}.html"
    path.write_text(html, encoding="utf-8")

    return path


def parse_card_detail(card_id, group):
    detail_url = f"{BASE_URL}/cards/detail/{card_id}"

    response = requests.get(
        detail_url,
        headers=HEADERS,
        timeout=10,
    )

    #save_html(card_id, response.text)

    soup = BeautifulSoup(response.text, "lxml")

    image_tag = soup.select_one("img.feature_image")
    image_url = image_tag.get("src") if image_tag else None

    card_number_tag = soup.select_one("span.p_num")
    card_number = card_number_tag.get_text(" ", strip=True) if card_number_tag else None

    name_tag = soup.select_one("span.card-hp.title")
    name = name_tag.get_text(" ", strip=True) if name_tag else None

    hp_tag = soup.select_one("span.hp_num")
    hp = hp_tag.get_text(" ", strip=True) if hp_tag else None

    type_tag = soup.select_one(".header img.type_b")
    card_type = type_tag.get("title") if type_tag else None

    category_tag = soup.select_one("div.pokemon-info")
    category = category_tag.get_text(" ", strip=True) if category_tag else None

    illustrator_tag = soup.select_one("p.illustrator")
    illustrator = illustrator_tag.get_text(" ", strip=True) if illustrator_tag else None

    return {
        "card_id": card_id,
        "group": group,
        "name": name,
        "card_number": card_number,
        "hp": hp,
        "type": card_type,
        "category": category,
        "illustrator": illustrator,
        "image_url": image_url,
        "detail_url": detail_url,
    }


def main():
    cards = []
    seen_card_ids = set()
    failed_cards = []

    for group_info in CARD_GROUPS:
        group = group_info["group"]
        card_type_num = group_info["card_type_num"]
        card_type = group_info["card_type"]

        print(f"\n=== {group} 수집 시작 ===")

        for page in range(0, 20):
            print(f"\n페이지 수집중: group={group}, page={page}")

            card_list = get_card_list(
                card_type_num=card_type_num,
                card_type=card_type,
                page=page,
            )

            if not card_list:
                print("더 이상 카드 없음. 다음 그룹으로 이동.")
                break

            for item in card_list.values():
                card_id = item["CardNum"]

                if card_id in seen_card_ids:
                    continue

                seen_card_ids.add(card_id)

                print(f"상세 수집중: {card_id}")

                try:
                    parsed_card = parse_card_detail(card_id, group)
                    cards.append(parsed_card)
                    time.sleep(0.5)

                except Exception as e:
                    failed_cards.append(card_id)

                    print(f"에러 발생: {card_id}")
                    print(e)
            time.sleep(1)

    print(f"\n총 수집 카드 수: {len(cards)}")
    print(f"실패 카드 수: {len(failed_cards)}")
    print("실패 카드 목록:", failed_cards)
    
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(cards)
    csv_path = output_dir / "cards_all_sample.csv"

    df.to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"\nCSV 저장 완료: {csv_path}")


if __name__ == "__main__":
    main()