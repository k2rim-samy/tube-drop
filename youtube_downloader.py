import os
import uuid
import re
import shutil
import yt_dlp
from utils import format_bytes, format_duration, download_thumbnail
import database

UPLOADS_DIR = '/tmp/uploads'
THUMBNAILS_DIR = '/tmp/thumbnails'
COOKIE_PATH = os.path.join(os.path.dirname(__file__), 'cookies.txt')

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(THUMBNAILS_DIR, exist_ok=True)


def _copy_cookie_to_writable_location(source_path):
    if not source_path or not os.path.isfile(source_path):
        return None

    temp_dir = os.environ.get('TMPDIR') or '/tmp'
    os.makedirs(temp_dir, exist_ok=True)

    temp_cookie_path = os.path.join(temp_dir, 'cookies.txt')
    try:
        shutil.copy2(source_path, temp_cookie_path)
        os.chmod(temp_cookie_path, 0o600)
        return temp_cookie_path
    except OSError:
        return source_path


def get_cookiefile_path():
    candidates = [
        COOKIE_PATH,
        os.path.join(os.getcwd(), 'cookies.txt'),
        os.path.join(os.path.dirname(__file__), 'cookies.txt'),
    ]

    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return _copy_cookie_to_writable_location(candidate)
    return None


def get_yt_dlp_base_options(extra_options=None):
    options = {
        'quiet': True,
        'no_warnings': True,
        'js_runtimes': {'node': {}},
        'remote_components': ['ejs:github'],
    }

    cookiefile = get_cookiefile_path()
    if cookiefile:
        options['cookiefile'] = cookiefile

    if extra_options:
        options.update(extra_options)

    return options


def sanitize_filename(name):
    clean = re.sub(r'[\\/*?:"<>|]', '', name)
    clean = clean.strip()[:100]
    return clean or "video"

def get_youtube_info(url):
    ydl_opts = get_yt_dlp_base_options({
        'skip_download': True,
    })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        # Determine best available thumbnail
        thumbnail = info.get('thumbnail')
        thumbnails = info.get('thumbnails', [])
        if thumbnails:
            sorted_thumbs = sorted(thumbnails, key=lambda t: t.get('preference', 0) or (t.get('width', 0) * t.get('height', 0)), reverse=True)
            if sorted_thumbs:
                thumbnail = sorted_thumbs[0].get('url', thumbnail)

        duration = info.get('duration', 0)
        
        formats = info.get('formats', [])
        heights = set()
        has_audio = False
        for f in formats:
            h = f.get('height')
            if h:
                heights.add(h)
            if f.get('acodec') != 'none':
                has_audio = True

        available_qualities = []
        if any(h >= 1080 for h in heights):
            available_qualities.append({'id': '1080p', 'label': 'Full HD 1080p (MP4)', 'type': 'video'})
        if any(h >= 720 for h in heights):
            available_qualities.append({'id': '720p', 'label': 'HD 720p (MP4)', 'type': 'video'})
        if any(h >= 480 for h in heights):
            available_qualities.append({'id': '480p', 'label': 'Standard 480p (MP4)', 'type': 'video'})
        if any(h >= 360 for h in heights):
            available_qualities.append({'id': '360p', 'label': 'Compact 360p (MP4)', 'type': 'video'})
            
        if not available_qualities:
            available_qualities.append({'id': 'best', 'label': 'Best Available Quality (MP4)', 'type': 'video'})
        else:
            available_qualities.insert(0, {'id': 'best', 'label': 'Maximum Quality (Best Video+Audio)', 'type': 'video'})

        if has_audio:
            available_qualities.append({'id': 'mp3', 'label': 'Audio Only (MP3 High Quality)', 'type': 'audio'})
            available_qualities.append({'id': 'm4a', 'label': 'Audio Only (M4A Original)', 'type': 'audio'})

        return {
            'id': info.get('id'),
            'title': info.get('title', 'Unknown Title'),
            'channel': info.get('uploader') or info.get('channel', 'Unknown Channel'),
            'channel_url': info.get('uploader_url') or info.get('channel_url', ''),
            'duration': duration,
            'duration_str': format_duration(duration),
            'views_count': info.get('view_count', 0),
            'thumbnail': thumbnail,
            'description': info.get('description', '')[:500],
            'upload_date': info.get('upload_date', ''),
            'qualities': available_qualities
        }

