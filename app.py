import os
import re

import pandas as pd
from flask import Flask, jsonify, render_template

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "meals.csv")
ENCODINGS = ("utf-8-sig", "utf-8", "cp949", "euc-kr")
BR_PATTERN = re.compile(r"<br\s*/?>", re.IGNORECASE)

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
try:
    app.json.ensure_ascii = False
except AttributeError:
    pass


def read_csv_with_fallback(path):
    last_error = None
    for enc in ENCODINGS:
        try:
            return pd.read_csv(path, encoding=enc, dtype=str)
        except (UnicodeDecodeError, UnicodeError) as e:
            last_error = e
    raise last_error


def format_date(value):
    digits = re.sub(r"\D", "", str(value))
    if len(digits) >= 8:
        digits = digits[:8]
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return str(value).strip()


def parse_menu(value):
    if pd.isna(value):
        return []
    items = BR_PATTERN.split(str(value))
    return [re.sub(r"\s+", " ", item).strip() for item in items if item and item.strip()]


def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def load_lunch_meals():
    df = read_csv_with_fallback(CSV_PATH)
    df.columns = [str(c).strip() for c in df.columns]

    required = ["급식일자", "식사명", "요리명", "칼로리정보"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"meals.csv에 필수 컬럼이 없습니다: {missing}")

    df["식사명"] = df["식사명"].astype(str).str.strip()
    lunch = df[df["식사명"] == "중식"].copy()

    lunch["date"] = lunch["급식일자"].apply(format_date)
    lunch = lunch.sort_values("date")

    return [
        {
            "date": row["date"],
            "menu": parse_menu(row["요리명"]),
            "kcal": clean_text(row["칼로리정보"]),
        }
        for _, row in lunch.iterrows()
    ]


try:
    LUNCH_MEALS = load_lunch_meals()
    LOAD_ERROR = None
except Exception as e:
    LUNCH_MEALS = []
    LOAD_ERROR = str(e)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/meals")
def get_meals():
    if LOAD_ERROR:
        return jsonify({"error": LOAD_ERROR}), 500
    return jsonify(LUNCH_MEALS)


if __name__ == '__main__':
    import os
    # 외부 포트 환경에 맞춰 서버를 0.0.0.0으로 완전 개방하는 설정입니다.
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)