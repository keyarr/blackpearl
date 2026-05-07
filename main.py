"""Black Pearl — YouTube audio downloader with web interface."""

import asyncio
import json
import os
import re
import shutil
import uuid
from pathlib import Path

# Ensure Deno is on PATH (yt-dlp needs it for YouTube JS challenges)
_deno_bin = Path.home() / ".deno" / "bin"
if _deno_bin.exists():
    os.environ["PATH"] = str(_deno_bin) + os.pathsep + os.environ.get("PATH", "")

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TRCK, APIC, ID3NoHeaderError
import musicbrainzngs
import requests as http_requests
from pydantic import BaseModel
from yt_dlp import YoutubeDL

# MusicBrainz setup
musicbrainzngs.set_useragent("BlackPearl", "1.0", "https://github.com/blackpearl")

# ─── Paths ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DOWNLOADS_DIR = Path(os.environ.get("SPOT_DOWNLOADS_DIR", str(BASE_DIR / "downloads")))
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

# ─── App ─────────────────────────────────────────────────────────────
app = FastAPI(title="Black Pearl", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# In-memory store for active downloads progress
download_progress: dict[str, dict] = {}


# ─── Cookie / Browser detection ─────────────────────────────────────
COOKIE_FILE = BASE_DIR / "cookies.txt"
_BROWSER_ORDER = ["firefox", "chrome", "chromium", "brave", "edge", "opera", "vivaldi", "zen", "librewolf"]


def _detect_browser_cookies() -> dict | None:
    """Try to find an installed browser and use its cookies.
    Returns yt-dlp cookie options dict or None if no browser found.
    """
    # 1. If user provided a manual cookies.txt file, use that
    if COOKIE_FILE.exists():
        print(f"[cookies] Usando cookies.txt: {COOKIE_FILE}")
        return {"cookiefile": str(COOKIE_FILE)}

    # 2. Try to detect installed browsers
    home = Path.home()
    browser_profiles = {
        "firefox": [
            home / ".mozilla/firefox",
            home / "snap/firefox/common/.mozilla/firefox",
        ],
        "chrome": [
            home / ".config/google-chrome",
            home / ".config/chromium",
            home / "snap/chromium/common/chromium",
        ],
        "brave": [home / ".config/BraveSoftware/Brave-Browser"],
        "edge": [home / ".config/microsoft-edge"],
        "opera": [home / ".config/opera"],
        "vivaldi": [home / ".config/vivaldi"],
        "zen": [home / ".zen"],
        "librewolf": [
            home / ".librewolf",
            home / ".local/share/librewolf",
        ],
    }

    for browser in _BROWSER_ORDER:
        profiles = browser_profiles.get(browser, [])
        for profile_dir in profiles:
            if profile_dir.exists():
                print(f"[cookies] Browser detectado: {browser} em {profile_dir}")
                return {"cookiesfrombrowser": (browser,)}

    print("[cookies] Nenhum browser encontrado e sem cookies.txt — downloads podem falhar!")
    return None


def _inject_cookies(opts: dict) -> dict:
    """Merge cookie options into yt-dlp opts."""
    cookie_opts = _detect_browser_cookies()
    if cookie_opts:
        try:
            opts.update(cookie_opts)
        except Exception as e:
            print(f"[cookies] Aviso: falha ao injetar cookies: {e}")
    return opts


# ─── Helpers ─────────────────────────────────────────────────────────
YOUTUBE_URL_RE = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)/.+"
)


def _is_url(text: str) -> bool:
    return bool(YOUTUBE_URL_RE.match(text.strip()))


