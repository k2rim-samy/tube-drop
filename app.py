import os
import uuid
import time
import threading
from flask import Flask, render_template, request, jsonify, send_file, Response, abort
import database
import utils
from youtube_downloader import get_youtube_info, download_youtube_video, UPLOADS_DIR, THUMBNAILS_DIR

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB upload limit

# In-memory storage for asynchronous tasks
TASKS = {}
TASKS_LOCK = threading.Lock()

# Initialize DB on start
database.init_db()

def run_import_task(task_id, url, quality, custom_title):
    with TASKS_LOCK:
        TASKS[task_id]['status'] = 'starting'
        TASKS[task_id]['status_text'] = 'Connecting to YouTube...'

    try:
        def get_task_state():
            with TASKS_LOCK:
                return TASKS.get(task_id)

        task_state = get_task_state()
        if not task_state:
            return

        download_youtube_video(
            task_id=task_id,
            url=url,
            quality=quality,
            custom_title=custom_title,
            task_state=task_state
        )
    except Exception as e:
        print(f"Task {task_id} failed: {e}")
        with TASKS_LOCK:
            if task_id in TASKS:
                TASKS[task_id]['status'] = 'error'
                TASKS[task_id]['error_message'] = str(e)
                TASKS[task_id]['status_text'] = f"Failed: {str(e)[:120]}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/youtube/info', methods=['POST'])
def fetch_yt_info():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'success': False, 'error': 'Please provide a valid YouTube URL'}), 400

    yt_id = utils.extract_youtube_id(url)
    if not yt_id:
        return jsonify({'success': False, 'error': 'Invalid YouTube URL or unsupported link format.'}), 400

    try:
        info = get_youtube_info(url)
        return jsonify({'success': True, 'data': info})
    except Exception as e:
        return jsonify({'success': False, 'error': f"Failed to retrieve video information: {str(e)}"}), 500

@app.route('/api/youtube/import', methods=['POST'])
def start_import():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    quality = data.get('quality', 'best')
    custom_title = data.get('custom_title', '').strip()

    if not url:
        return jsonify({'success': False, 'error': 'YouTube URL is required'}), 400

    task_id = str(uuid.uuid4())
    with TASKS_LOCK:
        TASKS[task_id] = {
            'task_id': task_id,
            'url': url,
            'quality': quality,
            'title': custom_title or 'Fetching title...',
            'status': 'queued',
            'status_text': 'Task queued for download',
            'progress': 0.0,
            'speed_str': '--',
            'eta_str': '--',
            'downloaded_bytes': 0,
            'total_bytes': 0,
            'error_message': None,
            'created_at': time.time()
        }

    thread = threading.Thread(
        target=run_import_task,
        args=(task_id, url, quality, custom_title),
        daemon=True
    )
    thread.start()

    return jsonify({'success': True, 'task_id': task_id})

