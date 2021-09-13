/** Show Password */
!function (a) {
    a(function () {
        a('[data-toggle="password"]').each(function () {
            var b = a(this);
            var c = a(this).parent().find(".input-group-text");
            c.css("cursor", "pointer").addClass("input-password-hide");
            c.on("click", function () {
                if (c.hasClass("input-password-hide")) {
                    c.removeClass("input-password-hide").addClass("input-password-show");
                    c.find(".fas").removeClass("fa-eye").addClass("fa-eye-slash");
                    b.attr("type", "text")
                } else {
                    c.removeClass("input-password-show").addClass("input-password-hide");
                    c.find(".fas").removeClass("fa-eye-slash").addClass("fa-eye");
                    b.attr("type", "password")
                }
            })
        })
    })
}(window.jQuery);

function request_output_url(url, job_name) {
    $.ajax({
        url: url,
        data: {'job_name': job_name,},
        dataType: 'json',
        async: false,
        success: function (data) {
            if (data.url) {
                window.open(data.url);
            }
        }
    });
}

function auto_close_alerts() {
    window.setTimeout(function () {
        $(".alert-fade").fadeTo(500, 0).slideUp(500, function () {
            $(this).remove();
        });
    }, 4000);
}

$(function () {
    $('[data-toggle="tooltip"]').tooltip()
})

$(function () {
    $('[data-toggle="popover"]').popover()
})

$('#free_service').popover({trigger: "hover"});
$('#pophover').popover({trigger: "hover"});
$('.dropdown-toggle').dropdown()