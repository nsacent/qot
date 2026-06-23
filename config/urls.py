"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/locations/", include("apps.locations.urls")),
    path("api/v1/categories/", include("apps.categories.urls")),
    path("api/v1/listings/", include("apps.listings.urls")),
    path("api/v1/favorites/", include("apps.favorites.urls")),
    path("api/v1/chats/", include("apps.chats.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/moderation/", include("apps.moderation.urls")),
    path("api/v1/admin-panel/", include("apps.adminpanel.urls")),
    path("api/v1/seller/", include("apps.seller.urls")),
    path("api/v1/sellers/", include("apps.sellers.urls")),
    path("api/v1/home/", include("apps.home.urls")),
    path("api/v1/me/", include("apps.me.urls")),
    path("api/v1/searches/", include("apps.searches.urls")),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)