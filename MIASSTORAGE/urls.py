from django.conf.urls import url
from MIASSTORAGE import views as storageView

urlpatterns=['MIASSTORAGE.views'
    url(r'^uploadobject', storageView.uploadobject),
]
