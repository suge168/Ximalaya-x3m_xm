# Ximalaya x3m、xm 

喜马拉雅 `.xm` / `.x3m` 音频格式解密与格式分析工具。

本项目整理了两套互不兼容的容器格式的还原方法，并提供可直接运行的 Python 脚本。仅用于学习文件格式、个人备份**你有权访问**的音频内容。

> 本项目不破解付费内容、不绕过登录与授权。是否可下载/播放取决于你自己的账号权限。

## 格式对比

| 项目 | `.xm` | `.x2m` / `.x3m` |
|---|---|---|
| 来源 | PC 客户端 | Android 客户端 |
| 文件头 | 标准 `ID3` 标签 | 前 1024 字节被打乱 |
| 加密范围 | `ID3_size` 之后的 `TSIZ` 字节 | 仅前 1024 字节 |
| 核心算法 | AES-256-CBC + WASM + base64 | 置换表 + 固定 32 字节 XOR |
| 依赖 | ID3 标签、WASM 模块 | 无第三方依赖 |
| 输出 | M4A / MP3 | M4A |

## 目录结构

```text
.
├── README.md
├── requirements.txt
├── xm_encryptor.wasm        # .xm 解密所需的 WASM 模块
├── decrypt_xm.py            # .xm 解密脚本
└── decrypt_x3m.py           # .x3m 解密脚本（无需第三方依赖）
```

## 安装

```bash
pip install -r requirements.txt
```

`.x3m` 解密不需要安装任何依赖；只有 `.xm` 解密需要 `pycryptodome`、`mutagen`、`wasmtime`。

## 使用

### 解密 `.xm`

把 `xm_encryptor.wasm` 放在 `decrypt_xm.py` 同一目录。

```bash
# 解密指定文件
python decrypt_xm.py "某个文件.xm" "另一个文件.xm"

# 解密当前目录下所有 .xm
python decrypt_xm.py
```

输出目录为脚本同级的 `output/`。

### 解密 `.x3m`

```bash
# 解密指定文件
python decrypt_x3m.py "某个文件.x3m"

# 批量（支持通配符）
python decrypt_x3m.py download/*.x3m

# 解密当前目录下所有 .x3m
python decrypt_x3m.py
```

输出目录为脚本同级的 `output/`，文件扩展名改为 `.m4a`。

## 原理简述

### `.xm`

1. 读取 ID3 标签，取得 `TSIZ`、AES IV（`TSRC` 或 `TENC`）、base64 前缀（`TSSE`）和曲目号。
2. 对 `raw[ID3_size : ID3_size + TSIZ]` 做 AES-256-CBC 解密，密钥固定为 `ximalayaximalayaximalayaximalaya`。
3. 把可打印的解密结果和曲目号写入 `xm_encryptor.wasm` 内存，调用导出函数 `g`。
4. 将返回字符串与 `TSSE` 拼接后 base64 解码，再加回尾部原始数据，得到标准音频文件。

### `.x3m`

只处理前 1024 字节：

```text
encrypted_header = data[0:1024]

for dst in 0..1023:
    src = scramble_table[dst]
    data[dst] = encrypted_header[src] XOR key[dst % 32]
```

第 1024 字节之后保持不变。`scramble_table` 是 `0..1023` 的固定排列，`key` 是固定的 32 字节。解密后文件头恢复为 `ftypM4A`。

## 校验

解密成功的文件通常具有以下特征：

- `data[4:8] == b"ftyp"`
- `data[8:12] in (b"M4A ", b"isom")`
- 文件大小与输入 x3m 一致（x3m 算法只替换前 1024 字节）

可用 `mutagen` 读取时长：

```python
from mutagen.mp4 import MP4
print(MP4("output/example.m4a").info.length)
```

## 参考项目

- [Ximalaya-XM-Decrypt](https://github.com/sld272/Ximalaya-XM-Decrypt/) — `.xm` 算法与 `xm_encryptor.wasm`



## 免责声明

本项目仅供学习研究和个人备份使用。请遵守平台服务条款和相关法律法规，尊重内容创作者版权，勿用于侵权或商业用途。使用本项目产生的后果由使用者自行承担。
