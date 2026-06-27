import pandas as pd
import psycopg2


CSV_PATH = "data/processed/cards_clean.csv"

DB_CONFIG = {
    "dbname": "pokemon_card_db",
    "user": "a123",
    "host": "localhost",
    "port": 5432,
}


def main():
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    for _, row in df.iterrows():
        cur.execute(
            """
            INSERT INTO cards (
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
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (card_id) DO UPDATE SET
                card_group = EXCLUDED.card_group,
                name = EXCLUDED.name,
                card_number = EXCLUDED.card_number,
                hp = EXCLUDED.hp,
                card_type = EXCLUDED.card_type,
                category = EXCLUDED.category,
                illustrator = EXCLUDED.illustrator,
                image_url = EXCLUDED.image_url,
                detail_url = EXCLUDED.detail_url;
            """,
            (
                str(row["card_id"]),
                str(row["group"]),
                str(row["name"]),
                str(row["card_number"]),
                str(row["hp"]) if pd.notna(row["hp"]) else None,
                str(row["type"]) if pd.notna(row["type"]) else None,
                str(row["category"]) if pd.notna(row["category"]) else None,
                str(row["illustrator"]) if pd.notna(row["illustrator"]) else None,
                str(row["image_url"]),
                str(row["detail_url"]),
            ),
        )

    conn.commit()
    cur.close()
    conn.close()

    print(f"DB 적재 완료: {len(df)}장")


if __name__ == "__main__":
    main()