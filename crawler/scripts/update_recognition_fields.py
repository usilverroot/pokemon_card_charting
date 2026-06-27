import re

import psycopg2


DB_CONFIG = {
    "dbname": "pokemon_card_db",
    "user": "a123",
    "host": "localhost",
    "port": 5432,
}


def extract_set_code(image_url):
    if not image_url:
        return None

    match = re.search(
        r"/wmimages/[^/]+/([^/]+)/",
        image_url
    )

    if match:
        return match.group(1)

    return None


def parse_card_number(card_number):
    if not card_number:
        return None, None, None

    card_number = card_number.strip()

    parts = card_number.split()

    number_part = parts[0]

    rarity = None

    if len(parts) > 1:
        rarity = parts[1]

    if "/" in number_part:
        main_num, suffix_num = number_part.split("/", 1)
    else:
        main_num = number_part
        suffix_num = None

    return main_num, suffix_num, rarity


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            card_id,
            card_number,
            image_url
        FROM cards
    """)

    rows = cur.fetchall()

    updated_count = 0

    for card_id, card_number, image_url in rows:

        main_num, suffix_num, rarity = parse_card_number(card_number)

        set_code = extract_set_code(image_url)

        recognition_key = "_".join(
            filter(
                None,
                [
                    set_code,
                    main_num,
                    suffix_num,
                    rarity,
                ]
            )
        )

        cur.execute(
            """
            UPDATE cards
            SET
                card_number_main = %s,
                card_number_suffix = %s,
                rarity = %s,
                set_code = %s,
                recognition_key = %s
            WHERE card_id = %s
            """,
            (
                main_num,
                suffix_num,
                rarity,
                set_code,
                recognition_key,
                card_id,
            ),
        )

        updated_count += 1

    conn.commit()

    print(f"업데이트 완료: {updated_count}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()