def _sanitize_filename(title: str) -> str:
    """Strip YouTube cruft from title: (Official Video), [xyz123], etc."""
    # Remove common suffixes/crap in parentheses
    title = re.sub(r'\(Official\s*(Music\s*)?Video\)', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\(Official\s*Audio\)', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\(Lyric\s*Video\)', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\(Visualizer\)', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\(Live\)', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\(Official\)', '', title, flags=re.IGNORECASE)
    # Remove bracket tags like [abc123], [Official Video], etc
    title = re.sub(r'\[.*?\]', '', title)
    # Remove any character not safe for filenames (Windows/Linux/Mac)
    # Keep: alphanumeric, spaces, hyphens, underscores, dots, parentheses, commas, apostrophes
    title = re.sub(r'[<>:"/\\|?*]', '', title)
    # Remove trailing hyphens/whitespace, collapse spaces
    title = re.sub(r'\s+', ' ', title).strip(' -')
    return title


def _parse_title_artist(title: str) -> tuple[str, str]:
    """Try to extract artist + track from YouTube title like 'Artist - Track'."""
    # Remove YouTube cruft first
    clean = _sanitize_filename(title)
    # Pattern: "Artist - Track"
    m = re.match(r'^(.+?)\s*[-–—]\s*(.+)$', clean)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", clean


def _search_youtube_music(artist: str, track: str) -> dict | None:
    """Search YouTube Music for structured metadata (artist, album, year, track).

    YouTube Music returns metadata that regular YouTube doesn't: artist, album,
    release_year, track name.
    """
    query = f"{artist} {track}".strip()
    if not query:
        return None
    try:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": True,
            "default_search": "ytsearch",
        }
        with YoutubeDL(opts) as ydl:
            # Search YouTube Music specifically
            info = ydl.extract_info(
                f"https://music.youtube.com/search?q={query.replace(' ', '+')}",
                download=False,
            )
            if not info:
                return None

            entries = info.get("entries", [])
            if not entries:
                return None

            # Pick first video result (skip channels/playlists)
            video_id = None
            for entry in entries:
                if entry.get("ie_key") == "Youtube" and entry.get("id"):
                    video_id = entry["id"]
                    break

            if not video_id:
                return None

            # Fetch full metadata for this video
            full_info = ydl.extract_info(
                f"https://music.youtube.com/watch?v={video_id}",
                download=False,
            )
            if not full_info:
                return None

            result = {
                "artist": full_info.get("artist") or full_info.get("creator") or full_info.get("uploader") or "",
                "track": full_info.get("track") or full_info.get("title") or "",
                "album": full_info.get("album") or "",
                "year": str(full_info.get("release_year") or "") or "",
                "thumbnail": full_info.get("thumbnail") or "",
            }
            print(f"[yt-music] Metadata: artist={result['artist']!r}, album={result['album']!r}, year={result['year']!r}")
            return result
    except Exception as e:
        print(f"[yt-music] Search error: {e}")
        return None


