import base64
import glob
import struct
import sys
import zlib
from pathlib import Path

# 来自 unlock-music/src/decrypt/ximalaya.ts 的 x3mScrambleTable
# 1024 个 uint16，按小端打包后 zlib 压缩再 base64
_X3M_TABLE_B64 = """
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
"""

KEY = bytes.fromhex(
    "333938396431313161616435363133393430"
    "6634666334346236333962323932"
)
TABLE = struct.unpack(
    "<1024H",
    zlib.decompress(base64.b64decode("".join(_X3M_TABLE_B64.split()))),
)

HEADER_SIZE = 1024


def decrypt_x3m(data: bytes) -> bytes:
    """解密单个 .x3m 文件的字节内容，返回标准 M4A 字节。"""
    if len(data) < HEADER_SIZE:
        raise ValueError("文件小于 1024 字节，不是有效的 x3m")

    buf = bytearray(data)
    encrypted_header = bytes(buf[:HEADER_SIZE])
    for dst, src in enumerate(TABLE):
        buf[dst] = encrypted_header[src] ^ KEY[dst % len(KEY)]
    return bytes(buf)


def main() -> None:
    files: list[Path] = []
    for pattern in sys.argv[1:]:
        files.extend(Path(p) for p in glob.glob(pattern))
    if not files:
        files = sorted(Path(".").glob("*.x3m"))

    out_dir = Path("./output")
    out_dir.mkdir(parents=True, exist_ok=True)

    ok_count = 0
    for src in files:
        result = decrypt_x3m(src.read_bytes())
        out = out_dir / (src.stem + ".m4a")
        out.write_bytes(result)

        ok = result[4:8] == b"ftyp" and result[8:12] in (b"M4A ", b"isom")
        print(f"{src.name} -> {out}")
        print(f"  size={len(result)}  header={result[:12].hex(' ')}  valid={ok}")
        ok_count += int(ok)

    print(f"\n总计处理 {len(files)} 个文件，其中 {ok_count} 个校验通过。")


if __name__ == "__main__":
    main()
