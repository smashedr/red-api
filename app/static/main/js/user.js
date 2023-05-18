$(document).ready(function() {

    // Get and set the csrf_token
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    // Init the logout form click function
    $('.log-out').on('click', function () {
        $('#log-out').submit();
        return false;
    });

});