def _search_musicbrainz(artist: str, track: str, album: str = "") -> dict | None:
    """Search MusicBrainz for metadata. Returns dict with album, year, etc.

    Strategy:
    1. Search recordings by artist+track (+album if given)
    2. Collect all releases from all recordings
    3. Pre-filter by title keywords (remove obvious compilations/live)
    4. For top candidates, fetch release-group to verify type is Album
    5. Pick the earliest verified studio album
    """
    if not artist and not track:
        return None
    try:
        query_parts = []
        if artist:
            query_parts.append(f'artist:"{artist}"')
        if track:
            query_parts.append(f'recording:"{track}"')
        if album:
            query_parts.append(f'releasegroup:"{album}"')
        query = " AND ".join(query_parts) if query_parts else track
        print(f"[mb] Query: {query}")
        result = musicbrainzngs.search_recordings(query=query, limit=10)
        recordings = result.get("recording-list", [])
        if not recordings:
            return None

        mb_artist = recordings[0].get("artist-credit", [{}])[0].get("name", artist)
        mb_title = recordings[0].get("title", track)

        # Collect all unique releases from all recordings
        all_releases = []
        seen_ids = set()
        for rec in recordings:
            rec_id = rec.get("id")
            if not rec_id:
                continue
            try:
                full_rec = musicbrainzngs.get_recording_by_id(rec_id, includes=["releases"])
                for rel in full_rec.get("recording", {}).get("release-list", []):
                    rid = rel.get("id", "")
                    if rid and rid not in seen_ids:
                        seen_ids.add(rid)
                        all_releases.append(rel)
            except Exception as e:
                print(f"[tagger] Recording detail fetch error for {rec_id}: {e}")

        if not all_releases:
            return {"artist": mb_artist, "title": mb_title, "album": "", "year": "", "track": "", "release_mbid": ""}

        # Pre-filter: remove obvious compilations/live by title
        candidates = _filter_releases(all_releases, track)

        # If no candidates after filtering, fall back to all releases
        if not candidates:
            candidates = all_releases

        # Score and sort candidates
        scored = []
        seen_titles = set()
        for rel in candidates:
            key = (rel.get("title", "").lower().strip(), rel.get("date", ""))
            if key in seen_titles:
                continue
            seen_titles.add(key)
            scored.append((_score_release(rel, track), rel))
        scored.sort(key=lambda x: x[0])

        # Verify top 5 candidates with release-group type (via get_release_by_id)
        best_result = None
        for _, rel in scored[:5]:
            rel_id = rel.get("id")
            if rel_id:
                try:
                    full_rel = musicbrainzngs.get_release_by_id(rel_id, includes=["release-groups"])
                    rg = full_rel.get("release", {}).get("release-group", {})
                    primary = rg.get("primary-type", "").lower()
                    secondary = [s.lower() for s in rg.get("secondary-type-list", [])]
                    # Accept: Album type, no compilation/live secondary
                    if primary == "album" and "compilation" not in secondary and "live" not in secondary:
                        best_result = rel
                        print(f"[tagger] Verified album via release-group: {rel.get('title')}")
                        break
                    else:
                        print(f"[tagger] Rejected: {rel.get('title')} (type={primary}, secondary={secondary})")
                except Exception as e:
                    print(f"[tagger] Release-group fetch error: {e}")
                    continue

        # Fallback: if no verified album, use best scored candidate
        if not best_result and scored:
            best_result = scored[0][1]
            print(f"[tagger] Fallback to best scored: {best_result.get('title')}")

        mb_album = ""
        mb_year = ""
        mb_track = ""
        mb_release_mbid = ""
        if best_result:
            mb_album = best_result.get("title", "")
            mb_year = best_result.get("date", "")[:4] if best_result.get("date") else ""
            mb_release_mbid = best_result.get("id", "")
            mediums = best_result.get("medium-list", [])
            if mediums:
                tracks = mediums[0].get("track-list", [])
                if tracks:
                    mb_track = tracks[0].get("number", "")

        return {
            "artist": mb_artist,
            "title": mb_title,
            "album": mb_album,
            "year": mb_year,
            "track": mb_track,
            "release_mbid": mb_release_mbid,
        }
    except Exception as e:
        print(f"[tagger] MusicBrainz search error: {e}")
        return None


_COMPILATION_KW = [
    "greatest hits", "best of", "compilation", "collection", "anthology",
    "essentials", "legend", "tribute", "years of", "volume", "rock stars",
    "soundtrack", "various artists", "the best", "ultimate", "gold",
    "platinum", "hits", "classic rock", "retrospective", "rarities",
    "box set", "deluxe", "remaster",
]
_LIVE_KW = ["live", "concert", "session", "bootleg"]


def _filter_releases(releases: list, track_name: str = "") -> list:
    """Remove obvious compilations, live albums, and box sets by title."""
    track_lower = track_name.lower().strip()
    filtered = []
    for rel in releases:
        title = rel.get("title", "").lower().strip()
        # Skip if title is just the track name (single)
        if title == track_lower:
            continue
        # Skip compilations
        if any(kw in title for kw in _COMPILATION_KW):
            continue
        # Skip live
        if any(kw in title for kw in _LIVE_KW):
            continue
        filtered.append(rel)
    return filtered


def _score_release(rel: dict, track_name: str = "") -> int:
    """Score a release: lower = better. Studio albums score lowest."""
    title = rel.get("title", "").lower().strip()
    track_lower = track_name.lower().strip()
    score = 0

    # Penalize compilations heavily
    if any(kw in title for kw in _COMPILATION_KW):
        score += 200

    # Penalize live
    if any(kw in title for kw in _LIVE_KW):
        score += 100

    # Penalize if title is just the track name (likely a single)
    if title == track_lower:
        score += 50

    # Bonus: looks like a proper album title (not track name, not compilation)
    if (title != track_lower and len(title) > 2
            and not any(kw in title for kw in _COMPILATION_KW + _LIVE_KW)):
        score -= 50

    # Prefer earlier dates
    date = rel.get("date", "9999")
    try:
        year = int(date[:4])
        score += max(0, year - 1950)
    except (ValueError, IndexError):
        score += 500

    return score


