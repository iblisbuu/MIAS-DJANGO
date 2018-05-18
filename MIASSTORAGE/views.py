"""
Process the request and gives back the corresponding response for /storage url
Author: Jeonkyu Lee, Murali krishnan and Umang Patel
Last Tested: 6/12/2017 by Murali Krishnan
Verified with: Python 3.6, Django 1.11
"""

from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.conf import settings
import requests
from MIASSTORAGE import storage
from datetime import datetime
import cv2
import numpy as np

###########################################################################
#  Def Name     : storageHome
#  Input        : request
#  Output       : response(a html page along with the data processed for each request which is a context)
#  Purpose      : To give response to each request for the url '/storage'
#  Author       : Jeonkyu Lee, Murali Krishnan and Umang Patel
#  Last Modified: 06/12/2017 by Murali Krishnan
############################################################################
def storageHome(request):
	if request.method == 'POST':
		'''
		This block returns the response for the post request for /storage url
		'''
		if request.POST['submit'] == 'Upload Image':
			'''
			This block uploads the selected image to the bucket
			'''
			#myfile contains the list of selected images by the user
			myfile = request.FILES.getlist('image')
			#add_bucket contains the bucket selected by the user
			add_bucket = request.POST['uploadImageHiddenBucket']
			#new_images contains the list of images to be added to the selected bucket
			new_images = []
			#This statement creates object for each selected image in the bucket
			for files in myfile:
				temp_file = storage.create_object(add_bucket,files,'ad')['name']
				new_images.append(temp_file)
			#objects gets the list of all buckets and its images
			objects = getlist()
			my_dict={'loggedIn': True, 'new_images':new_images,'add_bucket':add_bucket,'objects':objects}
		elif request.POST['submit'] == 'Upload Folder':
			'''
			This block uploads the selected folder with the images to the bucket
			'''
			#myfile contains the list of selected images by the user
			myfile = request.FILES.getlist('folderimage')
			#add_bucket contains the bucket selected by the user
			add_bucket = request.POST['uploadFolderHiddenBucket']
			#new_images contains the list of images to be added to the selected bucket
			new_images = []
			#This statement creates object for each selected image in the bucket
			for files in myfile:
				temp_file = storage.create_object(add_bucket,files,'ad')['name']
				new_images.append(temp_file)
			#objects gets the list of all buckets and its images
			objects = getlist()
			my_dict={'loggedIn': True, 'new_images':new_images,'add_bucket':add_bucket,'objects':objects}
		elif request.POST['submit'] == 'Delete Image':
			'''
			This block deletes the selected images in the bucket
			'''
			#delete_list contains the list of images to be deleted selected by the user
			delete_list = (request.POST['hiddenimages']).split(",")
			delete_bucket = delete_list[0]
			deleted_images = []
			#This statement deletes the images in the bucket
			for deleteobject in delete_list[1:]:
				storage.delete_object(delete_bucket,deleteobject)
				deleted_images.append(deleteobject)
			#objects gets the list of all buckets and its images
			objects = getlist()
			my_dict={'loggedIn': True, 'deleted_images':deleted_images,'delete_bucket':delete_bucket,'objects':objects}
		elif request.POST['submit'] == 'Add Customer':
			'''
			This block creates a bucket in the google cloud storage
			'''
			#add_customer contains the name of the bucket to be created in the google cloud storage
			add_customer = request.POST['addcust']
			#This statement creates the bucket in the google cloud storage
			storage.create_bucket(settings.CLOUD_PROJECT_ID,add_customer.lower())
			#objects gets the list of all buckets and its images
			objects = getlist()
			my_dict={'loggedIn': True, 'add_customer':add_customer,'objects':objects}
		elif request.POST['submit'] == 'Delete Customer':
			'''
			This block deletes a bucket in the google cloud storage
			'''
			#delete_customer contains the name of the bucket to be deleted in the google cloud storage
			delete_customer = request.POST['deletebucket']
			#This statement deletes the selected bucket in the google cloud storage
			storage.delete_bucket(delete_customer)
			#objects gets the list of all buckets and its images
			objects = getlist()
			my_dict={'loggedIn': True, 'delete_customer':delete_customer,'objects':objects}
	else:
		'''
		This block returns the response for the get request for /storage url
		'''
		try:
			#loggedInUser contains the logged in user email
			loggedInUser = request.session['uEmail']
		except:
			#This statement redirects the user to the login page
			return redirect('/login')
		#objects gets the list of all buckets and its images
		objects = getlist()
		my_dict={'loggedIn': True, 'objects':objects}
	#This statement returns the response as a HTML page along with the data to be displayed in it
	return render(request,'storage.html',context=my_dict)
		

###########################################################################
#  Def Name     : getlist
#  Input        : None
#  Output       : list of buckets and its images in the google cloud storage
#  Purpose      : To give list of buckets and its images in the google cloud storage
#  Author       : Jeonkyu Lee, Murali Krishnan and Umang Patel
#  Last Modified: 06/12/2017 by Murali Krishnan
############################################################################
def getlist():
	#response contains the list of all buckets for the selected project
	response = storage.list_buckets(settings.CLOUD_PROJECT_ID)
	#objects contains the list of all images in each bucket
	objects = []
	#This statement gets the bucket whose name starts with datacore
	for lstbct in response['items']:
		if lstbct['name'].startswith('datacore'):
			#blobs contains all the images from each bucket
			blobs = []
			#respobject contains all the images from each bucket
			respobject = storage.list_objects(lstbct['name'])
			#This statement gets the details of all the images in each bucket
			for index, bct in enumerate(respobject):
				#if 'segment/' not in str(bct['name']):
				blobs.append({ 'index': index, 'name': str(bct['name']), 'public_url': 'https://storage.googleapis.com/'+lstbct['name']+'/'+str(bct['name']), 'timecreated': datetime.strptime(str(bct['timeCreated']),  '%Y-%m-%dT%H:%M:%S.%fZ'), 'type': str(bct['contentType'])})
			objects.append({'bucketName': lstbct['name'], 'blobs': blobs, 'totalBlobs': len(blobs)})
	return objects
