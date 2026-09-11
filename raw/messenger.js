/**
 * across-domain
 * @param {*} options
 */
function Messenger(options) {
    var options = options || {};
    this.domain = options.domain || document.domain;
    this.target = options.target || window;
    this.targetOrigin = options.targetOrigin || '*';
    this.handles = {};
    if (!document.addEventListener) {
        return false;
    }
    window.addEventListener('message', this.receive.bind(this), false);
}
Messenger.prototype.emit = function (type, params, otherTarget) {
    if (!this.target.postMessage) {
        return false;
    }
    var data = {
        type: type,
        params: params
    };
    // console.debug('=====' + this.domain + '=====post', data);
    (otherTarget || this.target).postMessage(data, this.targetOrigin);
};
Messenger.prototype.receive = function (event) {
    // if (event.origin !== this.targetOrigin) {
    // 	return;
    // }
    // console.debug("=====" + this.domain + "=====receive", event.data);
    var data = event.data;
    if (!data) {
        return false;
    }
    // var pluginHandle = this.pluginHandles[_data.type];
    // pluginHandle && pluginHandle(_data, this);
    var typeHandles = this.handles[data.type] || [];
    if (typeHandles.length) {
        typeHandles.forEach(function (handle) {
            handle(data);
        });
    }
};
Messenger.prototype.ask = function (type, params) {
    var _this = this;
    return new Promise(function (resolve) {
        var replyTypeName = 'reply:' + type;
        var askTypeName = 'ask:' + type;
        _this.emit(askTypeName, params);
        _this.on(replyTypeName, function (res) {
            resolve(res);
        });
    });
};
Messenger.prototype.reply = function (type, handler, otherTarget) {
    var _this = this;
    var replyTypeName = 'reply:' + type;
    var askTypeName = 'ask:' + type;
    var replyHandler = function (data) {
        Promise.resolve(handler(data)).then(function (result) {
            _this.emit(replyTypeName, result, otherTarget);
        });
    };
    this.on(askTypeName, replyHandler);
};
Messenger.prototype.on = function (type, handle) {
    if (!this.handles[type]) {
        this.handles[type] = [];
    }
    this.handles[type].push(handle);
};
Messenger.prototype.off = function (type, handle) {
    if (!this.handles[type]) return;
    if (!handle) {
        this.handles[type] = [];
        return;
    }
    var typeHandles = this.handles[type] || [];
    this.handles[type] = typeHandles.filter(function (_handler) {
        return _handler !== handle;
    });
};
Messenger.shouldOpen = (function () {
    if (/Electron/i.test(navigator.userAgent)) {
        return true;
    }
    function getChromeVersion() {
        var arr = navigator.userAgent.split(' ');
        var chromeVersion = '';
        for (var i = 0; i < arr.length; i++) {
            if (/chrome/i.test(arr[i])) chromeVersion = arr[i];
        }
        if (chromeVersion) {
            return Number(chromeVersion.split('/')[1].split('.')[0]);
        } else {
            return false;
        }
    }
    var version = getChromeVersion();
    return version && version >= 115;
})();
