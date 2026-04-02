import ctypes
import json
import os
from ctypes import wintypes


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


_crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

_CryptProtectData = _crypt32.CryptProtectData
_CryptProtectData.argtypes = [
    ctypes.POINTER(_DATA_BLOB),
    wintypes.LPCWSTR,
    ctypes.POINTER(_DATA_BLOB),
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(_DATA_BLOB),
]
_CryptProtectData.restype = wintypes.BOOL

_CryptUnprotectData = _crypt32.CryptUnprotectData
_CryptUnprotectData.argtypes = [
    ctypes.POINTER(_DATA_BLOB),
    ctypes.POINTER(wintypes.LPWSTR),
    ctypes.POINTER(_DATA_BLOB),
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(_DATA_BLOB),
]
_CryptUnprotectData.restype = wintypes.BOOL

_LocalFree = _kernel32.LocalFree
_LocalFree.argtypes = [ctypes.c_void_p]
_LocalFree.restype = ctypes.c_void_p


def _bytes_to_blob(data):
    buf = (ctypes.c_byte * len(data)).from_buffer_copy(data)
    return _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))


def _blob_to_bytes(blob):
    if not blob.pbData:
        return b""
    return ctypes.string_at(blob.pbData, blob.cbData)


def _dpapi_encrypt(plaintext, entropy=b"CCWater"):
    in_blob = _bytes_to_blob(plaintext)
    ent_blob = _bytes_to_blob(entropy) if entropy else _DATA_BLOB()
    out_blob = _DATA_BLOB()
    ok = _CryptProtectData(ctypes.byref(in_blob), None, ctypes.byref(ent_blob), None, None, 0, ctypes.byref(out_blob))
    if not ok:
        raise OSError(ctypes.get_last_error())
    try:
        return _blob_to_bytes(out_blob)
    finally:
        _LocalFree(out_blob.pbData)


def _dpapi_decrypt(ciphertext, entropy=b"CCWater"):
    in_blob = _bytes_to_blob(ciphertext)
    ent_blob = _bytes_to_blob(entropy) if entropy else _DATA_BLOB()
    out_blob = _DATA_BLOB()
    ok = _CryptUnprotectData(ctypes.byref(in_blob), None, ctypes.byref(ent_blob), None, None, 0, ctypes.byref(out_blob))
    if not ok:
        raise OSError(ctypes.get_last_error())
    try:
        return _blob_to_bytes(out_blob)
    finally:
        _LocalFree(out_blob.pbData)


def _config_path(config_dir):
    return os.path.join(config_dir, "ccwater_ai_config.dat")


def load_ai_config(config_dir, default_host="api.deepseek.com"):
    path = _config_path(config_dir)
    if not os.path.exists(path):
        return {"api_host": default_host, "api_key": ""}
    try:
        with open(path, "rb") as f:
            enc = f.read()
        raw = _dpapi_decrypt(enc)
        obj = json.loads(raw.decode("utf-8"))
        host = str(obj.get("api_host") or default_host).strip() or default_host
        key = str(obj.get("api_key") or "").strip()
        return {"api_host": host, "api_key": key}
    except Exception:
        return {"api_host": default_host, "api_key": ""}


def save_ai_config(config_dir, api_host, api_key):
    os.makedirs(config_dir, exist_ok=True)
    host = (api_host or "").strip() or "api.deepseek.com"
    key = (api_key or "").strip()
    raw = json.dumps({"api_host": host, "api_key": key}, ensure_ascii=False).encode("utf-8")
    enc = _dpapi_encrypt(raw)
    with open(_config_path(config_dir), "wb") as f:
        f.write(enc)
    return True


def migrate_ai_config(old_dir, new_dir, default_host="api.deepseek.com"):
    old_path = _config_path(old_dir)
    new_path = _config_path(new_dir)
    if not os.path.exists(old_path) or os.path.exists(new_path):
        return False
    cfg = load_ai_config(old_dir, default_host=default_host)
    save_ai_config(new_dir, cfg.get("api_host", default_host), cfg.get("api_key", ""))
    return True
