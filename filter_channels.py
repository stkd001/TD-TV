import json
import os


# ============================================================
# TD-TV CONFIGURATION
# ============================================================

CATALOG_FILE = "catalog/tv/all.json"
STREAM_FOLDER = "stream/tv"
CATALOG_FOLDER = "catalog/tv"


ALLOWED_GENRES = {
    "News",
    "Sports",
    "Entertainment",
    "Lifestyle",
    "Kids",
    "Documentaries",
}


GENRE_CATALOGS = {
    "News": "news.json",
    "Sports": "sports.json",
    "Entertainment": "entertainment.json",
    "Lifestyle": "lifestyle.json",
    "Kids": "kids.json",
    "Documentaries": "documentaries.json"
}


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

    # Lower-priority kids
    "TeenNick",
    "Toonami Aftermath (East)",
    "Universal Kids",

    # Other
    "C-SPAN 1",
}


# Known mismatched streams that sometimes appear under
# otherwise valid TD-TV channels.
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


# ============================================================
# CHANNEL FILTERING
# ============================================================

def keep_channel(channel):
    name = channel.get("name", "").strip()
    genres = channel.get("genres", [])

    return (
        name not in BLOCKED_CHANNELS
        and "Latino" not in genres
        and any(genre in ALLOWED_GENRES for genre in genres)
    )


# ============================================================
# STREAM FORMATTING
# ============================================================

def format_stream_name(name):
    quality = (name or "").strip().upper()

    labels = {
        "4K": "✦ 4K",
        "UHD": "✦ 4K",
        "2160P": "✦ 4K",
        "FHD": "☀️ 1080P Sunroom",
        "1080P": "☀️ 1080P Sunroom",
        "HD": "☀️ 720P Sunroom",
        "720P": "☀️ 720P Sunroom",
        "SD": "☀️ SD Sunroom",
        "480P": "☀️ 480P Sunroom",
        "360P": "☀️ 360P Sunroom",
        "240P": "☀️ 240P Sunroom",
    }

    if quality in labels:
        return labels[quality]

    return f"☀️ {name} Sunroom" if name else "🌞 Sunroom"


def stream_score(stream):
    """
    Higher-resolution streams sort first.
    """

    name = str(stream.get("name", "")).upper()

    if any(x in name for x in ("4K", "2160", "UHD")):
        score = 400
    elif "1080" in name or "FHD" in name:
        score = 300
    elif "720" in name or " HD " in f" {name} ":
        score = 200
    elif "480" in name or "SD" in name:
        score = 100
    elif "360" in name:
        score = 50
    elif "240" in name:
        score = 25
    else:
        score = 0

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
    url = (url or "").lower()

    return any(
        pattern.lower() in url
        for pattern in CHANNEL_STREAM_BLOCKS.get(channel_name, set())
    )


# ============================================================
# STREAM CLEANUP
# ============================================================

def clean_streams(selected_channels):

    stats = {
        "with_streams": 0,
        "without_streams": 0,
        "retained": 0,
        "audio_removed": 0,
        "duplicates_removed": 0,
        "mismatched_removed": 0,
    }

    remaining = {}

    for channel_id, channel_name in selected_channels.items():

        filepath = os.path.join(
            STREAM_FOLDER,
            f"{channel_id}.json"
        )

        if not os.path.isfile(filepath):
            stats["without_streams"] += 1
            continue

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            cleaned = []
            seen_urls = set()

            for stream in data.get("streams", []):

                original_name = stream.get("name", "").strip()
                description = stream.get("description", "").strip()
                url = stream.get("url", "").strip()

                if not url:
                    continue

                if original_name.upper() == "AUDIO":
                    stats["audio_removed"] += 1
                    continue

                if url in seen_urls:
                    stats["duplicates_removed"] += 1
                    continue

                if should_remove_stream(channel_name, url):
                    stats["mismatched_removed"] += 1
                    continue

                seen_urls.add(url)

                stream["name"] = format_stream_name(original_name)

                stream["description"] = "🔴 LIVE • TD-TV"

                if description:
                    stream["description"] += f"\n{description}"

                cleaned.append(stream)

            cleaned.sort(
                key=stream_score,
                reverse=True
            )


            data["streams"] = cleaned
            remaining[channel_name] = len(cleaned)

            if cleaned:
                stats["with_streams"] += 1
                stats["retained"] += len(cleaned)
            else:
                stats["without_streams"] += 1

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(
                    data,
                    f,
                    indent=2,
                    ensure_ascii=False
                )

        except (json.JSONDecodeError, OSError) as error:
            print(f"Could not process {channel_name}: {error}")
            stats["without_streams"] += 1

    print("")
    print("========== TD-TV UPDATE SUMMARY ==========")
    print(f"Channels selected: {len(selected_channels)}")
    print(f"Channels with streams: {stats['with_streams']}")
    print(f"Channels without streams: {stats['without_streams']}")
    print(f"Streams retained: {stats['retained']}")
    print(f"Audio streams removed: {stats['audio_removed']}")
    print(f"Duplicate URLs removed: {stats['duplicates_removed']}")
    print(f"Mismatched streams removed: {stats['mismatched_removed']}")

    print("")
    print("Cleaned-channel stream counts:")

    for channel_name in sorted(CHANNEL_STREAM_BLOCKS):
        print(
            f"  {channel_name}: "
            f"{remaining.get(channel_name, 0)}"
        )

    print("==========================================")
    return remaining

# ============================================================
# GENRE CATALOGS
# ============================================================

def create_genre_catalogs(catalog):

    print("")
    print("========== TD-TV CATALOGS ================")

    for genre, filename in GENRE_CATALOGS.items():

        genre_channels = [
            channel
            for channel in catalog.get("metas", [])
            if genre in channel.get("genres", [])
        ]

        output_path = os.path.join(
            CATALOG_FOLDER,
            filename
        )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {"metas": genre_channels},
                f,
                indent=2,
                ensure_ascii=False
            )

        print(f"{genre}: {len(genre_channels)} channels")

    print("==========================================")

# ============================================================
# MAIN
# ============================================================

with open(CATALOG_FILE, "r", encoding="utf-8") as f:
    catalog = json.load(f)

original_count = len(catalog.get("metas", []))

catalog["metas"] = [
    channel
    for channel in catalog.get("metas", [])
    if keep_channel(channel)
]

filtered_count = len(catalog["metas"])

with open(CATALOG_FILE, "w", encoding="utf-8") as f:
    json.dump(
        catalog,
        f,
        indent=2,
        ensure_ascii=False
    )


print("")
print(f"Original channels: {original_count}")
print(f"Filtered channels: {filtered_count}")
print(f"Removed channels: {original_count - filtered_count}")

selected_channels = {
    channel["id"]: channel.get("name", "").strip()
    for channel in catalog["metas"]
    if channel.get("id")
}

remaining = clean_streams(selected_channels)

catalog["metas"] = [
    channel
    for channel in catalog["metas"]
    if remaining.get(channel.get("name", "").strip(), 0) > 0
]

with open(CATALOG_FILE, "w", encoding="utf-8") as f:
    json.dump(
        catalog,
        f,
        indent=2,
        ensure_ascii=False
    )

create_genre_catalogs(catalog)
