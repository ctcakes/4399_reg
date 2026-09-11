/*
 * fix：解决部分浏览器第三方登录页以新tab打开后返回不到来源页
 */

function getDocCookie(name) {
    var strcookie = document.cookie;
    var arrcookie = strcookie.split('; ');
    for (var i = 0; i < arrcookie.length; i++) {
        var arr = arrcookie[i].split('=');
        if (arr[0] == name) {
            return arr[1];
        }
    }
    return '';
}

function setCookie(name, value, expire, path, domain, secure) {
    var val = name + '=' + escape(value);
    if (expire) {
        var date = new Date();
        if (expire < 30 * 86400) {
            expire = date.getTime() + expire * 1000;
            date.setTime(expire);
        }
        val += ';expires=' + date.toGMTString();
    }
    if (path) {
        val += ';path=' + path;
    }
    if (domain) {
        val += ';domain=' + domain;
    }
    if (secure) {
        val += ';secure';
    }
    document.cookie = val;
}

function getClassName(para, obj) {
    obj = obj || document;
    if (obj.getElementsByClassName) {
        return obj.getElementsByClassName(para);
    } else {
        var boxClass = obj.getElementsByTagName('*');
        var arrClass = [];
        for (var i = 0; i < boxClass.length; i++) {
            var nameBox = boxClass[i].className.split(' ');
            for (var j = 0; j < nameBox.length; j++) {
                if (nameBox[j] == para) {
                    arrClass.push(boxClass[i]);
                }
            }
        }
    }
    return arrClass;
}

function addEvent(elem, type, handle) {
    if (elem.addEventListener) {
        elem.addEventListener(type, handle, false);
    } else if (elem.attachEvent) {
        elem.attachEvent('on' + type, function () {
            handle.call(elem);
        });
    } else {
        elem['on' + type] = handle;
    }
}

String.prototype.bool = function () {
    return /^true$/i.test(this);
};

function string2Json(param) {
    var _object = {};
    var _xx = param.split('|');
    for (var i = 0; i < _xx.length; i++) {
        var _m = _xx[i].split('-');
        if (_m[0] == 'needVerifyIdcard') {
            _m[1] = _m[1].bool();
        }
        _object[_m[0]] = _m[1];
    }
    return _object;
}

function checkOpenerCookie() {
    var timerId = 1;
    var timerObj = {};

    function getPauthCookie() {
        // thOpenerCk：第三方授权结果页自定义cookie
        if (getDocCookie('thOpenerCk') && getDocCookie('Pauth')) {
            var _params = string2Json(getDocCookie('thOpenerCk'));
            if (Messenger.shouldOpen) {
                msnger.emit('UniLogin.loginPostHandle', _params);
            } else {
                window.parent.UniLogin.loginPostHandle(_params);
            }
            stopCheck();
        }
    }

    function startCheck() {
        var id = timerId++;
        timerObj[id] = true;
        function timerFn() {
            if (!timerObj[id]) return;
            getPauthCookie();
            setTimeout(timerFn, 1000);
        }
        timerFn();
    }

    function stopCheck() {
        timerObj = {};
        setCookie('thOpenerCk', 0, -1, '/', '4399.com');
    }

    return {
        start: startCheck,
        stop: stopCheck
    };
}

var _checkOpenerCookie = checkOpenerCookie();

_checkOpenerCookie.start();

try {
    /*弹窗登录框，关闭按钮*/
    var _par = window.parent.document.getElementById('loginDiv');
    if (_par) {
        addEvent(getClassName('login_close', _par)[0], 'click', function () {
            _checkOpenerCookie.stop();
        });
    }
} catch (error) {}
