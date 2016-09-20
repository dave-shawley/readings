require.config({
  paths: {
    "jquery": "lib/jquery-3.1.0.min",
    "transparency": "lib/transparency-0.11.0.min"
  }
});
require(["jquery", "transparency"],
  function (jQuery, transparency) {
    "use strict";
    jQuery.fn.render = transparency.jQueryPlugin;
    jQuery.ajax({
      "url": "/",
      "dataType": "json"
    }).done(function(data, status, jqxhr) {
      data.redirect = data.redirect || "";
      if (data.redirect) {
        document.location.assign(data.redirect);
      } else {
        $("#readings").render(data, {
          "reading-link": {
            "text": function() { return this.title; },
            "href": function() { return this.href; }
          },
          "added": {
            "text": function() {
              var parsed = new Date(this.added);
              return "added (" + parsed.toDateString() + ")";
            }
          }
        });
      }
    }).fail(function(jqxhr, status, error) {
      console.log('Failed to retrieve data');
      console.log(error);
    });

    jQuery("#logout").on("click", function(event) {
      document.location.assign("/logout");
    });
  });
