"""
Process the request and gives back the corresponding response for /imageCrop url
Author: Jeonkyu Lee and Murali krishnan
Last Tested: 6/12/2017 by Murali Krishnan
Verified with: Python 3.6, Django 1.11
"""

from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.conf import settings
from google.cloud import storage as gStorage
from MIASSTORAGE import storage
from datetime import datetime
import time
from google.cloud import vision
from PIL import Image, ImageDraw
import json
import requests
import base64
from io import BytesIO, StringIO
import numpy as np
import os

#adImages contains the list of advertisement images
adImages = []
#nonAdImages contains the list of non advertisement images
nonAdImages = []
#objects contains the total images in the selected bucket
objects = {}

###########################################################################
#  Def Name     : imageCropHome
#  Input        : request
#  Output       : response(a html page along with the data processed for each request which is a context)
#  Purpose      : To give response to each request for the url '/imageCrop'
#  Author       : Jeonkyu Lee and Murali Krishnan 
#  Last Modified: 06/12/2017 by Murali Krishnan
############################################################################
def imageCropHome(request):
	global adImages
	global nonAdImages
	global objects
	if request.method == 'GET':
		'''
		This block returns the response for the get request
		'''
		try:
			#loggedInUser contains the email of the user if he/she has logged in
			loggedInUser = request.session['uEmail']
		except:
			#This statement redirects the user to the welcome page if he/she has not logged in
			return redirect('/welcome')
		#response contains the list of all the buckets for the selected project
		response = storage.list_buckets(settings.CLOUD_PROJECT_ID)
		#This statement gets only the bucket whose name starts with datacore
		for lstbct in response['items']:
			if lstbct['name'].startswith('datacore'):
				#blobs contains the list of cropped and the images in the root folder of each bucket
				blobs = []
				#respobject contains the list of all the images in the bucket
				respobject = storage.list_objects(lstbct['name'])
				#This statement gets only the cropped images and the images in the root folder of each bucket
				for index, bct in enumerate(respobject):
					#This statement gets the cropped images in the bucket
					if 'segment/ad/cropped' in str(bct['name']):
						blobs.append({'index': index, 'name': str(bct['name']),
									  'public_url': 'https://storage.googleapis.com/' + lstbct['name'] + '/' + str(
										  bct['name']),
									  'timecreated': datetime.strptime(str(bct['timeCreated']),
																	   '%Y-%m-%dT%H:%M:%S.%fZ'),
									  'type': str(bct['contentType'])})									  
					else:	
						#This statement gets the images in the root folder of the bucket
						if 'segment/' in str(bct['name']):
							pass
						else:
							blobs.append({'index': index, 'name': str(bct['name']),
									      'public_url': 'https://storage.googleapis.com/' + lstbct['name'] + '/' + str(
										  bct['name']),
									      'timecreated': datetime.strptime(str(bct['timeCreated']),
																	   '%Y-%m-%dT%H:%M:%S.%fZ'),
									      'type': str(bct['contentType'])})
				objects.update({lstbct['name']: blobs})
		#context contains the data to be passed to the HTML page for the post request
		context = {
			'loggedIn' : True,
			'operation' : 'get',
			'objects': objects,
		}
		#This statement returns the response as a HTML page along with the data to be displayed in it
		return render(request, 'imageCropping.html', context)
	else:
		if request.POST['submit'] == 'Perform Image Crop':
			'''
			This block returns the data for the selected images to perform cropping
			'''
			#totalSelectedImages contains the list of images selected by the user
			totalSelectedImages = []
			#selectedCropImages contains the list of images cropped by the user
			selectedCropImages = request.POST.getlist('miasCropImages')
			count = 0
			#This statement returns the data for the selected images for cropping
			for selectedCropImage in selectedCropImages:
				#responseCrop gets the data for the selectedImage from the google cloud storage for cropping
				responseCrop = requests.get(selectedCropImage.split('+')[1])
				#CropImage contains the selected image data in base64 format
				CropImage = base64.b64encode(BytesIO(responseCrop.content).getvalue()).decode()
				#imageName creates the name for the cropped image
				imageName = 'segment/ad/' + 'cropped_' + selectedCropImage.split('+')[0] 
				totalSelectedImages.append({'imageName' : imageName, 'imageData' : CropImage})
				count += 1
			#context contains the data to be passed to the HTML page for the post request
			context = {
				'loggedIn' : True,
				'count' : count,
				'operation' : 'Crop',
				'objects': objects,
				'selectedImages' : totalSelectedImages,
				'selectedBucket' :  selectedCropImage.split('+')[2],
			}		
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'imageCropping.html', context)
		if request.POST['submit'] == 'Save':
			'''
			This block saves the cropped images in the respective bucket
			'''
			miasImagesStorage = gStorage.Client()
			#miasBucket contains the bucket selected by the user
			miasBucket = miasImagesStorage.get_bucket(request.POST['selectedBucket'])
			#totalCroppedImage contains the total number of images cropped by the user
			totalCroppedImage = int(request.POST['totalCount'])
			#This statement saves the cropped images in the respective folder
			for croppedImages in range(totalCroppedImage):
				try:
					#imageName contains the name of the cropped image
					imageName = request.POST['imageNameHidden_' + str(croppedImages)]
					#This statement saves the cropped image in the ad folder in the bucket
					if 'segment/ad' in imageName:
						#croppedImageData contains the data for the cropped image
						croppedImageData = request.POST['imageDataHidden_' + str(croppedImages)]
						#b64CroppedImageData contains the base64 data for the cropped image
						b64CroppedImageData = croppedImageData[22: ]
						#blob creates an object for the cropped image in the google cloud storage bucket
						blob = miasBucket.blob(imageName)
						#This statement uploads the base64 image data for the cropped image to the created object in the google cloud 
						#storage bucket
						blob.upload_from_string(base64.b64decode(b64CroppedImageData), ('image/' + imageName.split('.')[1]))
					else:
						#This statement saves the cropped image in the ad folder in the bucket
						#croppedImageData contains the data for the cropped image
						croppedImageData = request.POST['imageDataHidden_' + str(croppedImages)]
						#b64CroppedImageData contains the base64 data for the cropped image
						b64CroppedImageData = croppedImageData[22: ]
						#blob creates an object for the cropped image in the google cloud storage bucket
						blob = miasBucket.blob(imageName)
						#This statement uploads the base64 image data for the cropped image to the created object in the google cloud 
						#storage bucket
						blob.upload_from_string(base64.b64decode(b64CroppedImageData), ('image/' + imageName.split('.')[1]))
				except:
			 		pass
			#context contains the data to be passed to the HTML page for the post request
			context = { 
				'loggedIn' : True,
				'operation' : 'Save',
				'objects': objects,
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'imageCropping.html', context)

