import json

# Channel categories Tyler wants to keep
ALLOWED_GENRES = {
    "Local",
    "News",
    "Sports",
    "Entertainment",
    "Lifestyle",
    "Kids",
    "Documentaries",
    "Music"
}

# Individual channels to remove even if
# they belong to one of the categories above
BLOCKED_CHANNELS = {
    "QVC",
    "HSN",
    "ShopHQ"
}

CATALOG_FILE = "catalog/tv/all.json"


def keep_channel(channel):
    name = channel.get("name", "").strip()
    genres = channel.get("genres", [])

    # Remove specifically blocked channels
    if name in BLOCKED_CHANNELS:
        return False

    # Remove Latino channels
    if "Latino" in genres:
        return False

    # Keep channels belonging to one of our categories
    return any(genre in ALLOWED_GENRES for genre in genres)


with open(CATALOG_FILE, "r", encoding="utf-8") as f:
    catalog = json.load(f)

original_count = len(catalog.get("metas", []))

catalog["metas"] = [
    channel
    for channel in catalog.get("metas", [])
    if keep_channel(channel)
]

new_count = len(catalog["metas"])

with open(CATALOG_FILE, "w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)

print(f"Original channels: {original_count}")
print(f"Filtered channels: {new_count}")
print(f"Removed channels: {original_count - new_count}")
