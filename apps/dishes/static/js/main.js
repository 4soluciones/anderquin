$(document).ready(function () {

    /*  Show/Hidden Submenus */
    $('.nav-btn-submenu').on('click', function (e) {
        e.preventDefault();
        var SubMenu = $(this).next('ul');
        var iconBtn = $(this).children('.fa-chevron-right');

        if (SubMenu.hasClass('show-nav-lateral-submenu')) {
            $(this).removeClass('active');
            // iconBtn.removeClass('fa-rotate-90');
            iconBtn.css("transform", "");
            SubMenu.removeClass('show-nav-lateral-submenu');
            SubMenu.slideUp(100, "linear");
        } else {
            $(this).addClass('active');
            // iconBtn.addClass('fa-rotate-90');
            iconBtn.css("transform", "rotate(90deg)");
            SubMenu.addClass('show-nav-lateral-submenu');
            SubMenu.slideDown(100, "linear");
        }

    });

    /*  Show/Hidden Nav Lateral */
    $('.show-nav-lateral').on('click', function (e) {
        e.preventDefault();
        var NavLateral = $('.nav-lateral');
        var PageConten = $('.page-content');
        if (NavLateral.hasClass('active')) {
            NavLateral.removeClass('active');
            PageConten.removeClass('active');
        } else {
            NavLateral.addClass('active');
            PageConten.addClass('active');
        }
    });

    /*  Exit system buttom */
    /*
    $('.btn-exit-system').on('click', function(e){
        e.preventDefault();
        Swal.fire({
            title: 'Are you sure to close the session?',
            text: "You are about to close the session and exit the system",
            type: 'question',
            showCancelButton: true,
            confirmButtonColor: '#3085d6',
            cancelButtonColor: '#d33',
            confirmButtonText: 'Yes, exit!',
            cancelButtonText: 'No, cancel'
        }).then((result) => {
            if (result.value) {
                //window.location=$(this).attr('href');
            }
        });
    });
*/


});



(function ($) {
    $(window).on("load", function () {
        // $(".page-content, .nav-lateral-content").mCustomScrollbar({
        // 	theme:"dark",
        // 	scrollbarPosition: "inside",
        // 	autoHideScrollbar: true,
        // 	scrollButtons: {enable: true}
        // });

        // used to display a toast
        toastr.options = {
            "closeButton": true,
            "debug": false,
            "newestOnTop": true,
            "progressBar": true,
            "positionClass": "toast-top-right",
            "preventDuplicates": true,
            "onclick": null,
            "showDuration": "300",
            "hideDuration": "1000",
            "timeOut": "5000",
            "extendedTimeOut": "1000",
            "showEasing": "swing",
            "hideEasing": "linear",
            "showMethod": "fadeIn",
            "hideMethod": "fadeOut"
        }


    });
})(jQuery);
