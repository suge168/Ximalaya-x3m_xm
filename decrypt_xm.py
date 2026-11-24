import base64
import io
import struct
import sys
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from mutagen.easyid3 import ID3
from wasmtime import Instance, Module, Store

BASE = Path(__file__).resolve().parent
WASM = BASE / "xm_encryptor.wasm"
OUT = BASE / "output"
XM_KEY = b"ximalayaximalayaximalayaximalaya"


def printable_prefix(data: bytes) -> bytes:
    for i, b in enumerate(data):
        if b < 0x20 or b > 0x7E:
            return data[:i]
    return data


def read_id3(data: bytes) -> dict:
    tag = ID3(io.BytesIO(data), v2_version=3)

    def text(key: str) -> str:
        return "" if tag.get(key) is None else str(tag[key])

    iv_hex = text("TSRC") or text("TENC")
    if not iv_hex:
        raise RuntimeError("ID3 中没有 TSRC/TENC，无法确定 AES IV")

    return {
        "title": text("TIT2"),
        "album": text("TALB"),
        "artist": text("TPE1"),
        "track": int(text("TRCK")),
        "iv": bytes.fromhex(iv_hex),
        "size": int(text("TSIZ")),
        "header_size": tag.size,
        "encoding_technology": text("TSSE"),
    }


def decrypt_xm(raw: bytes, exports, memory, store) -> tuple[dict, bytes]:
    info = read_id3(raw)
    encrypted = raw[info["header_size"]:info["header_size"] + info["size"]]

    stage1 = AES.new(XM_KEY, AES.MODE_CBC, info["iv"]).decrypt(
        pad(encrypted, 16)
    )
    stage1 = printable_prefix(stage1)

    track_id = str(info["track"]).encode()
    stack_pointer = exports["a"](store, -16)
    data_offset = exports["c"](store, len(stage1))
    track_offset = exports["c"](store, len(track_id))

    memory.write(store, stage1, data_offset)
    memory.write(store, track_id, track_offset)
    exports["g"](
        store,
        stack_pointer,
        data_offset,
        len(stage1),
        track_offset,
        len(track_id),
    )

    values = struct.unpack(
        "<4i", memory.read(store, stack_pointer, stack_pointer + 16)
    )
    result_pointer, result_length = values[0], values[1]
    result_text = memory.read(
        store, result_pointer, result_pointer + result_length
    ).decode()

    decoded = base64.b64decode(info["encoding_technology"] + result_text)
    final = decoded + raw[info["header_size"] + info["size"]:]
    return info, final


def main() -> None:
    if not WASM.exists():
        raise SystemExit(f"缺少 WASM 模块：{WASM}")

    store = Store()
    module = Module.from_file(store.engine, str(WASM))
    exports = Instance(store, module, []).exports(store)
    memory = exports["i"]

    files = [Path(p) for p in sys.argv[1:]]
    if not files:
        files = sorted(Path(".").glob("*.xm"))
    OUT.mkdir(parents=True, exist_ok=True)

    for src in files:
        info, final = decrypt_xm(src.read_bytes(), exports, memory, store)
        ext = "m4a" if final[4:8] == b"ftyp" else "mp3"
        dst = OUT / (src.stem + "." + ext)
        dst.write_bytes(final)
        print(f"{src.name} -> {dst}")
        print(f"  title={ascii(info['title'])}")
        print(f"  ext={ext}  size={len(final)}  head={final[:16].hex(' ')}")


if __name__ == "__main__":
    main()
