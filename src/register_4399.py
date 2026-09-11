# -*- coding: utf-8 -*-
"""
4399 注册接口客户端 —— 脚本内输入明文，加密由脚本完成。

逆向目标
--------
页面  https://ptlogin.4399.com/ptlogin/regFrame.do?regMode=reg_normal&...
脚本  //ptlogin.3304399.net/resource/validation.js?v=320
接口  POST https://ptlogin.4399.com/ptlogin/register.do

加密逻辑（validation.js，全文只有这一处加解密）
-----------------------------------------------
    function encryptAES(IdVal) {
        return CryptoJS.AES.encrypt(IdVal, 'lzYW5qaXVqa').toString();
    }

口令 'lzYW5qaXVqa' 硬编码在前端；等价于 OpenSSL
`enc -aes-256-cbc -md md5 -pass pass:lzYW5qaXVqa` 的默认行为：
随机 8 字节 salt -> EVP_BytesToKey(MD5, 1 次) 派生 key/iv
-> AES-256-CBC + PKCS7 -> Base64("Salted__" + salt + ciphertext)

哪些字段加密
------------
见 validation.js 的 check_reg_new()：
    password / passwordveri / realname / idcard 四个字段全部走 encryptAES，
    前提是隐藏域 <input id="j-sec" value="1"> 的 sec == 1；
    sec != 1 时原样明文提交（实测服务端稳定下发 1）。

username / email 不加密，明文提交。
登录接口用的是同一套加密（check_login / check_phone_login 同样调 encryptAES）。

用法
----
    python register_4399.py --dry-run \\
        --username myaccount123 --password MyPass123 \\
        --realname 张三 --idcard 110101190001010014
"""

import argparse
import json
import re
import time

import requests

from crypto_4399 import encrypt_aes

REG_FRAME_URL = "https://ptlogin.4399.com/ptlogin/regFrame.do"
REGISTER_URL = "https://ptlogin.4399.com/ptlogin/register.do"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://my.4399.com/account/login",
    "Origin": "https://ptlogin.4399.com",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 对齐 ucenter.js 中 my.4399.com 的 uloginProp（regMode 见 UniLogin.showPopupReg）
REG_FRAME_PARAMS = {
    "regMode": "reg_normal",
    "postLoginHandler": "refreshParent",
    "displayMode": "embed",
    "appId": "my",
    "externalLogin": "qq",
    "regIdcard": "true",
    "autoLogin": "false",
    "includeFcmInfo": "false",
    "expandFcmInput": "true",
    "fcmFakeValidate": "false",
    "mainDivId": "popup_reg_div",
    "iframeId": "popup_reg_frame",
}

# 需要 encryptAES 的字段 -> 明文来源的 payload key
ENCRYPTED_FIELDS = {
    "password": "password",
    "passwordveri": "passwordveri",
    "realname": "realname",
    "idcard": "idcard",
}


