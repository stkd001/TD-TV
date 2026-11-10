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
    # Shopping
    "QVC",
    "HSN",
    "ShopHQ",

    # Out-of-market regional sports
    "Altitude Sports",
    "Chicago Sports Network",
    "FanDuel Florida",
    "FanDuel Indiana",
    "FanDuel North",
    "FanDuel Ohio",
    "FanDuel Oklahoma",
    "FanDuel SoCal",
    "FanDuel South",
    "FanDuel Southeast",
    "FanDuel Sun",
    "FanDuel Wisconsin",
    "Marquee Sports Network",
    "MSG",
    "NBC Sports Bay Area",
    "NBC Sports Boston",
    "NBC Sports California",
    "NBC Sports Philadelphia",
    "NESN",
    "Spectrum SportsNet",
    "Spectrum SportsNet LA",
    "SportsNet New York",
    "YES Network",

    # Niche sports
    "Gol TV",
    "Pursuit ",
    "Racer Network",

    # Lower-priority entertainment/lifestyle
    "AWE",
    "BET Her",
    "Bounce",
    "Buzzr",
    "Comedy TV",
    "Discovery Life",
    "FYI",
    "Hallmark Family",
    "Hallmark Mystery",
    "Ion Mystery",
    "Lifetime Movie Network",
    "Oprah Winfrey Network (OWN)",
    "Outdoor Channel",
    "TV One",
    "Vice TV",
    "We TV",

    # Lower-priority kids/music
    "TeenNick",
    "Toonami Aftermath (East)",
    "Universal Kids",

    # Other
    "C-SPAN 1"
}

CATALOG_FILE = "catalog/tv/all.json"
STREAM_FOLDER = "stream/tv"
CATALOG_FOLDER = "catalog/tv"

GENRE_CATALOGS = {
    "Local": "local.json",
    "News": "news.json",
    "Sports": "sports.json",
    "Entertainment": "entertainment.json",
    "Lifestyle": "lifestyle.json",
    "Kids": "kids.json",
    "Documentaries": "documentaries.json",
    "Music": "music.json",
}
CHANNEL_STREAM_BLOCKS = {
    "ABC": {
        "abc-nsw",
        "abc-qld",
        "abc-sa",
        "abc-tv-plus",
        "weather_in_90_seconds",
        "news_in_90_seconds",
        "business_in_90_seconds",
        "sport_in_90_seconds",
        "radio-abc",
    },

    "CNN": {
        "cnn_news18",
        "cnn-news18",
        "cnnturk",
        "cnn_turk",
        "cnnnow-samsungin",
        "cnnfast",
    },

    "TNT": {
        "tnt-novelas",
        "tnt_novelas",
        "/arg/tnt",
        "douyu",
    },

    "CNBC": {
        "cnbc_bazaar",
        "cnbc-bazaar",
        "cnbc_awaaz",
        "cnbc-awaaz",
        "cnbc_tv18",
        "cnbc-tv18",
    },

    "BBC News": {
        "bbc_arabic",
        "bbc-arabic",
    },

    "Disney Channel": {
        "/arg/disney_channel",
        "/arg/disney-channel",
    },

    "MTV": {
        "mtv-lebanon",
        "mumbai-edge",
        "marketingregion=de",
        "mtvridiculousness",
        "mtv-the-shores",
    },
}
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
    
def stream_score(stream):
    """
    Score streams so TD-TV can rank the most desirable
    stream first without removing alternatives.
    """
    score = 0

    original_name = str(stream.get("name", "")).upper()

    # Resolution
    if "4K" in original_name or "2160" in original_name or "UHD" in original_name:
        score += 400
    elif "1080" in original_name or "FHD" in original_name:
        score += 300
    elif "720" in original_name or original_name == "HD":
        score += 200
    elif "480" in original_name or original_name == "SD":
        score += 100
    elif "360" in original_name:
        score += 50
    elif "240" in original_name:
        score += 25

    # FPS, if upstream provides it
    try:
        fps = float(stream.get("fps", 0) or 0)

        if fps >= 60:
            score += 40
        elif fps >= 50:
            score += 30
        elif fps >= 30:
            score += 20
    except (ValueError, TypeError):
        pass

    # Bitrate, if upstream provides it
    try:
        bitrate = float(stream.get("bitrate", 0) or 0)

        if bitrate >= 8_000_000:
            score += 40
        elif bitrate >= 5_000_000:
            score += 30
        elif bitrate >= 3_000_000:
            score += 20
        elif bitrate >= 1_000_000:
            score += 10
    except (ValueError, TypeError):
        pass

    return score

