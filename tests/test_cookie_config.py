import os

from youtube_downloader import get_cookiefile_path, get_yt_dlp_base_options


def test_cookiefile_path_uses_project_cookie_file():
    path = get_cookiefile_path()
    assert path is not None
    assert os.path.exists(path)
    assert os.path.basename(path) == 'cookies.txt'


def test_yt_dlp_base_options_include_cookiefile():
    options = get_yt_dlp_base_options()
    assert 'cookiefile' in options
    assert options['cookiefile'] == get_cookiefile_path()
