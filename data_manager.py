import os
import json

def save_data_as_json(name, cid, data, folder="data"):
    if not os.path.exists(folder):
        os.makedirs(folder)
    filename = f"{name}_{cid}.json"
    filepath = os.path.join(folder, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
