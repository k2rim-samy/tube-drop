# TubeDrop Studio 🎬

A modern, professional web application for importing, uploading, streaming, and managing YouTube videos and local video media.

---

## ✨ Features

- **YouTube Import with Live Inspection**:
  - Paste any YouTube link (Standard videos, Shorts, mobile links, `youtu.be/`).
  - Fetches title, channel name, views count, duration, and highest-resolution thumbnail before downloading.
  - Built-in YouTube embedded player to preview the video before importing.
  - Multi-quality selection:
    - 🎬 **Maximum Quality** (1080p / 1440p / 4K MP4 with video + audio merged via FFmpeg)
    - 📺 **Balanced HD** (720p MP4)
    - 📱 **Compact** (480p / 360p MP4)
    - 🎵 **High Quality Audio** (MP3 192/320kbps extraction)
    - 🎧 **Original Audio** (M4A)

- **Local Video Upload**:
  - Drag-and-drop or file picker for local files (`.mp4`, `.webm`, `.mkv`, `.mov`, `.mp3`).
  - Automatic thumbnail generation via `ffmpeg`.
  - Automatic duration probe via `ffprobe`.

- **Real-Time Task Queue & Progress Tracking**:
  - Background asynchronous worker threads.
  - Live progress bar with speed (`MB/s`), downloaded vs total size, ETA, and processing status.

- **Built-In Media Vault & Studio Player**:
  - HTML5 video/audio player with seeking and playback speed controls.
  - HTTP Range Request (`206 Partial Content`) support for instantaneous seeking.
  - Search bar with live debounced filtering.
  - Category filters: All Media, YouTube Imports, Local Uploads, Audio Only.
  - Sorting: Newest, Oldest, Largest Size, Longest Duration, Title (A-Z).
  - One-click file download to local device.
  - One-click copy stream URL.
  - Video deletion with confirmation dialog (removes metadata and disk files).

---

## 🚀 Getting Started

### 1. Requirements
- Python 3.10+
- FFmpeg & FFprobe
- Node.js (used by `yt-dlp` JavaScript challenge engine)

### 2. Installation
```bash
pip install -r requirements.txt
```

### 3. Run the Server
```bash
python3 app.py
```
Open your browser at:
**`http://localhost:5000`** (or access from your phone/LAN using your device IP address e.g. `http://<your-ip>:5000`).

---

## 📁 Project Structure

```text
Project/
├── app.py                  # Flask backend with REST APIs and stream endpoints
├── database.py             # SQLite database manager for video records
├── youtube_downloader.py   # yt-dlp downloader worker and metadata engine
├── utils.py                # FFmpeg thumbnailing, duration, and formatting helpers
├── requirements.txt        # Python dependencies
├── static/
│   ├── css/
│   │   └── style.css       # Responsive dark-theme stylesheet
│   ├── js/
│   │   └── app.js          # Client-side UI, polling, and player logic
│   ├── uploads/            # Downloaded and uploaded video files
│   └── thumbnails/         # Video thumbnails
├── templates/
│   └── index.html          # Main web application dashboard
└── library.db              # SQLite persistence database
```
