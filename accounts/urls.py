# accounts.urls.py 
from django.urls import path, re_path
from django.contrib.auth import views as auth_views
from .views import (
        AccountHomeView, 
        AccountEmailActivateView,
        UserDetailUpdateView
        )

app_name = 'accounts'

urlpatterns  = [
    path('', AccountHomeView.as_view(), name='home'),
    path('details/', UserDetailUpdateView.as_view(), name='user-update'),
    #path('history/products/', UserProductHistoryView.as_view(), name='user-product-history'),
    re_path('email/confirm/(?P<key>[0-9A-Za-z]+)/', AccountEmailActivateView.as_view(), name='email-activate'),
    path('email/resend-activation/', AccountEmailActivateView.as_view(), name='resend-activation'),
]