# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=[
        ('ffmpeg-bin/ffmpeg.exe', '.'),
        ('ffmpeg-bin/ffprobe.exe', '.'),
    ],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
    ] + collect_data_files('yt_dlp'),
    hiddenimports=[
        'core',
        'core.download',
        'core.jobs',
        'core.metadata',
        'core.playlist',
        'core.search',
        'core.util',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'mutagen',
        'mutagen.mp3',
        'mutagen.mp4',
        'mutagen.id3',
        'mutagen._tags',
        'musicbrainzngs',
        'flask',
        'flask.templating',
        'jinja2',
        'jinja2.ext',
        'werkzeug',
        'werkzeug.serving',
        'werkzeug.debug',
    ] + collect_submodules('yt_dlp'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'scipy', 'PIL', 'cv2',
        'pandas', 'IPython', 'notebook', 'pytest',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='bajamusica',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='bajamusica',
)
