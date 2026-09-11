import json, os, shutil

with open("data/products.json") as f:
    products = json.load(f)["products"]

os.makedirs("data/products", exist_ok=True)

for p in products:
    folder = os.path.join("data", "product_images", p["category"])
    files = sorted(os.listdir(folder))
    src = os.path.join(folder, files[0])
    dst = os.path.join("data", "products", os.path.basename(p["image"]))
    shutil.copy(src, dst)
    print("copied", p["category"], "->", dst)

print("Done! All product images copied.")