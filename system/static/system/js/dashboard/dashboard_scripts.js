$(document).ready(function () {
    $.ajax({
        url: $("#job_chart").attr("data-url"),
        dataType: 'json',
        success: function (data) {
            let ctx = document.getElementById('job_chart').getContext('2d');
            let job_chart = new Chart(ctx, data);
        }
    });

    $.ajax({
        url: $("#chart").attr("data-url"),
        dataType: 'json',
        success: function (data) {
            Highcharts.chart("chart", data);
        }
    });
});