class Register4399:
    def __init__(self, headers: dict = None, timeout: int = 20):
        self.session = requests.Session()
        self.session.headers.update(headers or DEFAULT_HEADERS)
        self.session.proxies = {
            "http": "http://127.0.0.1:7897",
            "https": "http://127.0.0.1:7897",
        }
        self.timeout = timeout
        self.hidden_fields = {}
        self.sec = "1"

    # ------------------------------------------------------------ 1. 拉表单
    def fetch_reg_frame(self) -> dict:
        """GET regFrame.do：拿隐藏域初值 + 服务端预填用户名，并领取 USESSIONID。

        USESSIONID 是后续 register.do 的会话凭据，缺了会被拒。
        """
        params = dict(REG_FRAME_PARAMS, v=str(int(time.time() * 1000)))
        resp = self.session.get(REG_FRAME_URL, params=params,
                                timeout=self.timeout)
        resp.raise_for_status()
        html = resp.text

        fields = {}
        for m in re.finditer(r'<input[^>]*type="hidden"[^>]*>', html):
            tag = m.group(0)
            name = re.search(r'name="([^"]+)"', tag)
            value = re.search(r'value="([^"]*)"', tag)
            if name:
                fields[name.group(1)] = value.group(1) if value else ""

        self.hidden_fields = fields
        # sec == 1 时前端才做 AES，否则明文
        self.sec = fields.get("sec", "1")

        suggested = ""
        m = re.search(r'<input(?=[^>]*id="j-username")[^>]*>', html, re.S)
        if m:
            v = re.search(r'value="([^"]*)"', m.group(0))
            if v:
                suggested = v.group(1)

        return {"hidden_fields": fields, "suggested_username": suggested,
                "sec": self.sec, "cookies": self.session.cookies.get_dict()}

    # ------------------------------------------------------------ 2. 造载荷
    def build_payload(self, username: str, password: str,
                      password2: str = None, realname: str = "",
                      idcard: str = "", email: str = "") -> dict:
        """明文入参 -> register.do 期望的密文表单。"""
        if not self.hidden_fields:
            self.fetch_reg_frame()

        raw = {
            "password": password,
            "passwordveri": password if password2 is None else password2,
            "realname": realname,
            "idcard": idcard,
        }

        payload = dict(self.hidden_fields)
        payload.update({
            "username": username,
            "email": email,
            "reg_eula_agree": "on",
        })
        for field, source in ENCRYPTED_FIELDS.items():
            value = raw[source]
            payload[field] = encrypt_aes(value) if self.sec == "1" else value
        return payload

    # ------------------------------------------------------------ 3. 提交
    def submit(self, payload: dict) -> requests.Response:
        return self.session.post(
            REGISTER_URL, data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Referer": REG_FRAME_URL},
            timeout=self.timeout,
        )

    # ------------------------------------------------------------ 4. 判读
    @staticmethod
    def parse_result(resp: requests.Response) -> dict:
        """服务端两种响应模板：错误页 / 重渲染表单，错误信息位置不同。"""
        html = resp.text

        m = re.search(r'<div class="login_error">\s*<strong>(.*?)</strong>',
                      html, re.S)
        if m:
            return {"ok": False, "message": _clean(m.group(1))}

        m = re.search(r'<div id="Msg"[^>]*>(.*?)</div>', html, re.S)
        if m and _clean(m.group(1)):
            return {"ok": False, "message": _clean(m.group(1))}

        if "login_comfirm" in html or "reg_success" in html:
            return {"ok": True, "message": _clean(html)[:200]}

        return {"ok": False, "message": "未识别的响应", "raw_len": len(html)}

    # ------------------------------------------------------------ 5. 一步到位
    def register(self, username: str, password: str, password2: str = None,
                 realname: str = "", idcard: str = "", email: str = "") -> dict:
        if not self.hidden_fields:
            self.fetch_reg_frame()
        payload = self.build_payload(username, password, password2,
                                     realname, idcard, email)
        resp = self.submit(payload)
        result = self.parse_result(resp)
        result["status_code"] = resp.status_code
        return result


def _clean(s: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>|&nbsp;', '', s)).strip()


def main():
    ap = argparse.ArgumentParser(description="4399 注册接口（明文入参，内部 AES）")
    ap.add_argument("--username", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--password2", default=None, help="默认与 --password 相同")
    ap.add_argument("--realname", default="", help="真实姓名（防沉迷）")
    ap.add_argument("--idcard", default="", help="身份证号（防沉迷）")
    ap.add_argument("--email", default="")
    ap.add_argument("--dry-run", action="store_true",
                    help="只打印将提交的密文载荷，不发注册请求")
    args = ap.parse_args()

    client = Register4399()
    info = client.fetch_reg_frame()
    print(f"[*] sec={info['sec']}  服务端建议用户名={info['suggested_username']}")
    print(f"[*] USESSIONID={info['cookies'].get('USESSIONID')}")

    payload = client.build_payload(args.username, args.password,
                                   args.password2, args.realname,
                                   args.idcard, args.email)

    print("\n[*] 提交载荷（已加密）:")
    for k, v in payload.items():
        print(f"    {k} = {v}")

    print("\n[*] 明文 -> 密文对照:")
    print(f"    password     {args.password!r} -> {payload['password']}")
    print(f"    passwordveri {payload and (args.password2 or args.password)!r}"
          f" -> {payload['passwordveri']}")
    if args.realname:
        print(f"    realname     {args.realname!r} -> {payload['realname']}")
    if args.idcard:
        print(f"    idcard       {args.idcard!r} -> {payload['idcard']}")

    if args.dry_run:
        print("\n[*] --dry-run，未发送注册请求")
        return

    result = client.register(args.username, args.password, args.password2,
                             args.realname, args.idcard, args.email)
    print("\n[*] 注册结果:", json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