def download_youtube_video(task_id, url, quality='best', custom_title=None, task_state=None):
    video_uuid = str(uuid.uuid4())
    output_tmpl = os.path.join(UPLOADS_DIR, f"{video_uuid}_%(title).100B.%(ext)s")

    media_type = 'audio' if quality in ['mp3', 'm4a'] else 'video'

    if quality == 'mp3':
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_tmpl,
        }
        format_name = 'MP3 (Audio)'
    elif quality == 'm4a':
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': output_tmpl,
        }
        format_name = 'M4A (Audio)'
    elif quality == '1080p':
        ydl_opts = {
            'format': 'best[height<=1080][ext=mp4]/best[height<=1080]/best[ext=mp4]/best',
            'outtmpl': output_tmpl,
        }
        format_name = '1080p MP4'
    elif quality == '720p':
        ydl_opts = {
            'format': 'best[height<=720][ext=mp4]/best[height<=720]/best[ext=mp4]/best',
            'outtmpl': output_tmpl,
        }
        format_name = '720p MP4'
    elif quality == '480p':
        ydl_opts = {
            'format': 'best[height<=480][ext=mp4]/best[height<=480]/best[ext=mp4]/best',
            'outtmpl': output_tmpl,
        }
        format_name = '480p MP4'
    elif quality == '360p':
        ydl_opts = {
            'format': 'best[height<=360][ext=mp4]/best[height<=360]/best[ext=mp4]/best',
            'outtmpl': output_tmpl,
        }
        format_name = '360p MP4'
    else: # best
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': output_tmpl,
        }
        format_name = 'Max Quality MP4'

    def progress_hook(d):
        if not task_state:
            return
        status = d.get('status')
        if status == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            task_state['status'] = 'downloading'
            task_state['downloaded_bytes'] = downloaded
            task_state['total_bytes'] = total
            if total > 0:
                percent = round((downloaded / total) * 100, 1)
                task_state['progress'] = min(percent, 98.0)
            
            speed = d.get('speed')
            if speed:
                task_state['speed_str'] = f"{format_bytes(speed)}/s"
            eta = d.get('eta')
            if eta is not None:
                task_state['eta_str'] = f"{eta}s"
            
        elif status == 'finished':
            task_state['status'] = 'processing'
            task_state['progress'] = 98.5
            task_state['status_text'] = 'Merging and post-processing with FFmpeg...'

    ydl_opts.update({
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
        'js_runtimes': {'node': {}},
        'remote_components': ['ejs:github'],
    })

    if task_state:
        task_state['status'] = 'fetching'
        task_state['status_text'] = 'Starting stream extraction...'

    ydl_opts = get_yt_dlp_base_options(ydl_opts)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        final_filename = ydl.prepare_filename(info)
        
        if quality == 'mp3':
            base, _ = os.path.splitext(final_filename)
            final_filename = base + '.mp3'
        elif quality in ['best', '1080p', '720p', '480p', '360p']:
            base, _ = os.path.splitext(final_filename)
            if os.path.exists(base + '.mp4'):
                final_filename = base + '.mp4'

        if not os.path.exists(final_filename):
            matching = [f for f in os.listdir(UPLOADS_DIR) if f.startswith(video_uuid)]
            if matching:
                final_filename = os.path.join(UPLOADS_DIR, matching[0])

        file_size = os.path.getsize(final_filename) if os.path.exists(final_filename) else 0

        thumb_url = info.get('thumbnail')
        thumb_filename = f"{video_uuid}.jpg"
        thumb_local_path = os.path.join(THUMBNAILS_DIR, thumb_filename)
        thumb_relative_path = f"thumbnails/{thumb_filename}"
        
        if thumb_url:
            download_thumbnail(thumb_url, thumb_local_path)
            
        title = custom_title.strip() if custom_title and custom_title.strip() else info.get('title', 'Unknown Title')
        channel = info.get('uploader') or info.get('channel', 'Unknown Channel')
        duration = info.get('duration', 0)
        
        video_record = {
            'video_uuid': video_uuid,
            'title': title,
            'channel': channel,
            'duration': duration,
            'duration_str': format_duration(duration),
            'file_name': os.path.basename(final_filename),
            'file_path': final_filename,
            'file_size': file_size,
            'thumbnail_path': thumb_relative_path if os.path.exists(thumb_local_path) else '',
            'format_name': format_name,
            'media_type': media_type,
            'source_type': 'youtube',
            'source_url': url,
            'views_count': info.get('view_count', 0),
            'description': (info.get('description') or '')[:1000]
        }
        
        db_id = database.add_video(video_record)
        
        if task_state:
            task_state['status'] = 'completed'
            task_state['progress'] = 100.0
            task_state['status_text'] = 'Upload & import complete!'
            task_state['video_id'] = db_id
            task_state['video_record'] = {**video_record, 'id': db_id}

        return db_id
ydl_opts = get_yt_dlp_base_options({
    'skip_download': True,
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'ios']
        }
    }
})