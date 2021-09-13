$(document).ready(function () {
    $("#file_select_button").click(function() {open_file_select()});
});

function BtnLoading(elem) {
    $(elem).attr("data-original-text", $(elem).html());
    $(elem).prop("disabled", true);
    $(elem).html('<span class="spinner-grow spinner-grow-sm" role="status" aria-hidden="true"></span> Loading...');
}

function BtnReset(elem) {
    $(elem).prop("disabled", false);
    $(elem).html($(elem).attr("data-original-text"));
}

function open_file_select() {
    let selected_option = $("#id_file_storage option:selected").text().toLowerCase()
    if (selected_option === "dropbox") {
        Dropbox.choose(options = {
            linkType: "direct",
            extensions: ['.ksp'],
            success: function (files) {
                let file = files[0]
                $('#id_file_data').val(JSON.stringify(file));
                $('.selected_file span').html(file.name);
            },
        });
    } else if (selected_option === "rendershare") {
        BtnLoading($("#file_select_button"));
        $.ajax({
            url: 'get_file_select',
            dataType: 'json',
            success: function (data) {
                if (data.data) {
                    $('#select_file_modal').replaceWith(data.data);
                    $("#select_file_modal").modal("show");
                    BtnReset($("#file_select_button"));
                }
            }
        });

    }
}