def should_remove_stream(channel_name, url):
    """
    Remove a stream only when its URL contains a known
    mismatched regional or channel variant.
    """

    channel_name = (channel_name or "").strip()
    url_lower = (url or "").lower()

    blocked_patterns = CHANNEL_STREAM_BLOCKS.get(
        channel_name,
        set()
    )

    return any(
        pattern.lower() in url_lower
        for pattern in blocked_patterns
    )
def format_stream_files(selected_channel_ids):
    channels_with_streams = 0
    channels_without_streams = 0
    streams_formatted = 0
    audio_removed = 0
    duplicates_removed = 0
    mismatched_streams_removed = 0
    remaining_by_channel = {}
    mismatched_by_channel = {}

    if not os.path.isdir(STREAM_FOLDER):
        print(f"Stream folder not found: {STREAM_FOLDER}")
        return

    for channel_id, channel_name in selected_channels.items():
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
                
                # Remove clearly mismatched regional/channel variants
                if should_remove_stream(channel_name, url):
                    mismatched_streams_removed += 1

                    mismatched_by_channel[channel_name] = (
                        mismatched_by_channel.get(channel_name, 0) + 1
                    )

                    continue
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

            # Rank best-quality streams first
            cleaned_streams.sort(
                key=stream_score,
                reverse=True
            )

            # Record TD-TV's preferred stream for inspection
            if cleaned_streams:
                best = cleaned_streams[0]

                print(
                    f"BEST | {channel_name} | "
                    f"{best.get('name', 'Unknown')} | "
                    f"Score: {stream_score(best)}"
                )

            data["streams"] = cleaned_streams
            remaining_by_channel[channel_name] = len(cleaned_streams)
            
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
    print(f"Mismatched streams removed: {mismatched_streams_removed}")
    if mismatched_by_channel:
        print("")
        print("Mismatched streams removed by channel:")

        for channel_name, count in sorted(
            mismatched_by_channel.items()
        ):
            print(f"  {channel_name}: {count}")

    print("")
    print("Remaining streams for cleaned channels:")

    for channel_name in sorted(CHANNEL_STREAM_BLOCKS):
        remaining = remaining_by_channel.get(channel_name, 0)
        print(f"  {channel_name}: {remaining}")

    print(f"Duplicate URLs removed: {duplicates_removed}")
    print("==========================================")

def create_genre_catalogs(catalog):
    """
    Create separate TD-TV catalog files for each genre
    using only channels that survived our main filter.
    """

    genre_counts = {}

    for genre, filename in GENRE_CATALOGS.items():
        genre_channels = []

        for channel in catalog.get("metas", []):
            genres = channel.get("genres", [])

            if genre in genres:
                genre_channels.append(channel)

        genre_catalog = {
            "metas": genre_channels
        }

        output_path = os.path.join(
            CATALOG_FOLDER,
            filename
        )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                genre_catalog,
                f,
                indent=2,
                ensure_ascii=False
            )

        genre_counts[genre] = len(genre_channels)

    print("")
    print("========== TD-TV CATALOGS ================")

    for genre, count in genre_counts.items():
        print(f"{genre}: {count} channels")

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
create_genre_catalogs(catalog)

print(f"Original channels: {original_count}")
print(f"Filtered channels: {new_count}")
print(f"Removed channels: {original_count - new_count}")

# -----------------------------
# Format TD-TV streams
# -----------------------------

selected_channels = {
    channel.get("id"): channel.get("name", "").strip()
    for channel in catalog["metas"]
    if channel.get("id")
}

format_stream_files(selected_channels)
