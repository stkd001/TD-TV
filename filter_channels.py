import json
import os

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

# Individual channels to remove
BLOCKED_CHANNELS = {
    "QVC",
    "HSN",
    "ShopHQ"
}

CATALOG_FILE = "catalog/tv/all.json"
STREAM_FOLDER = "stream/tv"


def keep_channel(channel):
    name = channel.get("name", "").strip()
    genres = channel.get("genres", [])

    if name in BLOCKED_CHANNELS:
        return False

    if "Latino" in genres:
        return False

    return any(genre in ALLOWED_GENRES for genre in genres)


def format_stream_name(original_name):
    """
    Convert upstream quality labels into consistent
    TD-TV resolution labels.
    """

    quality = (original_name or "").strip().upper()

    # 4K
    if quality in {"4K", "UHD", "2160P"}:
        return "✦ 4K"

    # 1080P and below are Sunroom
    if quality in {"FHD", "1080P"}:
        return "☀️ 1080P Sunroom"

    if quality in {"HD", "720P"}:
        return "☀️ 720P Sunroom"

    if quality in {"SD", "480P"}:
        return "☀️ 480P Sunroom"

    if quality == "360P":
        return "☀️ 360P Sunroom"

    if quality == "240P":
        return "☀️ 240P Sunroom"

    # Anything we don't recognize
    return f"☀️ {original_name} Sunroom" if original_name else "☀️ Sunroom"


def format_stream_files():
    files_processed = 0
    streams_formatted = 0

    if not os.path.isdir(STREAM_FOLDER):
        print(f"Stream folder not found: {STREAM_FOLDER}")
        return

    for filename in os.listdir(STREAM_FOLDER):

        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(STREAM_FOLDER, filename)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            streams = data.get("streams", [])

            if not streams:
                continue

            changed = False

            for stream in streams:
                original_name = stream.get("name", "")
                original_description = stream.get("description", "").strip()

                # Format the resolution/name
                stream["name"] = format_stream_name(original_name)

                # Show TD-TV first, then preserve the original
                # USA TV Next stream description underneath
                if original_description:
                    stream["description"] = (
                        f"🔴 LIVE • TD-TV\n"
                        f"{original_description}"
                    )
                else:
                    stream["description"] = "🔴 LIVE • TD-TV"

                changed = True
                streams_formatted += 1

            if changed:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(
                        data,
                        f,
                        indent=2,
                        ensure_ascii=False
                    )

                files_processed += 1

        except (json.JSONDecodeError, OSError) as error:
            print(f"Could not process {filename}: {error}")

    print(f"Stream files formatted: {files_processed}")
    print(f"Individual streams formatted: {streams_formatted}")

for stream in streams:

    original_name = stream.get("name", "")
    original_description = stream.get("description", "").strip()

    # Format the resolution/name
    stream["name"] = format_stream_name(original_name)

    # Keep the original USA TV Next stream description
    # and display it beneath TD-TV
    if original_description:
        stream["description"] = (
            f"🔴 LIVE • TD-TV\n"
            f"{original_description}"
        )
    else:
        stream["description"] = "🔴 LIVE • TD-TV"

    changed = True
    streams_formatted += 1

            if changed:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(
                        data,
                        f,
                        indent=2,
                        ensure_ascii=False
                    )

                files_processed += 1

        except (json.JSONDecodeError, OSError) as error:
            print(f"Could not process {filename}: {error}")

    print(f"Stream files formatted: {files_processed}")
    print(f"Individual streams formatted: {streams_formatted}")


# -----------------------------
# Filter channel catalog
# -----------------------------

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
    json.dump(
        catalog,
        f,
        indent=2,
        ensure_ascii=False
    )

print(f"Original channels: {original_count}")
print(f"Filtered channels: {new_count}")
print(f"Removed channels: {original_count - new_count}")

# -----------------------------
# Format TD-TV streams
# -----------------------------

format_stream_files()
