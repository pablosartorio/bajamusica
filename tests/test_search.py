from core.search import _is_youtube_url


def test_url_watch_clasica():
    assert _is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


def test_url_corta_youtu_be():
    assert _is_youtube_url("https://youtu.be/dQw4w9WgXcQ")


def test_url_shorts():
    assert _is_youtube_url("https://www.youtube.com/shorts/dQw4w9WgXcQ")


def test_url_sin_esquema_ni_www():
    assert _is_youtube_url("youtube.com/watch?v=dQw4w9WgXcQ")


def test_url_con_parametros_extra():
    assert _is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s")


def test_texto_comun_no_es_url():
    assert not _is_youtube_url("canciones de pescetti")


def test_otro_sitio_no_es_youtube():
    assert not _is_youtube_url("https://vimeo.com/12345")
