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

    function renderList(data) {
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
            "goto-reading": function () {
              return this.href;
            },
            "remove-reading": function () {
              return this.link;
            },
            "text": function () {
              return "";
            }
          }
        });
        jQuery("li.reading div").on("click", function (event) {
          event.preventDefault();
          window.open(this.parentElement["goto-reading"]);
        });
        jQuery("li.reading").mouseenter(function (event) {
          $(this).children("button.remove-reading").show();
        });
        jQuery("li.reading").mouseleave(function (event) {
          $(this).children("button.remove-reading").hide();
        });
        jQuery(".remove-reading").on("click", function (event) {
          event.preventDefault();
          jQuery.ajax({
            "url": this.parentElement["remove-reading"],
            "method": "DELETE"
          }).done(function() {
            jQuery.ajax({
              "url": "/",
              "method": "GET",
              "dataType": "json"
            }).done(renderList).fail(showError);
          });
        });
      }
    }

    function showError(jqxhr, status, error) {
      console.log('Failed to retrieve data');
      console.log(error);
    }

    jQuery.ajax({
      "url": "/",
      "dataType": "json"
    }).done(renderList).fail(showError);

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
        jQuery.ajax({
          "url": "/",
          "method": "POST",
          "data": jQuery("#add-form").serialize(),
          "dataType": "json"
        }).done(function() {
          jQuery.ajax({
            "url": "/",
            "method": "GET",
            "dataType": "json",
            "crossDomain": true,
            "xhrFields": {"withCredentials": false},
            "headers": {"X-Requested-With": "XMLHTTPRequest"}
          }).done(renderList).fail(showError);
        });
      }
    });

    jQuery("#cancel-button").on("click", function () {
      jQuery("#add-panel").hide();
      jQuery("#click-blocker").hide();
    });

  });
