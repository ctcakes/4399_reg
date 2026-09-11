// Verify JS-side crypto using the EXACT file served by ptlogin.3304399.net
const CryptoJS = require('../raw/cryptojs-aes.js');
// same function as validation.js
function encryptAES(v) { return CryptoJS.AES.encrypt(v, 'lzYW5qaXVqa').toString(); }

const samples = process.argv.slice(2);
for (const s of samples) {
  const ct = encryptAES(s);
  // decrypt with the same lib for a self-check
  const pt = CryptoJS.AES.decrypt(ct, 'lzYW5qaXVqa').toString(CryptoJS.enc.Utf8);
  console.log(JSON.stringify({ plain: s, cipher: ct, roundtrip: pt }));
}
