# -*- coding: utf-8 -*-
"""
4399 注册接口加密逻辑的 Python 等价实现。

对应前端 ptlogin.3304399.net/resource/validation.js：

    function encryptAES(IdVal) {
        return CryptoJS.AES.encrypt(IdVal, 'lzYW5qaXVqa').toString();
    }

CryptoJS.AES.encrypt(明文, 口令字符串) 走的是 PasswordBasedCipher 分支，等价于
OpenSSL `enc -aes-256-cbc -md md5` 的默认行为：

  1. 随机生成 8 字节 salt
  2. EVP_BytesToKey(MD5, iterations=1) 派生 32 字节 key + 16 字节 iv
  3. AES-256-CBC + PKCS7 填充
  4. 输出 Base64("Salted__" || salt || ciphertext)

口令固定为 'lzYW5qaXVqa'，salt 每次随机，故同一明文每次密文不同，服务端自行解密。
"""

import base64
import hashlib
import os

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# validation.js 中硬编码的口令
PASSPHRASE = b"lzYW5qaXVqa"

SALT_LEN = 8
KEY_LEN = 32  # AES-256
IV_LEN = 16
OPENSSL_MAGIC = b"Salted__"


def _evp_bytes_to_key(password: bytes, salt: bytes,
                      key_len: int = KEY_LEN, iv_len: int = IV_LEN) -> tuple:
    """OpenSSL EVP_BytesToKey / CryptoJS EvpKDF 等价实现。

    CryptoJS 默认 hasher 为 MD5、iterations 为 1：
        D_1 = MD5(password || salt)
        D_i = MD5(D_{i-1} || password || salt)
    串联后前 key_len 字节为 key，紧随其后的 iv_len 字节为 iv。
    """
    derived = b""
    prev = b""
    while len(derived) < key_len + iv_len:
        prev = hashlib.md5(prev + password + salt).digest()
        derived += prev
    return derived[:key_len], derived[key_len:key_len + iv_len]


def encrypt_aes(plaintext: str, passphrase: bytes = PASSPHRASE) -> str:
    """等价于前端 encryptAES(plaintext)。

    返回 Base64 字符串，即 register.do 表单里 password / passwordveri /
    realname / idcard 字段应当提交的值。
    """
    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")

    salt = os.urandom(SALT_LEN)
    key, iv = _evp_bytes_to_key(passphrase, salt)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(plaintext, AES.block_size))

    return base64.b64encode(OPENSSL_MAGIC + salt + ciphertext).decode("ascii")


def decrypt_aes(b64_ciphertext: str, passphrase: bytes = PASSPHRASE) -> str:
    """解密（仅用于自校验 / 抓包比对，注册流程本身不需要）。"""
    raw = base64.b64decode(b64_ciphertext)
    if not raw.startswith(OPENSSL_MAGIC):
        raise ValueError("不是 CryptoJS/OpenSSL 口令加密格式（缺少 Salted__ 头）")

    salt = raw[len(OPENSSL_MAGIC):len(OPENSSL_MAGIC) + SALT_LEN]
    ciphertext = raw[len(OPENSSL_MAGIC) + SALT_LEN:]

    key, iv = _evp_bytes_to_key(passphrase, salt)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ciphertext), AES.block_size).decode("utf-8")


if __name__ == "__main__":
    # 用 Node 侧真实 CryptoJS 产出的密文做交叉验证
    vectors = [
        ("123456", "U2FsdGVkX1+1bKZxpY7Ylq/fd2QviBhkLPAyu1yahh8="),
        ("MyPassw0rd", "U2FsdGVkX1+s5mp+r0e+umM3VRMCr/evnlhm9OA+PP4="),
        ("张三", "U2FsdGVkX182F11qW4YVF1S3sU2ULhTYYfH59WtS0jU="),
        ("330100194207072598",
         "U2FsdGVkX1/A+7bTVGphtag9YYr1XzmRUf+t01G8kM4nKo9/h68e8wkKFEWIGrrI"),
    ]
    ok = True
    for plain, ct in vectors:
        got = decrypt_aes(ct)
        flag = "OK " if got == plain else "FAIL"
        if got != plain:
            ok = False
        print(f"[{flag}] JS密文 -> Python解密: {plain!r} == {got!r}")

    # 反向：Python 加密 -> 前端可解
    for plain, ct in vectors:
        mine = encrypt_aes(plain)
        back = decrypt_aes(mine)
        flag = "OK " if back == plain else "FAIL"
        if back != plain:
            ok = False
        print(f"[{flag}] Python加密 -> 自解: {plain!r} -> {mine[:32]}...")

    print("\nALL PASS" if ok else "\nSOME FAILED")
