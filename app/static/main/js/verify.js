$(document).ready(function() {

    $(".form-control").focus(function() {
        $(this).removeClass('is-invalid');
    });

} );

function g_captcha_callback(data) {
    console.log(data);
    if ($('#verify-btn').hasClass('disabled')) {
        return;
    }
    var formData = new FormData($('#verify-form')[0]);
    $.ajax({
        url: window.location.pathname,
        type: 'POST',
        data: formData,
        beforeSend: function (jqXHR) {
            $('#verify-btn').addClass('disabled');
        },
        complete: function () {
            $('#verify-btn').removeClass('disabled');
        },
        success: function (data, textStatus, jqXHR) {
            console.log('Status: ' + jqXHR.status + ', Data: ' + JSON.stringify(data));
            $("#verify-form").hide();
            $("#verify-success").show();
        },
        error: function (data, textStatus) {
            console.log('Status: ' + data.status + ', Response: ' + data.responseText);
            try {
                console.log(data.responseJSON);
                if (data.responseJSON.hasOwnProperty('error_message')) {
                    alert(data.responseJSON['error_message'])
                } else {
                    $($('#contact-form').prop('elements')).each(function () {
                        if (data.responseJSON.hasOwnProperty(this.name)) {
                            $('#' + this.name + '-invalid').empty().append(data.responseJSON[this.name]);
                            $(this).addClass('is-invalid');
                        }
                    });
                }
            } catch (error) {
                console.log(error);
                alert('Fatal Error: ' + error)
            }
        },
        cache: false,
        contentType: false,
        processData: false
    });
    return false;
}
