$(document).ready(function(){

	/*  Show/Hidden Submenus */
	$('.nav-btn-submenu').on('click', function(e){
		e.preventDefault();
		var SubMenu=$(this).next('ul');
		var iconBtn=$(this).children('.fa-chevron-right');

		if(SubMenu.hasClass('show-nav-lateral-submenu')){
			$(this).removeClass('active');
			// iconBtn.removeClass('fa-rotate-90');
			iconBtn.css("transform","");
			SubMenu.removeClass('show-nav-lateral-submenu');
			SubMenu.slideUp(100,"linear");
		}
		else{
			$(this).addClass('active');
			// iconBtn.addClass('fa-rotate-90');
			iconBtn.css("transform","rotate(90deg)" );
			SubMenu.addClass('show-nav-lateral-submenu');
			SubMenu.slideDown(100,"linear");
		}

	});

	/*  Show/Hidden Nav Lateral */
	$('.show-nav-lateral').on('click', function(e){
		e.preventDefault();
		let NavLateral=$('.nav-lateral');
		let PageContent=$('.page-content');
		if(NavLateral.hasClass('active')){
			NavLateral.removeClass('active');
			PageContent.removeClass('active');
		}else{
			NavLateral.addClass('active');
			PageContent.addClass('active');
		}
	});

	/*  Exit system button */
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

$(document).ready(function () {

// MEGA MENU

	$('.navbar-light .dmenu').hover(function () {
        $(this).find('.sm-menu').first().stop(true, true).slideDown(150);
    }, function () {
        $(this).find('.sm-menu').first().stop(true, true).slideUp(105)
    });


});

$(document).ready(function() {

	$(".megamenu").on("click", function(e) {
		e.stopPropagation();
	});

});



(function($){
    $(window).on("load",function(){
    	
        $(".page-content, .nav-lateral-content").mCustomScrollbar({
        	theme:"dark",
        	scrollbarPosition: "inside",
        	autoHideScrollbar: true,
        	scrollButtons: {enable: true}
        });

		// used to display a toast
		toastr.options = {
		  "closeButton": true,
		  "debug": false,
		  "newestOnTop": true,
		  "progressBar": true,
		  "positionClass": "toast-top-full-width",
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

		$('#mCSB_2_container').css({'height': '100% !important'});

    });


})(jQuery);


    CanvasJS.addCultureInfo("es",
        {
            decimalSeparator: ",",// Observe ToolTip Number Format
            digitGroupSeparator: ".", // Observe axisY labels
            months: ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]

        });
