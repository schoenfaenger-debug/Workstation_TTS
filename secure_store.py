"""Protects the Euler key with Windows DPAPI; the key never appears in settings.json."""
import base64, ctypes, json, os
from ctypes import wintypes
from pathlib import Path

class DATA_BLOB(ctypes.Structure): _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]
def _blob(data: bytes):
    buf = ctypes.create_string_buffer(data); return DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte))), buf
def save_key(path: Path, key: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt": raise RuntimeError("Sichere Schlüsselablage ist nur unter Windows verfügbar.")
    source, keep = _blob(key.encode()); out = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(ctypes.byref(source), "Euler API Key", None, None, None, 0, ctypes.byref(out)): raise ctypes.WinError()
    try: path.write_text(json.dumps({"dpapi": base64.b64encode(ctypes.string_at(out.pbData, out.cbData)).decode()}), encoding="utf-8")
    finally: ctypes.windll.kernel32.LocalFree(out.pbData)
def load_key(path: Path) -> str:
    if not path.exists(): return ""
    if os.name != "nt": return ""
    raw = base64.b64decode(json.loads(path.read_text(encoding="utf-8"))["dpapi"]); source, keep = _blob(raw); out = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(out)): return ""
    try: return ctypes.string_at(out.pbData, out.cbData).decode()
    finally: ctypes.windll.kernel32.LocalFree(out.pbData)
