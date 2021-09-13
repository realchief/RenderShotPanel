$(document).ready(function () {
    $(".custom-file-input").change(function (event) {
        let files = event.target.files
        let label_name = (files.length > 1) ? files.length + " Files selected" : files[0].name;
        $(this).next('.custom-file-label').html(label_name);
    });
});
