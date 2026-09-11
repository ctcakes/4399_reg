if (Messenger.shouldOpen) {
	msnger.ask("has:__protocol").then(function (data) {
		if (data.params) {
			document
				.getElementById("reg_eula_agree")
				.removeAttribute("checked");
		}
	});
} else {
	if (
		"__protocol" in parent.unionLoginProps &&
		!parent.unionLoginProps.__protocol
	) {
		document.getElementById("reg_eula_agree").removeAttribute("checked");
	}
}

var captchaId;
var captcha;
//弹窗
var PopupView = PopupView || {};

//验证码
PopupView.fcaptcha = function (data, phone, appId, v, sig, btn) {
	var pview = this;
	ue.dialog({
		id: "j-fcaptcha_popup",
		content: baidu.template("fcaptchaTmpl", data),
		lock: true,
		init: function () {
			var _pop = this,
				$pop = this.obj;

			$pop.find(".j-btn_close").bind("click", function () {
				_pop.close();

				return false;
			});
			captchaId = $("#j-captcha1").attr("captchaId");
			captcha;
			$("#j-captcha1").bind("click", function () {
				var $this = $(this);
				captchaId = $this.attr("captchaId");
				$this.attr(
					"src",
					"//ptlogin.4399.com/ptlogin/captcha.do?captchaId=" +
						captchaId +
						"&xx=" +
						captchabv++
				);
			});

			$pop.find(".j-btn_sure").bind("click", function () {
				captcha = $("#fCaptcha").val();
				if (captcha) {
					sendRegPhoneCodeAjax(
						phone,
						appId,
						v,
						sig,
						btn,
						_pop,
						captchaId,
						captcha
					);
				} else {
					$(".j-ftip").html("验证码不能为空");
				}
			});
		}
	});
};

if (!isPhoneReg) {
	/*第三方登录板式一*/
	if (document.getElementById("j-reg4399-btn") != null) {
		document.getElementById("j-reg4399-btn").onclick = function () {
			document.getElementById("popup_thirdparty_reg").style.display =
				"none";
			document.getElementById("j-popLogin_box").style.display = "block";
			document.getElementById("username").focus();
			if (Messenger.shouldOpen) {
				msnger.emit("setIFrameHeight", {
					iframeId: "popup_reg_frame",
					height: document.body.offsetHeight
				});
			} else {
				parent.window.UniLogin.setIframeHeight("popup_reg_frame");
			}
		};
	}
}

// 完善防沉迷
if (document.getElementById("addinfo") != null) {
	document.getElementById("addinfo").onclick = function () {
		var fcm_info_div = document.getElementById("fcm_info_div"),
			placeholder_ele = document.getElementById("placeholder_div"),
			status = +this.getAttribute("data-status");
		if (status) {
			fcm_info_div.style.display = "block";
			placeholder_ele.style.display = "none";
			this.setAttribute("data-status", "0");
		} else {
			fcm_info_div.style.display = "none";
			placeholder_ele.style.display = "block";
			this.setAttribute("data-status", "1");
		}

		// if (isPhoneReg) {
		// 	parent.window.UniLogin.setIframeHeight("popup_email_reg_frame");
		// } else {
		if (Messenger.shouldOpen) {
			msnger.emit("setIFrameHeight", {
				iframeId: "popup_reg_frame",
				height: document.body.offsetHeight
			});
		} else {
			parent.window.UniLogin.setIframeHeight("popup_reg_frame");
		}

		//}
	};
}

// if(parent.window.unionLoginProps.__level){
//    document.getElementById('j-level').value=parent.window.unionLoginProps.__level;
// }

(function () {
	var $password = document.getElementById("j-password"),
		$passwordveri = document.getElementById("j-passwordveri");

	YJ.on($password, "blur", function () {
		checkInput($password, "password", true);

		verifyPwdEqual($passwordveri, $password);
	});

	YJ.on($passwordveri, "blur", function () {
		verifyPwdEqual($passwordveri, $password);
	});
})();
