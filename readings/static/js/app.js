require.config({
  paths: {
    "jquery": "lib/jquery-3.1.0.min",
    "moment": "lib/moment-2.15.0.min",
    "transparency": "lib/transparency-0.11.0.min"
  }
});
require(["jquery", "moment", "transparency"],
  function (jQuery, moment, transparency) {
    "use strict";
    jQuery.fn.render = transparency.jQueryPlugin;
    jQuery.ajax({
      "url": "/",
      "dataType": "json"
    }).done(function (data) {
      data.redirect = data.redirect || "";
      if (data.redirect) {
        document.location.assign(data.redirect);
      } else {
        jQuery("#readings").render(data, {
          "added": {
            "text": function () {
              var parsed = moment(this.added);
              return "added " + parsed.fromNow();
            }
          },
          "link": {
            "href": function () {
              return this.href;
            },
            "text": function () {
              return "";
            }
          }
        });
        jQuery("li.reading").on("click", function (event) {
          event.preventDefault();
          window.open(this.href);
        });
      }
    }).fail(function (jqxhr, status, error) {
      console.log('Failed to retrieve data');
      console.log(error);
    });

    jQuery("#logout").on("click", function (event) {
      event.preventDefault();
      document.location.assign("/logout");
    });

    jQuery("#add-reading").on("click", function () {
      jQuery("#add-title").val("");
      jQuery("#add-url").val("");
      jQuery("#click-blocker").show();
      jQuery("#add-panel").show();
    });

    jQuery("#add-button").on("click", function (event) {
      event.preventDefault();

      var title = document.getElementById("add-title"),
        url = document.getElementById("add-url");
      if (title.validity.valid && url.validity.valid) {
        jQuery("#add-panel").hide();
        jQuery("#click-blocker").hide();
        jQuery("#add-form").submit();
      }
    });

    jQuery("#cancel-button").on("click", function () {
      jQuery("#add-panel").hide();
      jQuery("#click-blocker").hide();
    });

  });
