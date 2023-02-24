//Language in datatables
var datatable_language = {
    "sProcessing": "Procesando...",
    "sLengthMenu": "Mostrar _MENU_ registros",
    "sZeroRecords": "No se encontraron resultados",
    "sEmptyTable": "Ningún dato disponible en esta tabla",
    "sInfo": "Mostrando registros del _START_ al _END_ de un total de _TOTAL_ registros",
    "sInfoEmpty": "Mostrando registros del 0 al 0 de un total de 0 registros",
    "sInfoFiltered": "(filtrado de un total de _MAX_ registros)",
    "sInfoPostFix": "",
    "sSearch": "Buscar:",
    "sUrl": "",
    "sInfoThousands": ",",
    "sLoadingRecords": "Cargando...",
    "oPaginate": {
        "sFirst": "Primero",
        "sLast": "Último",
        "sNext": "Siguiente",
        "sPrevious": "Anterior"
    },
    "oAria": {
        "sSortAscending": ": Activar para ordenar la columna de manera ascendente",
        "sSortDescending": ": Activar para ordenar la columna de manera descendente"
    },
    "decimal": ",",
    "thousands": "."
};



// $(window).load(function () {
// // $(window).resize(function () {
//     // $("body").prepend("<div>" + $(window).width() + "</div>");
//     //MOBILE DETECT
//     var w_width = $(window).width();
//     //console.log(w_width);
//     if (w_width < 768) {
//         // $(".template-web").remove();
//         console.log("template-web remove");
//     //$('nav.navbar').removeClass('navbar-fixed-top');
//     } else {
//         // $(".template-mobile").remove();
//         console.log("template-mobile remove");
//     }
// });

$(document).ready(function () {

    $("#sidebar-wrapper ul li").click(function(){
        remove_active();
        $(this).addClass('active');
    });

    function remove_active() {
         var _delete = $("#sidebar-wrapper ul").find('li');
        _delete.each(function(){
            $(this).removeClass('active');
        });
    };



    $('.get-page').click(function (event) {
        event.preventDefault();

            $('#loading').css('display', 'block');

            $('#portfolio').hide().fadeIn();


            var data_url = $(this).attr('data-url');

            var self = $(this);
            console.log("data_url: " + data_url);


            $.ajax({
                // url: data_url, // the endpoint /get/
                url: '/vetstore/get_page/',
                type: "GET", // http method
                data: {
                    // csrfmiddlewaretoken: $("input[name=csrfmiddlewaretoken]").val(),
                    data_url: data_url
                },
                // dataType: 'html',
                // async: true,
                dataType: 'json',
                // handle a successful response
                success: function (response) {
                    $('#portfolio').html(response.page);
                    $('#alerts').html(response.alert);
                    $('#loading').css('display', 'none');


                    if(response.list){
                        $('.list-products').html(response.list);
                    }
                    if(response.form){
                        $('#left-modal .modal-body').html(response.form);
                    }

                },
                error: function (xhr, errmsg, err) {
                    console.log(xhr.status + ": " + xhr.responseText); // provide a bit more info about the error to the console
                },
                fail:function (response) {
                    $('#alerts').html(response.alert);
                }
            });

    });

    /*Simple javascript toast notifications.*/
    toastr.options = {
        closeButton: true,
        progressBar: false,
        showMethod: 'slideDown',
        hideMethod : 'slideUp',
        newestOnTop: false,
        timeOut: 3000
    };


});
