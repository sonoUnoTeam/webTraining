"""
URL configuration for SiteWeb project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from userApp import views
from django.conf.urls.i18n import i18n_patterns


from userApp import views

urlpatterns = [
    path("", views.home, name='home'),
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path("trainingApp/", include("trainingApp.urls")),
    path('userApp/', include('userApp.urls')),
]

urlpatterns = [
    *i18n_patterns(*urlpatterns, prefix_default_language=True),
    ]

# Media fuera de i18n_patterns (sin prefijo /en/). static() solo funciona con DEBUG,
# por eso con SERVE_MEDIA se registra la vista serve directamente.
if settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]