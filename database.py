import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'library.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_uuid TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                channel TEXT,
                duration INTEGER DEFAULT 0,
                duration_str TEXT,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                thumbnail_path TEXT,
                format_name TEXT,
                media_type TEXT DEFAULT 'video',
                source_type TEXT DEFAULT 'youtube',
                source_url TEXT,
                views_count INTEGER DEFAULT 0,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

def add_video(video_data):
    with get_db() as conn:
        cursor = conn.execute('''
            INSERT INTO videos (
                video_uuid, title, channel, duration, duration_str,
                file_name, file_path, file_size, thumbnail_path,
                format_name, media_type, source_type, source_url,
                views_count, description, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            video_data['video_uuid'],
            video_data['title'],
            video_data.get('channel', 'Unknown'),
            video_data.get('duration', 0),
            video_data.get('duration_str', '00:00'),
            video_data['file_name'],
            video_data['file_path'],
            video_data.get('file_size', 0),
            video_data.get('thumbnail_path', ''),
            video_data.get('format_name', 'MP4'),
            video_data.get('media_type', 'video'),
            video_data.get('source_type', 'youtube'),
            video_data.get('source_url', ''),
            video_data.get('views_count', 0),
            video_data.get('description', ''),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        conn.commit()
        return cursor.lastrowid

def get_all_videos(query=None, source_filter='all', sort='newest'):
    with get_db() as conn:
        sql = 'SELECT * FROM videos WHERE 1=1'
        params = []
        
        if query:
            sql += ' AND (title LIKE ? OR channel LIKE ? OR description LIKE ?)'
            wildcard = f'%{query}%'
            params.extend([wildcard, wildcard, wildcard])
            
        if source_filter == 'youtube':
            sql += ' AND source_type = "youtube"'
        elif source_filter == 'upload':
            sql += ' AND source_type = "upload"'
        elif source_filter == 'audio':
            sql += ' AND media_type = "audio"'
        elif source_filter == 'video':
            sql += ' AND media_type = "video"'

        if sort == 'newest':
            sql += ' ORDER BY id DESC'
        elif sort == 'oldest':
            sql += ' ORDER BY id ASC'
        elif sort == 'size_desc':
            sql += ' ORDER BY file_size DESC'
        elif sort == 'duration_desc':
            sql += ' ORDER BY duration DESC'
        elif sort == 'title_asc':
            sql += ' ORDER BY title ASC'
        else:
            sql += ' ORDER BY id DESC'

        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

def get_video_by_id(video_id):
    with get_db() as conn:
        cursor = conn.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_video_by_uuid(video_uuid):
    with get_db() as conn:
        cursor = conn.execute('SELECT * FROM videos WHERE video_uuid = ?', (video_uuid,))
        row = cursor.fetchone()
        return dict(row) if row else None

def delete_video_by_id(video_id):
    with get_db() as conn:
        cursor = conn.execute('SELECT file_path, thumbnail_path FROM videos WHERE id = ?', (video_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        file_path = row['file_path']
        thumb_path = row['thumbnail_path']
        
        # Delete files from disk if they exist
        if file_path:
            full_file_path = file_path if os.path.isabs(file_path) else os.path.join(os.path.dirname(__file__), 'static', file_path)
            if os.path.exists(full_file_path):
                try:
                    os.remove(full_file_path)
                except OSError:
                    pass
                
        if thumb_path:
            full_thumb_path = thumb_path if os.path.isabs(thumb_path) else os.path.join(os.path.dirname(__file__), 'static', thumb_path)
            if os.path.exists(full_thumb_path):
                try:
                    os.remove(full_thumb_path)
                except OSError:
                    pass
                
        conn.execute('DELETE FROM videos WHERE id = ?', (video_id,))
        conn.commit()
        return True

def get_stats():
    with get_db() as conn:
        cursor = conn.execute('''
            SELECT 
                COUNT(*) as total_videos,
                COALESCE(SUM(file_size), 0) as total_bytes,
                COALESCE(SUM(duration), 0) as total_duration,
                SUM(CASE WHEN source_type = 'youtube' THEN 1 ELSE 0 END) as yt_count,
                SUM(CASE WHEN source_type = 'upload' THEN 1 ELSE 0 END) as upload_count
            FROM videos
        ''')
        row = cursor.fetchone()
        return dict(row) if row else {
            'total_videos': 0,
            'total_bytes': 0,
            'total_duration': 0,
            'yt_count': 0,
            'upload_count': 0
        }