def _pick_best_release(releases: list, track_name: str = "") -> dict | None:
    """Pick the best release from a list — prefer studio album with earliest date."""
    if not releases:
        return None

    seen = set()
    best = None
    best_score = 9999

    for rel in releases:
        title = rel.get("title", "").lower().strip()
        key = (title, rel.get("date", ""))
        if key in seen:
            continue
        seen.add(key)

        score = _score_release(rel, track_name)
        if score < best_score:
            best_score = score
            best = rel

    return best


def _download_cover_art(release_mbid: str) -> bytes | None:
    """Download cover art from Cover Art Archive."""
    if not release_mbid:
        return None
    try:
        url = f"https://coverartarchive.org/release/{release_mbid}/front-500"
        resp = http_requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.content
    except Exception as e:
        print(f"[tagger] Cover art download error: {e}")
    return None


def _apply_tags(filepath: Path, meta: dict, cover: bytes | None):
    """Apply ID3 tags to MP3 file."""
    try:
        try:
            audio = ID3(filepath)
        except ID3NoHeaderError:
            audio = ID3()
        if meta.get("title"):
            audio.add(TIT2(encoding=3, text=meta["title"]))
        if meta.get("artist"):
            audio.add(TPE1(encoding=3, text=meta["artist"]))
        if meta.get("album"):
            audio.add(TALB(encoding=3, text=meta["album"]))
        if meta.get("year"):
            audio.add(TDRC(encoding=3, text=meta["year"]))
        if meta.get("track"):
            audio.add(TRCK(encoding=3, text=meta["track"]))
        if cover:
            audio.add(APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,  # Cover (front)
                desc="Cover",
                data=cover,
            ))
        audio.save(filepath)
        print(f"[tagger] Tags aplicadas: {meta.get('artist')} - {meta.get('title')}")
    except Exception as e:
        print(f"[tagger] Erro ao aplicar tags: {e}")


