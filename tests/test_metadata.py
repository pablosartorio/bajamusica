from core.metadata import build_filename, clean_title, _safe


# ── clean_title ──────────────────────────────────────────────────────────
def test_saca_official_video():
    assert clean_title("Mi Tema (Official Video)") == "Mi Tema"


def test_saca_corchetes_con_lyrics():
    assert clean_title("Mi Tema [Lyrics HD]") == "Mi Tema"


def test_saca_feat_inline():
    assert clean_title("Mi Tema feat. Alguien Más") == "Mi Tema"


def test_conserva_parentesis_normales():
    # "(En Vivo)" no es ruido: no contiene ninguna palabra clave de descarte
    assert clean_title("Mi Tema (En Vivo)") == "Mi Tema (En Vivo)"


def test_colapsa_espacios():
    assert clean_title("Mi   Tema   (Video Oficial)") == "Mi Tema"


# ── _safe ────────────────────────────────────────────────────────────────
def test_safe_elimina_caracteres_invalidos():
    assert _safe('AC/DC: "Best*Of"?') == "ACDC BestOf"


def test_safe_recorta_puntos_y_espacios_de_punta():
    assert _safe("  nombre. ") == "nombre"


def test_safe_limita_largo():
    assert len(_safe("x" * 300)) == 100


# ── build_filename ───────────────────────────────────────────────────────
META = {"artist": "Soda Stereo", "album": "Signos", "title": "Persiana Americana"}


def test_scheme_artist_title():
    assert build_filename(META, "artist_title", ".mp3") == \
        "Soda Stereo - Persiana Americana.mp3"


def test_scheme_artist_album_title():
    assert build_filename(META, "artist_album_title", ".mp3") == \
        "Soda Stereo - Signos - Persiana Americana.mp3"


def test_scheme_album_cae_a_artist_title_sin_album():
    meta = dict(META, album="")
    assert build_filename(meta, "artist_album_title", ".mp3") == \
        "Soda Stereo - Persiana Americana.mp3"


def test_sin_artista_usa_solo_titulo():
    meta = {"artist": "", "album": "", "title": "Persiana Americana"}
    assert build_filename(meta, "artist_title", ".mp3") == "Persiana Americana.mp3"


def test_sin_nada_usa_fallback():
    meta = {"artist": "", "album": "", "title": ""}
    assert build_filename(meta, "artist_title", ".mp3") == "descarga.mp3"
