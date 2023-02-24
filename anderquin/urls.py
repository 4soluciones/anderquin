"""anderquin URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# import autocomplete_light

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.decorators import login_required

from django.conf import settings
from django.conf.urls.static import static

from apps.hrm.views import Home
from apps.users.views import Login, logoutUser

# autocomplete_light.autodiscover()
# admin.autodiscover()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dishes/', include(('apps.dishes.urls', 'dishes'))),
    path('api/v1/', include(('apps.apidishes.urls', 'apidishes'))),
    path('vetstore/', include(('apps.vetstore.urls', 'vetstore'))),
    path('hrm/', include(('apps.hrm.urls', 'hrm'))),
    path('comercial/', include(('apps.comercial.urls', 'comercial'))),
    path('sales/', include(('apps.sales.urls', 'sales'))),
    path('buys/', include(('apps.buys.urls', 'buys'))),
    path('accounting/', include(('apps.accounting.urls', 'accounting'))),

    path('', login_required(Home.as_view()), name='dashboard'),
    path('accounts/login/', Login.as_view(), name='login'),
    path('logout/', login_required(logoutUser), name='logout'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# if settings.DEBUG:
#     import debug_toolbar
    # urlpatterns += [
        # static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
        # static(settings.STATIC_URL, document_root=settings.STATIC_ROOT),
        # path('__debug__/', include(debug_toolbar.urls)),
    # ]