def _enrich_and_tag(filepath: Path, info_dict: dict) -> Path:
    """Enrich file with metadata, cover art, and rename.

    Flow:
    1. Parse artist/track from YouTube title
    2. Search YouTube Music for structured metadata (artist, album, year)
    3. Search MusicBrainz for release_mbid (cover art source)
    4. Download cover art (MusicBrainz > YouTube thumbnail > YouTube Music thumbnail)
    5. Apply ID3 tags
    6. Rename file: "{álbum - ano} {nome} {artista}.mp3"
    """
    # 1. Extract artist/track from yt-dlp info or parse from title
    yt_artist = info_dict.get("artist") or info_dict.get("uploader") or ""
    yt_title = info_dict.get("track") or info_dict.get("title") or filepath.stem

    # If no artist from yt-dlp, try parsing "Artist - Title" from YouTube title
    raw_title = info_dict.get("title", filepath.stem)
    parsed_artist, parsed_track = _parse_title_artist(raw_title)
    artist = yt_artist or parsed_artist
    track = parsed_track if parsed_artist else yt_title

    # Avoid using channel name as artist (e.g., "VEVO", "Topic", "Records")
    channel = info_dict.get("channel") or info_dict.get("uploader") or ""
    if artist and channel and artist.lower() == channel.lower():
        artist = parsed_artist or ""

    # 2. Search YouTube Music for structured metadata
    print(f"[tagger] Buscando YouTube Music: artist={artist!r}, track={track!r}")
    ytm = _search_youtube_music(artist, track)

    # Use YouTube Music data as primary source
    if ytm:
        artist = ytm.get("artist") or artist
        track = ytm.get("track") or track
        album = ytm.get("album") or ""
        year = ytm.get("year") or ""
        ytm_thumbnail = ytm.get("thumbnail")  # Prefer yt-music thumbnail
    else:
        album = info_dict.get("album") or ""
        year = str(info_dict.get("release_year") or info_dict.get("upload_date", "")[:4]) or ""
        ytm_thumbnail = None

    track_num = ""
    release_mbid = ""
    cover = None

    # 3. Search MusicBrainz for cover art (release_mbid)
    print(f"[tagger] Buscando MusicBrainz: artist={artist!r}, track={track!r}, album={album!r}")
    mb = _search_musicbrainz(artist, track, album)
    if mb:
        # Use MusicBrainz data to fill gaps
        if not album and mb.get("album"):
            album = mb["album"]
        if not year and mb.get("year"):
            year = mb["year"]
        if mb.get("track"):
            track_num = mb["track"]
        release_mbid = mb.get("release_mbid", "")

    # 4. Download cover art (priority: MusicBrainz > YouTube Music > YouTube thumbnail)
    print(f"[tagger] Cover download: release_mbid={release_mbid!r}, ytm_thumbnail={ytm_thumbnail!r}")
    if release_mbid:
        cover = _download_cover_art(release_mbid)
        print(f"[tagger] Cover from MusicBrainz: {'found' if cover else 'none'}")

    if not cover and ytm_thumbnail:
        try:
            print(f"[tagger] Trying yt-music thumbnail: {ytm_thumbnail}")
            resp = http_requests.get(ytm_thumbnail, timeout=10)
            if resp.status_code == 200:
                cover = resp.content
                print(f"[tagger] Usando thumbnail do YouTube Music como capa ({len(cover)} bytes)")
            else:
                print(f"[tagger] yt-music thumbnail status: {resp.status_code}")
        except Exception as e:
            print(f"[tagger] Erro ao baixar thumbnail do yt-music: {e}")

    if not cover:
        thumb_url = info_dict.get("thumbnail") or ""
        if thumb_url:
            try:
                print(f"[tagger] Trying YouTube thumbnail: {thumb_url}")
                resp = http_requests.get(thumb_url, timeout=10)
                if resp.status_code == 200:
                    cover = resp.content
                    print(f"[tagger] Usando thumbnail do YouTube como capa ({len(cover)} bytes)")
                else:
                    print(f"[tagger] YouTube thumbnail status: {resp.status_code}")
            except Exception as e:
                print(f"[tagger] Erro ao baixar thumbnail: {e}")
        else:
            print(f"[tagger] No thumbnail URL available")
    else:
        print(f"[tagger] Cover downloaded successfully ({len(cover)} bytes)")

    # 5. Apply ID3 tags
    print(f"[tagger] Aplicando tags: title={track!r}, artist={artist!r}, album={album!r}, year={year!r}, track_num={track_num!r}")
    _apply_tags(filepath, {
        "title": track,
        "artist": artist,
        "album": album,
        "year": str(year),
        "track": str(track_num),
    }, cover)

    # 6. Rename file: "{álbum - ano} {nome} {artista}.mp3"
    parts = []
    if album and year:
        parts.append(f"{album} - {year}")
    elif album:
        parts.append(album)
    parts.append(track)
    if artist:
        parts.append(artist)
    joined = " ".join(parts)
    print(f"[tagger] Parts before sanitize: album={album!r}, year={year!r}, track={track!r}, artist={artist!r}")
    print(f"[tagger] Joined string: {joined!r}")
    new_name = _sanitize_filename(joined)
    print(f"[tagger] Sanitized name: {new_name!r}")
    new_path = filepath.with_name(new_name + filepath.suffix)
    if new_path != filepath:
        # Avoid overwriting existing files
        counter = 1
        base = new_path
        while new_path.exists():
            new_path = base.with_name(f"{base.stem} ({counter}){base.suffix}")
            counter += 1
        filepath.rename(new_path)
        print(f"[tagger] Renomeado para: {new_path.name}")
    else:
        print(f"[tagger] Nome unchanged: {filepath.name}")
    return new_path


def _make_ydl_opts(task_id: str, output_dir: Path) -> dict:
    """Build yt-dlp options for best-quality audio download with metadata."""

    def _progress_hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            pct = (downloaded / total * 100) if total else 0
            download_progress[task_id] = {
                "status": "downloading",
                "percent": round(pct, 1),
                "speed": d.get("speed"),
                "eta": d.get("eta"),
                "filename": Path(d.get("filename", "")).name,
            }
        elif d["status"] == "finished":
            download_progress[task_id] = {
                "status": "processing",
                "percent": 100,
                "filename": Path(d.get("filename", "")).name,
            }

    opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
        "writethumbnail": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            },
            {"key": "FFmpegMetadata", "add_metadata": True},
            {"key": "EmbedThumbnail"},
        ],
        "progress_hooks": [_progress_hook],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 30,
        "retries": 3,
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
        "remote_components": ["ejs:github"],
    }
    return _inject_cookies(opts)


