$(document).ready(function() {

    // Back to Top Button, Function, and Listener
    let mybutton = document.getElementById("btn-back-to-top");
    window.onscroll = function () {
      scrollFunction();
    };
    function scrollFunction() {
        if (document.body.scrollTop > 20 || document.documentElement.scrollTop > 20) {
            mybutton.style.display = "block";
        } else {
            mybutton.style.display = "none";
        }
    }
    mybutton.addEventListener("click", backToTop);
    function backToTop() {
      document.body.scrollTop = 0;
      document.documentElement.scrollTop = 0;
    }

    // Show custom toast-alert classes on load
    $(".toast-alert").each(function() {
        console.log($(this).html());
        let toastAlert = new bootstrap.Toast($(this));
        toastAlert.show();
    });

    // Init a ClipboardJS attribute
    new ClipboardJS('.clip');

});

// Generate a BS toast and show it
function show_toast(message, bsClass = 'info', delay = '5000') {
  let toastContainer = $('.toast-container');
  let toast = $('<div class="toast align-items-center border-0" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="' + delay + '"><div class="d-flex"><div class="toast-body"></div><button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div></div>');
  toast.find('.toast-body').text(message);
  toast.addClass('text-bg-' + bsClass);
  toastContainer.append(toast);
  let jsToast = new bootstrap.Toast(toast);
  jsToast.show();
}
