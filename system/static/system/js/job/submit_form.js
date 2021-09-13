$(document).ready(function () {

    modify_setting_form()

    $('#quality_mode').on('change', function () {
        modify_setting_form()
    }).change();

    $(".select2_frame_list").select2({tags: true});
    $(".select2_cameras").select2({tags: true});

    $("#file_select_button").click(function() {open_file_select()});
});

const ws_url = 'wss://' + window.location.host + '/ws/jobs/'
let socket = new ReconnectingWebSocket(ws_url, null, {reconnectInterval: 3000});
socket.onmessage = function (e) {
    let data = JSON.parse(e.data);
    let actions = {
        'update_render_plan': update_render_plan,
        'update_output_format': update_output_format,
        'update_storage': update_storage,
        'set_select_file_modal': set_select_file_modal,

    };
    if (data.action) {
        actions[data.action](data);
    }

};

function BtnLoading(elem) {
    $(elem).attr("data-original-text", $(elem).html());
    $(elem).prop("disabled", true);
    $(elem).html('<span class="spinner-grow spinner-grow-sm" role="status" aria-hidden="true"></span> Choose Project File...');
}

function BtnReset(elem) {
    $(elem).prop("disabled", false);
    $(elem).html($(elem).attr("data-original-text"));
}

$("#version_list_input").change(function () {
    socket.send(JSON.stringify({
        'type': 'update_version_dependencies',
        'data': get_form_data(),
    }));
});

function modify_setting_form() {
    let quality_mode = $("#quality_mode option:selected").text();
    let max_sample_elements = $('.max_samples')
    let custom_samples_elements = $('.custom_samples')

    switch (quality_mode) {
        case "Maximum Samples":
            custom_samples_elements.hide();
            max_sample_elements.show();
            break;
        case "Custom Control":
            max_sample_elements.hide();
            custom_samples_elements.show();
            break;
    }
}

function get_form_data() {
    return {
        'software': $("#software_list_input option:selected").text(),
        'version': $("#version_list_input option:selected").text(),
        'storage': $("#storage_list_input option:selected").text(),
        'render_plan': $("#render_plan_list_input option:selected").text(),
        'output_format': $("#output_format_list_input option:selected").text(),
    }
}

function update_storage(data) {
    $('#storage_list_input').replaceWith(data.data);
}

function update_render_plan(data){
    $('#render_plan_list_input').replaceWith(data.data);
}

function update_output_format(data) {
    $('#output_format_list_input').replaceWith(data.data);
}

function open_file_select() {
    let selected_option = $("#storage_list_input option:selected").text().toLowerCase()
    if (selected_option === "dropbox") {
        Dropbox.choose(options = {
            linkType: "direct",
            extensions: ['.ksp'],
            success: function (files) {
                let file = files[0]
                $('#file_link_input').val(file.link);
                $('#file_name_input').val(file.name);
                $('#file_size_input').val(file.bytes);
                $('#file_id_input').val(file.id);
                $('.selected_file span').html(file.name);
            },
        });
    } else if (selected_option === "rendershare") {
        BtnLoading($("#file_select_button"));
        socket.send(JSON.stringify({
            'type': 'get_select_file_modal',
            'data': null,
        }));

    }
}

function set_select_file_modal(data) {
    $('#select_file_modal').replaceWith(data.html);
    $("#select_file_modal").modal("show");
    BtnReset($("#file_select_button"));
}