def _search_youtube(query: str, max_results: int = 8) -> list[dict]:
    """Search YouTube and return simplified results."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "default_search": f"ytsearch{max_results}",
        "extract_flat": "in_playlist",
        "noplaylist": True,
        "ignoreerrors": True,
        "remote_components": ["ejs:github"],
    }
    _inject_cookies(opts)
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
    if not info or "entries" not in info:
        return []
    results = []
    for entry in info["entries"]:
        if entry is None:
            continue
        tid = entry.get("id", "")
        raw_title = entry.get("title", "Sem título")
        artist, track = _parse_title_artist(raw_title)
        results.append({
            "id": tid,
            "title": raw_title,
            "channel": entry.get("channel", entry.get("uploader", "")),
            "duration": entry.get("duration"),
            "thumbnail": entry.get("thumbnail", f"https://i.ytimg.com/vi/{tid}/hqdefault.jpg"),
            "url": entry.get("webpage_url", f"https://www.youtube.com/watch?v={tid}"),
            "view_count": entry.get("view_count"),
            "artist": entry.get("artist") or artist,
            "track": entry.get("track") or track,
            "album": entry.get("album") or "",
        })
    return results


def _get_info(url: str) -> dict:
    """Extract metadata for a single URL."""
    opts = {"quiet": True, "no_warnings": True, "noplaylist": True, "remote_components": ["ejs:github"]}
    _inject_cookies(opts)
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            info = ydl.sanitize_info(info)
    except Exception as e:
        err = str(e).lower()
        if "cookies" in err or "cookie" in err or "format" in err:
            print(f"[info] Erro, tentando fallback: {e}")
            opts.pop("cookiefile", None)
            opts.pop("cookiesfrombrowser", None)
            opts["ignoreerrors"] = True
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                info = ydl.sanitize_info(info)
        else:
            raise
    tid = info.get("id", "")
    raw_title = info.get("title", "Sem título")
    artist, track = _parse_title_artist(raw_title)
    return {
        "id": tid,
        "title": raw_title,
        "channel": info.get("channel", info.get("uploader", "")),
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail", f"https://i.ytimg.com/vi/{tid}/hqdefault.jpg"),
        "url": info.get("webpage_url", url),
        "view_count": info.get("view_count"),
        "artist": info.get("artist") or artist,
        "track": info.get("track") or track,
        "album": info.get("album") or "",
    }


async def _download_audio(url: str, task_id: str, enrich: bool = True) -> Path:
    """Download audio in background thread, return path to the file."""

    opts = _make_ydl_opts(task_id, DOWNLOADS_DIR)
    download_progress[task_id] = {"status": "starting", "percent": 0}

    loop = asyncio.get_event_loop()
    info_dict = {}

    def _do_download():
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                info_dict["filename"] = ydl.prepare_filename(info)
                info_dict.update(ydl.sanitize_info(info) or {})
        except Exception as e:
            if "cookies" in str(e).lower() or "cookie" in str(e).lower():
                print(f"[cookies] Erro com cookies no download, tentando sem: {e}")
                opts.pop("cookiefile", None)
                opts.pop("cookiesfrombrowser", None)
                with YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    info_dict["filename"] = ydl.prepare_filename(info)
                    info_dict.update(ydl.sanitize_info(info) or {})
            else:
                raise

    await loop.run_in_executor(None, _do_download)

    # Find the final audio file (yt-dlp converts to .mp3 after postprocessing)
    original = Path(info_dict.get("filename", ""))
    stem = original.stem
    found = None
    for ext in (".mp3", ".m4a", ".opus", original.suffix):
        candidate = DOWNLOADS_DIR / (stem + ext)
        if candidate.exists():
            found = candidate
            break

    # Fallback: glob for recent files
    if not found:
        audio_files = list(DOWNLOADS_DIR.glob("*.mp3")) + list(DOWNLOADS_DIR.glob("*.m4a")) + list(DOWNLOADS_DIR.glob("*.opus"))
        if not audio_files:
            audio_files = [f for f in DOWNLOADS_DIR.iterdir() if f.is_file() and f.suffix not in (".jpg", ".png", ".webp", ".part")]
        if not audio_files:
            raise HTTPException(status_code=500, detail="Download falhou — nenhum arquivo gerado")
        found = audio_files[0]

    # Enrich with MusicBrainz metadata, cover art, and rename
    if enrich:
        enriched = await loop.run_in_executor(None, _enrich_and_tag, found, info_dict)
        return enriched
    return found


# ─── Models ──────────────────────────────────────────────────────────
class SearchRequest(BaseModel):
    query: str


class DownloadRequest(BaseModel):
    url: str
    title: str = ""
    enrich: bool = True


# ─── Routes ──────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/api/search")
async def search(req: SearchRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query vazia")

    if _is_url(query):
        # It's a URL — extract info directly
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _get_info, query)
        return {"results": [info], "type": "url"}

    # It's a text search
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, _search_youtube, query)
    return {"results": results, "type": "search"}


@app.post("/api/download")
async def start_download(req: DownloadRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL vazia")

    task_id = uuid.uuid4().hex[:12]
    download_progress[task_id] = {"status": "queued", "percent": 0}

    # Start download in background
    async def _bg_download():
        try:
            filepath = await _download_audio(url, task_id, enrich=req.enrich)
            download_progress[task_id] = {
                "status": "done",
                "percent": 100,
                "filename": filepath.name,
                "filepath": str(filepath),
                "task_id": task_id,
            }
        except Exception as e:
            err_msg = str(e)
            if "Sign in" in err_msg or "bot" in err_msg.lower():
                err_msg += "\n\nFaça upload de um cookies.txt em Configuracoes para resolver isso."
            download_progress[task_id] = {
                "status": "error",
                "percent": 0,
                "error": err_msg,
            }

    asyncio.create_task(_bg_download())
    return {"task_id": task_id}


@app.get("/api/progress/{task_id}")
async def get_progress(task_id: str):
    if task_id not in download_progress:
        raise HTTPException(status_code=404, detail="Task não encontrada")
    return download_progress[task_id]


@app.get("/api/download-file/{task_id}")
async def download_file(task_id: str):
    progress = download_progress.get(task_id)
    if not progress or progress.get("status") != "done":
        raise HTTPException(status_code=404, detail="Arquivo não pronto")

    filepath = Path(progress["filepath"])
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(
        path=str(filepath),
        filename=filepath.name,
        media_type="audio/mpeg",
    )


@app.delete("/api/tasks/{task_id}")
async def cleanup_task(task_id: str):
    """Clean up progress tracking. File stays on disk in downloads folder."""
    download_progress.pop(task_id, None)
    return {"ok": True}


# ─── Cookie Management ───────────────────────────────────────────────
@app.get("/api/cookies/status")
async def cookies_status():
    """Check if cookies are configured."""
    has_cookies = COOKIE_FILE.exists()
    return {
        "has_cookies": has_cookies,
        "source": "file" if has_cookies else "none",
    }


@app.post("/api/cookies/upload")
async def upload_cookies(file: UploadFile = File(...)):
    """Upload a cookies.txt file (Netscape format)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nenhum arquivo selecionado")

    content = await file.read()

    # Basic validation: check if it looks like a Netscape cookie file
    text = content.decode("utf-8", errors="ignore")
    if len(content) < 50:
        raise HTTPException(status_code=400, detail="Arquivo muito pequeno para ser um cookies.txt válido")

    # Check for Netscape format markers
    lines = text.strip().splitlines()
    is_netscape = False
    for line in lines[:5]:
        if line.startswith("# Netscape") or line.startswith("# HttpOnly_"):
            is_netscape = True
            break
        # Netscape format: domain\tpath\tsecure\texpiry\tname\tvalue
        if line.count('\t') >= 5:
            is_netscape = True
            break

    if not is_netscape:
        raise HTTPException(
            status_code=400,
            detail="O arquivo não está no formato Netscape cookies.txt. "
                   "Use a extensão 'Get cookies.txt LOCALLY' no Librewolf "
                   "e exporte da página do YouTube.",
        )

    COOKIE_FILE.write_bytes(content)
    print(f"[cookies] cookies.txt atualizado via upload ({len(content)} bytes)")
    return {"ok": True, "message": "Cookies atualizados com sucesso!"}


@app.delete("/api/cookies")
async def delete_cookies():
    """Remove the cookies.txt file."""
    if COOKIE_FILE.exists():
        COOKIE_FILE.unlink()
        print("[cookies] cookies.txt removido")
        return {"ok": True, "message": "Cookies removidos"}
    return {"ok": True, "message": "Nenhum cookies.txt para remover"}


# ─── Main ────────────────────────────────────────────────────────────
def main():
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8046, reload=False)


if __name__ == "__main__":
    main()
