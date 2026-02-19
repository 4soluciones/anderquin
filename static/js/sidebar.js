/**
 * ERP Sidebar - Funcionalidad del menú lateral
 * Se carga siempre para que funcione en todas las páginas (incluidas las que sobreescriben extrajs)
 */
$(document).ready(function() {
    // Toggle sidebar - ocultar/mostrar completamente (pantalla completa cuando está oculto)
    $('#sidebar-toggle').on('click', function() {
        $('#erp-sidebar').toggleClass('erp-sidebar-hidden');
        $('body').toggleClass('erp-sidebar-hidden');
        var isHidden = $('#erp-sidebar').hasClass('erp-sidebar-hidden');
        localStorage.setItem('erp-sidebar-hidden', isHidden);
        // Overlay solo en móvil cuando el menú está abierto (para cerrar al hacer clic fuera)
        if (window.innerWidth < 992) {
            $('#sidebar-overlay').toggleClass('active', !isHidden);
        }
    });

    // Cerrar sidebar al hacer clic en overlay (móvil)
    $('#sidebar-overlay').on('click', function() {
        $('#erp-sidebar').addClass('erp-sidebar-hidden');
        $('#sidebar-overlay').removeClass('active');
        $('body').addClass('erp-sidebar-hidden');
        localStorage.setItem('erp-sidebar-hidden', 'true');
    });

    // Submenús - toggle al hacer clic en secciones con submenú
    $(document).on('click', '.erp-nav-link[data-submenu]', function(e) {
        e.preventDefault();
        var $item = $(this).closest('.erp-nav-item');
        var $siblings = $item.siblings('.erp-nav-item');
        $siblings.removeClass('open');
        $item.toggleClass('open');
    });

    // Restaurar estado: desktop usa localStorage, móvil siempre empieza oculto
    if (window.innerWidth < 992) {
        $('#erp-sidebar').addClass('erp-sidebar-hidden');
        $('body').addClass('erp-sidebar-hidden');
    } else if (localStorage.getItem('erp-sidebar-hidden') === 'true') {
        $('#erp-sidebar').addClass('erp-sidebar-hidden');
        $('body').addClass('erp-sidebar-hidden');
    }
});
