"""MIAS URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from MIASHOME import views as homeView
from MIASDETECTION import views as detectionView
from MIASSEGMENTATION import views as segmentationView
from MIASSTORAGE import views as storageView
from MIASWORKFLOW import views as workflowView
from MIASIMAGECROP import views as imagecropView
from MIASLOGIN import views as loginView
from MIASREGISTRATION import views as registrationView
from MIASLOGOUT import views as logoutView
from MIASIMAGESEARCH import views as imageSearchView

urlpatterns = [	
    url(r'^admin/', admin.site.urls),
	url(r'^home', homeView.home),
	url(r'^$', homeView.welcome),	
	url(r'^welcome$', homeView.welcome),
	url(r'^detection', detectionView.detectionHome),
	url(r'^segmentation', segmentationView.segmentationHome),
	url(r'^storage', storageView.storageHome),
	url(r'^workflow', workflowView.workflowHome),
	url(r'^imageCrop', imagecropView.imageCropHome),
	url(r'^login', loginView.miasLogin),
	url(r'^registration', registrationView.miasRegistration),
	url(r'^logout', logoutView.logout),
	url(r'^imageSearch', imageSearchView.imageSearchHome),
]
