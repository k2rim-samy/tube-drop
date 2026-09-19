import re
import os
import subprocess
import urllib.request
import json

def format_bytes(size):
    if not size or size <= 0:
        return '0 B'
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    idx = 0
    size_float = float(size)
    while size_float >= 1024 and idx < len(units) - 1:
        size_float /= 1024
        idx += 1
    return f"{size_float:.1f} {units[idx]}"

def format_duration(seconds):
    if not seconds or seconds <= 0:
        return '00:00'
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def extract_youtube_id(url):
    if not url:
        return None
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?m\.youtube\.com\/watch\?v=([a-zA-Z0-9_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def download_thumbnail(url, output_path):
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=10) as response, open(output_path, 'wb') as out_file:
            out_file.write(response.read())
        return True
    except Exception as e:
        print(f"Error downloading thumbnail: {e}")
        return False

def generate_local_thumbnail(video_path, output_thumb_path):
    try:
        # Seek to 1 second (or 00:00:01) and extract 1 frame
        cmd = [
            'ffmpeg', '-y',
            '-ss', '00:00:01',
            '-i', video_path,
            '-vframes', '1',
            '-q:v', '2',
            '-vf', 'scale=640:-1',
            output_thumb_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return os.path.exists(output_thumb_path)
    except Exception as e:
        print(f"Error generating thumbnail with ffmpeg: {e}")
        # fallback: try at 00:00:00
        try:
            cmd = [
                'ffmpeg', '-y',
                '-ss', '00:00:00',
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',
                output_thumb_path
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return os.path.exists(output_thumb_path)
        except Exception:
            return False

def get_file_metadata(file_path):
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        data = json.loads(res.stdout)
        
        duration = float(data.get('format', {}).get('duration', 0))
        size = int(data.get('format', {}).get('size', os.path.getsize(file_path)))
        
        # Check if video stream exists
        is_video = any(s.get('codec_type') == 'video' for s in data.get('streams', []))
        media_type = 'video' if is_video else 'audio'
        
        return {
            'duration': int(duration),
            'duration_str': format_duration(duration),
            'file_size': size,
            'media_type': media_type
        }
    except Exception as e:
        print(f"Error probing file with ffprobe: {e}")
        size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        return {
            'duration': 0,
            'duration_str': '00:00',
            'file_size': size,
            'media_type': 'video'
        }
