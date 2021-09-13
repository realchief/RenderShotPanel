$(document).ready(function () {
    $("#ticket_search").on("keyup", function () {
        let value = $(this).val().toLowerCase();
        $("#tickets_list a").filter(function () {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
        });
    });

    $('.dropdown-menu a').click(function (e) {
        let value = $(this).text().toLowerCase();
        $("#tickets_list a").filter(function () {
            $(this).toggle($(this).find('div').text().toLowerCase().indexOf(value) > -1)
        });
    });
});

function request_ticket_replies(url, ticket_number) {
    $.ajax({
        url: url,
        data: {'ticket_number': ticket_number,},
        dataType: 'json',
        success: function (data) {
            if (data.html_content) {
                $("#replies_content *").replaceWith(data.html_content);
            }
        }
    });
}
