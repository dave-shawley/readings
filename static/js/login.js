require.config({
  paths: {
    "jquery": "lib/jquery-3.1.0.min",
    "jsrasign": "lib/jsrasign-5.0.15.min"
  }
});
require(["jquery", "jsrasign"],
  function (jQuery, jsrasign) {
    "use strict";
    jQuery("#login").on("submit", function (event) {
      var header = {alg: "HS256", typ: "JWT"}, payload = {},
        hstring, pstring, key, token;

      payload.iss = jQuery("html").parent().attr("location").href;
      payload.nbf = KJUR.jws.IntDate.get("now"); /* valid from NOW          */
      payload.exp = payload.nbf + 300;           /* 'til 5 minutes from NOW */
      payload.csrf = document.cookie.replace(
        /(?:(?:^|.*;\s*)csrf\s*\=\s*([^;]*).*$)|^.*$/, "$1");

      hstring = JSON.stringify(header);
      pstring = JSON.stringify(payload);
      key = CryptoJS.enc.Utf8.parse(jQuery("#password").val()).toString();
      token = KJUR.jws.JWS.sign("HS256", hstring, pstring, key);
      jQuery("#token").val(token);
      jQuery("#password").val("");
    });
  });
