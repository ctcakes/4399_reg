# 4399 注册接口 JS 逆向任务记录

## 目标

- 入口页面：`https://www.4399.com/index_pc.htm` → 注册按钮 → `//my.4399.com/account/login`
- 注册接口：`POST https://ptlogin.4399.com/ptlogin/register.do`
- 目标：脚本内输入明文，由脚本完成服务端可接受的加密

## Phase 1 — Observe（观察）

`index_pc.htm` 的"注册"入口指向 `my.4399.com/account/login`，该页加载统一登录组件
`//ptlogin.3304399.net/resource/ucenter.js?v=191225`。

`ucenter.js` 中注册面板由 `UniLogin.genRegFrameSrc(regMode)` 构造，落点为：

```
//ptlogin.<loginDomain>/ptlogin/regFrame.do?regMode=reg_normal&...&iframeId=popup_reg_frame
```

**关键点**：`regMode` 必须为 `reg_normal`。用 `regMode=0` 请求拿到的是残缺表单
（用户名 input 没有 `name` 属性，无法提交）；`reg_normal` 才是完整注册表单。

观察到的证据：

| 项 | 值 |
|---|---|
| 页面 | `https://ptlogin.4399.com/ptlogin/regFrame.do?regMode=reg_normal&...` |
| 表单 action | `/ptlogin/register.do` |
| 提交方式 | 原生 form POST，非 XHR |
| 加密脚本 | `//ptlogin.3304399.net/resource/validation.js?v=320` |
| 依赖库 | `//ptlogin.3304399.net/resource/cryptojs-aes.js?v=320` |
| 会话凭据 | `regFrame.do` 下发 `USESSIONID` cookie（`Domain=4399.com`），`register.do` 依赖它 |
| 翻页参数 | `sec=1`（隐藏域 `#j-sec`，实测稳定下发 1） |

## Phase 2 — Capture（采样）

`validation.js` 全文只有一处加解密入口：

```js
function encryptAES(IdVal) {
    return CryptoJS.AES.encrypt(IdVal, 'lzYW5qaXVqa').toString();
}
```

调用点全部集中在 `check_reg_new()` / `check_reg()` / `check_login()` 等校验函数，
注册流程（`check_reg_new`）中受同一开关控制：

```js
var $secv = document.getElementById('j-sec').value;

var _psdv = $secv == 1 ? encryptAES(_p1.value) : _p1.value;
document.getElementById('j-psd').value = _psdv;

var _psdvi = $secv == 1 ? encryptAES(_p2.value) : _p1.value;
document.getElementById('j-psd-veri').value = _psdvi;

// 姓名、身份证同理
var _xmv     = $secv == 1 ? encryptAES(_xm)     : _xm;
var _idcardv = $secv == 1 ? encryptAES(_idcard) : _idcard;

// 手机注册时手机号也走 encryptAES 写入 #j-sjphone
```

结论：**`password` / `passwordveri` / `realname` / `idcard` 四个字段加密**；
`username`、`email` 明文。

## Phase 3 — Rebuild（本地复现）

`CryptoJS.AES.encrypt(明文, 口令字符串)` 走的是 PasswordBasedCipher 分支，
等价于 OpenSSL `enc -aes-256-cbc -md md5` 默认行为。核对 `cryptojs-aes.js` 确认：

- `c.algo.EvpKDF` 默认 `{keySize:4, hasher:MD5, iterations:1}`
- `c.kdf.OpenSSL.execute(a,b,c,d)`：`d||(d=WordArray.random(8))`（8 字节 salt），
  `keySize: b+c`（AES 的 8+4=12 words = 48 字节），拆成 key(32) + iv(16)
- `c.format.OpenSSL.stringify`：`[1398893684,1701076831]`(= `Salted__`) ‖ salt ‖ ciphertext，再 Base64
- 填充 `cfg.padding` 默认 PKCS7

Python 侧实现见 `src/crypto_4399.py`。

