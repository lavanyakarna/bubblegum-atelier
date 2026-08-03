"""
Sorts Kaggle's "Fashion Product Images" dataset into 5 folders:
shoes, bags, clothing, accessories, makeup
Women's/girls' items only, to match the Bubblegum Atelier theme.

Run this from inside the smart-retail-ai folder:
    python organize_dataset.py
"""
import os
import shutil
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE, "data", "fashion-dataset", "styles.csv")
IMAGES_DIR = os.path.join(BASE, "data", "fashion-dataset", "images")
OUT_DIR = os.path.join(BASE, "data", "product_images")

MAX_PER_CATEGORY = 300

def map_category(row):
    gender = str(row.get("gender", "")).lower()
    if gender not in ("women", "girls"):
        return None

    master = str(row.get("masterCategory", "")).lower()
    sub = str(row.get("subCategory", "")).lower()

    if master == "footwear":
        return "shoes"
    if sub == "bags":
        return "bags"
    if master == "apparel":
        return "clothing"
    if master == "personal care" and ("makeup" in sub or "lip" in sub or "eye" in sub or "nail" in sub):
        return "makeup"
    if master == "accessories":
        return "accessories"
    return None


def main():
    df = pd.read_csv(CSV_PATH, on_bad_lines="skip")
    counts = {"shoes": 0, "bags": 0, "clothing": 0, "accessories": 0, "makeup": 0}

    for cat in counts:
        os.makedirs(os.path.join(OUT_DIR, cat), exist_ok=True)

    copied = 0
    for _, row in df.iterrows():
        category = map_category(row)
        if category is None or counts[category] >= MAX_PER_CATEGORY:
            continue

        src = os.path.join(IMAGES_DIR, f"{row['id']}.jpg")
        if not os.path.exists(src):
            continue

        dst = os.path.join(OUT_DIR, category, f"{row['id']}.jpg")
        shutil.copyfile(src, dst)
        counts[category] += 1
        copied += 1

    print(f"Copied {copied} images.")
    print(counts)


if __name__ == "__main__":
    main()