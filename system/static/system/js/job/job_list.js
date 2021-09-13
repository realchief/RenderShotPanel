$(document).ready(function () {
    let infinite = new Waypoint.Infinite({
        element: $('.infinite-container')[0],
        onBeforePageLoad: function () {
            $('.loading').show();
        },
        onAfterPageLoad: function ($items) {
            $('.loading').hide();
        }
    });

    $("#jobs_search").on("keyup", function () {
        filter_jobs();
    });

    $('#text_filters a').click(function (e) {
        e.preventDefault();
        $('#text_filters li').removeClass('active');
        $(this).parent().tab('show');
        $(".search-txt:text").val(this.id.split("_")[0]);
        filter_jobs();
    });

    $("#check_all").click(function () {
        $('input:checkbox').not(this).prop('checked', this.checked);
    });

    $('#delete-selected-jobs').click(function (e) {
        socket.send(JSON.stringify({
            'type': 'request_delete_jobs',
            'jobs': get_selected_jobs()
        }));
    });

    $('#suspend-selected-jobs').click(function (e) {
        socket.send(JSON.stringify({
            'type': 'request_suspend_jobs',
            'jobs': get_selected_jobs()
        }));
    });

});

const ws_url = 'wss://' + window.location.host + '/ws/jobs/'
let socket = new ReconnectingWebSocket(ws_url, null, {reconnectInterval: 3000});
socket.onmessage = function (e) {
    let data = JSON.parse(e.data);
    let actions = {
        'update_job': update_job,
        'add_job': add_job,
        'delete_job': delete_job,
        'set_change_plan': set_change_plan,
        'set_job_details': set_job_details,
        'set_job_error_reports': set_job_error_reports,
        'set_resubmit_job': set_resubmit_job,
        'show_messages': show_messages,
    };
    if (data.action){
        actions[data.action](data);
        filter_jobs();
    }

};

function filter_jobs() {
    let value = $(".search-txt:text").val().toLowerCase();
    $("#job_list_table tr").not(':first').filter(function () {
        $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
    });
}

function get_selected_jobs() {
    let selected_jobs = []
    $('input:checkbox:checked').each(function () {
        selected_jobs.push($(this).val());
    });
    return selected_jobs
}

function add_job(data) {
    $("#job_list_table tbody").prepend(data.html);

}

function update_job(data) {
    $('#job_item_' + data.job_id).replaceWith(data.html);

}

function delete_job(data) {
    $('#job_item_' + data.job_id).remove();

}

function request_pause_resume(job) {
    socket.send(JSON.stringify({
        'type': 'request_pause_resume',
        'jobs': [job,]
    }));
}

function request_delete_job(job) {
    socket.send(JSON.stringify({
        'type': 'request_delete_job',
        'jobs': [job,]
    }));
}

function get_job_details(job) {
    socket.send(JSON.stringify({
        'type': 'get_job_details',
        'job_name': job
    }));
}

function set_job_details(data) {
    $('#job_details_modal').replaceWith(data.html);
    $("#job_details_modal").modal("show");
}

function get_job_error_reports(job) {
    socket.send(JSON.stringify({
        'type': 'get_job_error_reports',
        'job_name': job
    }));
}

function set_job_error_reports(data) {
    $('#job_error_modal').replaceWith(data.html);
    $("#job_error_modal").modal("show");
}

function get_change_plan(job) {
    socket.send(JSON.stringify({
        'type': 'get_change_plan',
        'job_name': job
    }));
}

function set_change_plan(data) {
    $('#change_plan_modal').replaceWith(data.html);
    $("#change_plan_modal").modal("show");
}

function request_change_plan(job) {
    let selected_plan = $("#change_plan_select_input option:selected")
    socket.send(JSON.stringify({
        'type': 'request_change_plan',
        'job_name': job,
        'plan_name': selected_plan.text(),
        'plan_id': selected_plan.val(),
    }));
    $("#change_plan_modal").modal("hide");
}

function get_resubmit_job(job) {
    socket.send(JSON.stringify({
        'type': 'get_resubmit_job',
        'job_name': job
    }));
}

function set_resubmit_job(data) {
    $('#resubmit_job_modal').replaceWith(data.html);
    $("#resubmit_job_modal").modal("show");

}

function request_resubmit_job(job) {
    let frame_list = $("#resubmit_job_input").val()
    socket.send(JSON.stringify({
        'type': 'request_resubmit_job',
        'job_name': job,
        'frame_list': frame_list,
    }));
    $("#resubmit_job_modal").modal("hide");
}

function show_messages(data) {
    $('.rs_table').prepend(data.html);
    auto_close_alerts()
}