@app.route('/api/upload', methods=['POST'])
def handle_local_upload():
    if 'video_file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400

    file = request.files['video_file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    custom_title = request.form.get('custom_title', '').strip()
    original_filename = file.filename
    _, ext = os.path.splitext(original_filename)
    if not ext:
        ext = '.mp4'

    video_uuid = str(uuid.uuid4())
    safe_name = f"{video_uuid}_{int(time.time())}{ext}"
    saved_path = os.path.join(UPLOADS_DIR, safe_name)
    file.save(saved_path)

    meta = utils.get_file_metadata(saved_path)
    file_size = os.path.getsize(saved_path)

    thumb_name = f"{video_uuid}.jpg"
    thumb_path = os.path.join(THUMBNAILS_DIR, thumb_name)
    thumb_relative_path = f"thumbnails/{thumb_name}"
    
    thumb_success = utils.generate_local_thumbnail(saved_path, thumb_path)
    if not thumb_success:
        thumb_relative_path = ''

    title = custom_title or os.path.splitext(original_filename)[0]

    video_record = {
        'video_uuid': video_uuid,
        'title': title,
        'channel': 'Local Upload',
        'duration': meta['duration'],
        'duration_str': meta['duration_str'],
        'file_name': safe_name,
        'file_path': saved_path,
        'file_size': file_size,
        'thumbnail_path': thumb_relative_path,
        'format_name': ext.replace('.', '').upper(),
        'media_type': meta['media_type'],
        'source_type': 'upload',
        'source_url': '',
        'views_count': 0,
        'description': 'Directly uploaded media file'
    }

    db_id = database.add_video(video_record)
    return jsonify({'success': True, 'video': {**video_record, 'id': db_id}})

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    with TASKS_LOCK:
        task_list = list(TASKS.values())
        task_list.sort(key=lambda x: x['created_at'], reverse=True)
        return jsonify({'success': True, 'tasks': task_list})

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    with TASKS_LOCK:
        task = TASKS.get(task_id)
        if not task:
            return jsonify({'success': False, 'error': 'Task not found'}), 404
        return jsonify({'success': True, 'task': task})

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def dismiss_task(task_id):
    with TASKS_LOCK:
        if task_id in TASKS:
            del TASKS[task_id]
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Task not found'}), 404

@app.route('/api/videos', methods=['GET'])
def list_videos():
    query = request.args.get('q', '').strip()
    source_filter = request.args.get('filter', 'all')
    sort = request.args.get('sort', 'newest')

    videos = database.get_all_videos(query=query, source_filter=source_filter, sort=sort)
    stats = database.get_stats()

    for v in videos:
        v['file_size_str'] = utils.format_bytes(v.get('file_size', 0))
        if not v.get('duration_str'):
            v['duration_str'] = utils.format_duration(v.get('duration', 0))

    stats['total_bytes_str'] = utils.format_bytes(stats.get('total_bytes', 0))
    stats['total_duration_str'] = utils.format_duration(stats.get('total_duration', 0))

    return jsonify({'success': True, 'videos': videos, 'stats': stats})

@app.route('/api/videos/<int:video_id>', methods=['GET'])
def get_video(video_id):
    video = database.get_video_by_id(video_id)
    if not video:
        return jsonify({'success': False, 'error': 'Video not found'}), 404
    video['file_size_str'] = utils.format_bytes(video.get('file_size', 0))
    return jsonify({'success': True, 'video': video})

@app.route('/api/videos/<int:video_id>', methods=['DELETE'])
def delete_video(video_id):
    result = database.delete_video_by_id(video_id)
    if result:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Video not found or already deleted'}), 404

@app.route('/api/videos/<int:video_id>/stream')
def stream_video(video_id):
    video = database.get_video_by_id(video_id)
    if not video:
        abort(404)

    file_path = video['file_path']
    if not os.path.exists(file_path):
        abort(404)

    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    mimetypes = {
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.mkv': 'video/x-matroska',
        '.mov': 'video/quicktime',
        '.mp3': 'audio/mpeg',
        '.m4a': 'audio/mp4',
        '.ogg': 'audio/ogg',
        '.wav': 'audio/wav',
    }
    mime = mimetypes.get(ext, 'application/octet-stream')

    return send_file(file_path, mimetype=mime, conditional=True)

@app.route('/api/videos/<int:video_id>/download')
def download_video(video_id):
    video = database.get_video_by_id(video_id)
    if not video:
        abort(404)

    file_path = video['file_path']
    if not os.path.exists(file_path):
        abort(404)

    _, ext = os.path.splitext(file_path)
    safe_title = utils.re.sub(r'[\\/*?:"<>|]', '', video['title'])[:80] or 'video'
    download_name = f"{safe_title}{ext}"

    return send_file(file_path, as_attachment=True, download_name=download_name)

@app.route('/api/stats')
def get_library_stats():
    stats = database.get_stats()
    stats['total_bytes_str'] = utils.format_bytes(stats.get('total_bytes', 0))
    stats['total_duration_str'] = utils.format_duration(stats.get('total_duration', 0))
    return jsonify({'success': True, 'stats': stats})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 TubeDrop Studio server running on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
