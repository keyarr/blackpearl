# Black Pearl

A self-hosted YouTube audio downloader with automatic metadata tagging.

## Features

- **Search & Download** — Paste a YouTube URL or search by name
- **MP3 320kbps** — Best quality audio extraction
- **Auto-tag** — Fetches artist, album, track number, year from MusicBrainz
- **Cover Art** — Downloads album artwork automatically
- **YouTube Cookies** — Optional upload to bypass rate limits
- **i18n** — Portuguese (PT) / English (EN) toggle
- **Progress Tracking** — Real-time download progress bars

## Tech Stack

- **Backend:** FastAPI (Python 3.11+)
- **Frontend:** Vanilla JS + Jinja2 templates
- **Metadata:** yt-dlp, MusicBrainz, mutagen

## Quick Start

```bash
# Clone & enter
git clone https://github.com/<your-username>/blackpearl.git
cd blackpearl

# Create venv (Python 3.11+)
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# Install deps
pip install -r requirements.txt

# Run
python main.py
```

Open http://localhost:8046

## Requirements

- Python 3.11+
- FFmpeg (for audio conversion)
- Deno (optional, for YouTube JS challenges)

### FFmpeg Installation

**Linux (apt):**
```bash
sudo apt install ffmpeg
```

**macOS (brew):**
```bash
brew install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org (add to PATH)

### Deno (Optional)

Required only if YouTube returns JS challenges. Install:
```bash
curl -fsSL https://deno.land/x/install/install.sh | sh
# Add ~/.deno/bin to PATH
```

## Usage

1. Open the app
2. Paste a YouTube link (youtube.com/watch?v=...) or search term
3. Click search
4. Click download on the result
5. File saves to `downloads/` with ID3 tags

### Auto-tag Feature

When enabled (default), Black Pearl tries to:
1. Parse artist/track from YouTube title
2. Search YouTube Music for structured metadata
3. Query MusicBrainz for album/track info
4. Download cover art from Cover Art Archive
5. Apply ID3 tags and rename file

Disable via "Auto-tag" toggle in header.

### YouTube Cookies (Optional)

If YouTube blocks downloads ("Sign in to confirm you're not a bot"):

1. Install "Get cookies.txt LOCALLY" extension in Librewolf/Firefox
2. Log into YouTube
3. Export cookies
4. Open Settings (gear icon) → Upload cookies.txt

Or the app auto-detects cookies from installed browsers (Firefox, Chrome, Brave, Edge, etc.).

## Project Structure

```
blackpearl/
├── main.py              # FastAPI backend
├── requirements.txt     # Python deps
├── pyproject.toml      # Project config
├── templates/
│   └── index.html    # Jinja2 template
├── static/
│   ├── css/style.css # UI styles
│   └── js/app.js   # Frontend logic
├── downloads/        # Downloaded files
├── cookies.txt       # YouTube session (optional)
├── DESIGN.md       # Design system
├── PRODUCT.md     # Product brief
└── shape.md     # Frontend spec
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BP_DOWNLOADS_DIR` | Download folder | `./downloads` |

## API Endpoints

| Method | Endpoint | Description |
|--------|---------|------------|
| POST | `/api/search` | Search YouTube |
| POST | `/api/download` | Start download |
| GET | `/api/progress/{task_id}` | Check progress |
| DELETE | `/api/tasks/{task_id}` | Cleanup task |
| GET | `/api/cookies/status` | Cookie status |
| POST | `/api/cookies/upload` | Upload cookies |
| DELETE | `/api/cookies` | Remove cookies |

## Building for Production

```bash
# Production run
uvicorn main:app --host 0.0.0.0 --port 8046

# Or with gunicorn
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## License

MIT