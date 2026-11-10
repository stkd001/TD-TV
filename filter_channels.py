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
    TD-TV display labels without overstating resolution.
    """

    quality = (original_name or "").strip().upper()

    if quality in {"4K", "UHD", "2160P"}:
        return "✦ 4K"

    if quality in {"FHD", "1080P"}:
        return "☀️ 1080P Sunroom"

    if quality in {"HD", "720P"}:
        return "☀️ 720P Sunroom"

    if quality == "SD":
        return "☀️ SD Sunroom"

    if quality == "480P":
        return "☀️ 480P Sunroom"

    if quality == "360P":
        return "☀️ 360P Sunroom"

    if quality == "240P":
        return "☀️ 240P Sunroom"

    return f"☀️ {original_name} Sunroom" if original_name else "🌞 Sunroom"


def format_stream_files(selected_channel_ids):
    channels_with_streams = 0
    channels_without_streams = 0
    streams_formatted = 0
    audio_removed = 0
    duplicates_removed = 0

    if not os.path.isdir(STREAM_FOLDER):
        print(f"Stream folder not found: {STREAM_FOLDER}")
        return

    for channel_id in selected_channel_ids:
        filename = f"{channel_id}.json"
        filepath = os.path.join(STREAM_FOLDER, filename)

        # Selected channel has no stream file
        if not os.path.isfile(filepath):
            channels_without_streams += 1
            continue

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            streams = data.get("streams", [])

            if not streams:
                channels_without_streams += 1
                continue

            cleaned_streams = []
            seen_urls = set()

            for stream in streams:
                original_name = stream.get("name", "").strip()
                original_description = stream.get("description", "").strip()
                url = stream.get("url", "").strip()

                # Remove audio-only sources
                if original_name.upper() == "AUDIO":
                    audio_removed += 1
                    continue

                # Ignore streams without a playable URL
                if not url:
                    continue

                # Remove exact duplicate URLs
                if url in seen_urls:
                    duplicates_removed += 1
                    continue

                seen_urls.add(url)

                # Apply TD-TV resolution formatting
                stream["name"] = format_stream_name(original_name)

                # Add TD-TV identification while preserving
                # the original upstream stream description
                if original_description:
                    stream["description"] = (
                        f"🔴 LIVE • TD-TV\n"
                        f"{original_description}"
                    )
                else:
                    stream["description"] = "🔴 LIVE • TD-TV"

                cleaned_streams.append(stream)
                streams_formatted += 1

            data["streams"] = cleaned_streams

            # Count the channel based on streams remaining
            # after TD-TV cleanup
            if cleaned_streams:
                channels_with_streams += 1
            else:
                channels_without_streams += 1

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(
                    data,
                    f,
                    indent=2,
                    ensure_ascii=False
                )

        except (json.JSONDecodeError, OSError) as error:
            print(f"Could not process {filename}: {error}")
            channels_without_streams += 1

    print("")
    print("========== TD-TV UPDATE SUMMARY ==========")
    print(f"Channels selected: {len(selected_channel_ids)}")
    print(f"Channels with video streams: {channels_with_streams}")
    print(f"Channels without video streams: {channels_without_streams}")
    print(f"Video streams retained: {streams_formatted}")
    print(f"Audio streams removed: {audio_removed}")
    print(f"Duplicate URLs removed: {duplicates_removed}")
    print("==========================================")


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

selected_channel_ids = {
    channel.get("id")
    for channel in catalog["metas"]
    if channel.get("id")
}

format_stream_files(selected_channel_ids)