## Phase 4 — Patch / 验证

**本地交叉验证**（`src/verify_js.js` 直接 `require` 站点上下载的 `cryptojs-aes.js`）：

```
[OK ] JS密文 -> Python解密: '123456' == '123456'
[OK ] JS密文 -> Python解密: 'MyPassw0rd' == 'MyPassw0rd'
[OK ] JS密文 -> Python解密: '张三' == '张三'
[OK ] JS密文 -> Python解密: '330100194207072598' == '330100194207072598'
[OK ] Python加密 -> 自解: 4/4
ALL PASS
```

**服务端在线验证**（全部使用非法/合成数据，未创建任何账号）：

| 实验 | 载荷 | 服务端响应 | 说明 |
|---|---|---|---|
| 非法用户名 | `username="!!bad name probe!!"` | `用户名格式错误` | 请求格式被正确解析 |
| 合法用户名 + 非法身份证 | AES 加密全部字段，`idcard` 明文为 `123` | `wrong idcard` | 身份证为非法值被拒 |
| 明文身份证（对照） | `idcard="123"` 不加密 | `wrong idcard` | 该错误在密码校验之前短路，无法用于判断密码 |
| 合法校验位身份证 + 合成姓名 | `idcard=110101190001010014`（1900-01-01 合成号） | `您的身份证异常或错误` | **越过格式校验，进入实名核验** |

第三条对照组说明 `wrong idcard` 属于格式层短路，不能证明解密；
第四条是关键证据：同一个 AES 密文 `idcard` 字段**通过了格式校验**并推进到
"身份证异常或错误"（实名库核验）阶段 —— 若服务端未正确解开 AES，
绝无可能走到这一层。这同时证明服务端确实以 `lzYW5qaXVqa` 解密，
且 `realname` / `idcard` 走的是本方案还原的算法。

### 已知边界

- `password` / `passwordveri` 两个字段的在线验证**未做**：服务端在实名核验未通过前
  不进入密码校验分支，而通过实名核验需要真实姓名 + 对应身份证号，属于他人身份信息，
  不适合也不应使用。
- 该字段的判定依据是源码链路等价性 —— `encryptAES` 是全文唯一的加密函数，
  `password` / `realname` / `idcard` 在 `check_reg_new()` 中受同一个 `sec == 1`
  开关、调用同一个函数；其中 `realname` / `idcard` 已被服务端实测解密成功。
- 若后续要闭环，需要一个可用的实名信息，或抓一次真实浏览器注册的完整请求，
  用 `crypto_4399.decrypt_aes()` 解出 `password` 字段比对即可（该函数已实现并验证）。

## 成果

| 文件 | 说明 |
|---|---|
| `src/crypto_4399.py` | `encrypt_aes()` / `decrypt_aes()`，EVP_BytesToKey(MD5) + AES-256-CBC + PKCS7 + OpenSSL 封装 |
| `src/register_4399.py` | 完整客户端：`fetch_reg_frame()` → `build_payload()` → `submit()` → `parse_result()` |
| `src/verify_js.js` | 用真实站点 JS 产出密文做交叉验证 |

用法：

```bash
python register_4399.py --dry-run \
    --username mytestacct001 --password MyPass123 \
    --realname 张三 --idcard 110101190001010014
```

去掉 `--dry-run` 即真实提交。

## 服务端响应模板

两种，错误信息位置不同，客户端 `parse_result()` 两种都覆盖：

1. 错误页：`<div class="login_error"><strong>wrong idcard<br>&nbsp;</strong></div>`
2. 重渲染表单：`<div id="Msg">用户名格式错误</div>`

## 备注

- 该加密是**可逆的固定密钥对称加密**，口令硬编码在前端，属于传输层混淆而非安全防护；
  服务端可解，任何人也可解。同一明文每次密文不同（salt 随机）。
- 同一套 `encryptAES` 也用于登录接口（`check_login` / `check_phone_login`），
  如需逆向登录复用同一实现即可。
