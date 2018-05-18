"""
Process the request and gives back the corresponding response for /workflow url
Author: Jeonkyu Lee, Murali krishnan and Umang Patel
Last Tested: 6/12/2017 by Murali Krishnan
Verified with: Python 3.6, Django 1.11
"""
from django.shortcuts import render, redirect
from django.conf import settings
from google.cloud import storage
from django.http import HttpResponseRedirect
from google.cloud import vision
from PIL import Image, ImageDraw
import numpy as np
import cv2
import time
import json
import base64
import requests
from io import BytesIO, StringIO
import threading
import csv

#google cloud vision api key for authentication
googleapikey = 'https://vision.googleapis.com/v1/images:annotate?key=AIzaSyDQ6OmhEqEKvbIiHmjOz_ZIZW4ZTAwdmKA'

#selectedBucket stores the bucket selected by the user
selectedBucket = None

###########################################################################
#  Def Name     : workflowHome
#  Input        : request
#  Output       : response(a html page along with the data processed for each request which is a context)
#  Purpose      : To give response to each request for the url '/workflow'
#  Author       : Jeonkyu Lee, Murali Krishnan and Umang Patel
#  Last Modified: 06/12/2017 by Murali Krishnan
############################################################################
def workflowHome(request):
	#global selectedBucket
	if request.method == 'GET':
		'''
		This block returns the response for the get request
		'''
		try:
			#loggedInUser gets the email of the logged in user
			loggedInUser = request.session['uEmail']
		except:
			#This statement redirects the user if he/she has not logged in
			return redirect('/welcome')
		#context contains the data to be passed to the HTML page for the get request
		context = {
			'loggedIn' : True,
			'operationStep' : 'Workflow',
			'buckets' : None,
		}
		#This statement returns the response as a HTML page along with the data to be displayed in it
		return render(request, 'workflow.html', context)
	else:
		'''
		This block returns the response for the post request
		'''
		if request.POST['submit'] == 'Start Workflow':
			'''
			This block retrieves the number of available buckets in the google cloud storage
			'''
			miasClient = storage.Client()
			#availableBuckets contains the list of all buckets available in the google cloud storage
			availableBuckets = miasClient.list_buckets()
			#resultBuckets contains the list of buckets that start with datacore in its name
			resultBuckets = []
			#This statement filter the buckets based on the name which starts with datacore
			for bucket in availableBuckets:
				if bucket.name.startswith('datacore'):
					resultBuckets.append(bucket)
			#context contains the data to be passed to the HTML page for the post request
			context = {
				'loggedIn': True,
				'operationStep' : 'Selection',
				'buckets': resultBuckets,
			}			
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'workflow.html', context)
		elif request.POST['submit'] == 'Step 2: Segmentation':
			'''
			This block retrieves number of files in the selected bucket
			'''
			miasImagesStorage = storage.Client()
			#miasBucket stores the bucket selected by the user
			miasBucket = miasImagesStorage.get_bucket(request.POST['bucket'])
			selectedBucket = miasBucket
			#This statement gets the list of all the images in miasBucket
			images = miasBucket.list_blobs()
			#filteredImages contains the list of all images filtered based on the name
			filteredImages = []
			segmentedImages = []
			#This statement filters the images in the selected bucket based on the name
			for image in images:
				if 'segment/' in image.name:
					pass
				else:
					filteredImages.append({'bucket': request.POST['bucket'],'url': image.public_url, 'name' : image.name})
			#context contains the data to be passed to the HTML page for the post request
			context = {
				'loggedIn': True,
				'operationStep': 'Classify',
				'miasimages': filteredImages,
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'workflow.html', context)
		elif request.POST['submit'] == 'Step 3: Classification':
			'''
			This block classifies the image(advertisement or non-advertisement)
			'''
			#selectedImages gets the list of images selected by the user
			selectedImages = request.POST.getlist('miasimages')
			#threads contains the number of threads created based on the list of selected images
			threads = []
			#This statement gives the number of active threads
			initThreadsCnt = threading.active_count()
			#category contains the category selected by the user for image classification
			category = request.POST['category']
			#This statement prints the total active threads
			print("Initial Thread cnt => " + str(initThreadsCnt))
			#This statement creates and starts the thread that does the image classification
			miasImagesStorage = storage.Client()
			selectedBucket = miasImagesStorage.get_bucket(selectedImages[0].split('+')[2])
			sensitivity_type = request.POST['Sensitivity']
			# sensitivity_point = int(request.POST['sPoint'])
			for index, image in enumerate(selectedImages):
				t = threading.Thread(target=onClassification, args=(image, index, category))
				threads.append(t)
				t.start()
				print("Thread " + str(index) + " started")
			#cnt is the counter for calculating the time for the process
			cnt = 0
			print("After Thread cnt => " + str(threading.active_count()))
			while (initThreadsCnt != threading.active_count()):
				cnt += 1
				print("Time -> " + str(cnt) + "    Current Thread cnt => " + str(threading.active_count()))
				time.sleep(1)
				if cnt > 20:
					break
			#totalImages contains the list of all the images in the selected bucket
			totalImages = selectedBucket.list_blobs()
			#These statements contain the list of all general and automotive ad and non ad images
			adSegmentedImages = []
			nonAdSegmentedImages = []
			autoAdSegmentedImages = []
			autoNonAdSegmentedImages = []
			totalSegmentedImages = []
			#This statement gets the general and automotive ad and non ad images
			if category == 'General':
				for individualImage in totalImages:
					if 'segment/ad' in individualImage.name:
						adSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
					elif 'segment/nonad' in individualImage.name:
						nonAdSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
					elif 'segment/autoad' in individualImage.name:
						autoAdSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
					elif 'segment/autononad' in individualImage.name:
						autoNonAdSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				totalSegmentedImages.append({'segmentType': 'ad', 'adSegmentedImages': adSegmentedImages})
				totalSegmentedImages.append({'segmentType': 'nonad','nonAdSegmentedImages': nonAdSegmentedImages})
				totalSegmentedImages.append({'segmentType': 'autoad', 'autoAdSegmentedImages': autoAdSegmentedImages})
				totalSegmentedImages.append({'segmentType': 'autononad','autoNonAdSegmentedImages': autoNonAdSegmentedImages})
			elif category == 'Automotive':
				for individualImage in totalImages:
					if 'segment/ad' in individualImage.name:
						adSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
					elif 'segment/nonad' in individualImage.name:
						nonAdSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
					elif 'segment/autoad' in individualImage.name:
						autoAdSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
					elif 'segment/autononad' in individualImage.name:
						autoNonAdSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				totalSegmentedImages.append({'segmentType': 'ad', 'adSegmentedImages': adSegmentedImages})
				totalSegmentedImages.append({'segmentType': 'nonad','nonAdSegmentedImages': nonAdSegmentedImages})
				totalSegmentedImages.append({'segmentType': 'autoad', 'autoAdSegmentedImages': autoAdSegmentedImages})
				totalSegmentedImages.append({'segmentType': 'autononad','autoNonAdSegmentedImages': autoNonAdSegmentedImages})
			#context contains the data to be passed to the HTML page for the post request
			context = {
				'bucket' : selectedBucket.name,
				'loggedIn': True,
				'operationStep' : 'ClassifiedImages',
				'totalSegmentedImages' : totalSegmentedImages,
				'threadCount' : str(threading.active_count()),
				'category' : category,
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'workflow.html', context)
		elif request.POST['submit'] == 'Step 4: QA':
			'''
			This block does the image cropping
			'''
			totalNonAdImages = []
			#selectedImagesWf contains the list of all selected images for cropping
			selectedImagesWf = request.POST.getlist('miasCropImages')
			#category contains the category selected by the user
			category = request.POST['selectedCategory']
			bucket = None
			count = 0
			if category == 'General':
				for imageWf in selectedImagesWf:
					count += 1
					bucket = imageWf.split('+')[0]
					responseCrop = requests.get(imageWf.split('+')[2])
					cropImage = base64.b64encode(BytesIO(responseCrop.content).getvalue()).decode()
					selectedImageNameWf = imageWf.split('+')[1]
					if 'segment/ad' in selectedImageNameWf or 'segment/nonad' in selectedImageNameWf:
						croppedImageName = selectedImageNameWf.split('/')[0] + '/ad/' + 'cropped_' + selectedImageNameWf.split('/')[2]
					else:
						croppedImageName = selectedImageNameWf.split('/')[0] + '/autoad/' + 'cropped_' + selectedImageNameWf.split('/')[2]
					totalNonAdImages.append({'imageName': croppedImageName, 'imageData': cropImage})
			elif category == 'Automotive':
				for imageWf in selectedImagesWf:
					count += 1
					bucket = imageWf.split('+')[0]
					responseCrop = requests.get(imageWf.split('+')[2])
					cropImage = base64.b64encode(BytesIO(responseCrop.content).getvalue()).decode()
					selectedImageNameWf = imageWf.split('+')[1]
					if 'segment/ad' in selectedImageNameWf or 'segment/nonad' in selectedImageNameWf:
						croppedImageName = selectedImageNameWf.split('/')[0] + '/ad/' + 'cropped_' + selectedImageNameWf.split('/')[2] 
					else:
						croppedImageName = selectedImageNameWf.split('/')[0] + '/autoad/' + 'cropped_' + selectedImageNameWf.split('/')[2]
					totalNonAdImages.append({'imageName': croppedImageName, 'imageData': cropImage})
			#context contains the data to be passed to the HTML page for the post request
			context = {
				'count' : count,
				'loggedIn': True,
				'operationStep': 'CropImage',
				'totalNonAdImages': totalNonAdImages,
				'bucket': bucket,
				'category' : category,
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'workflow.html', context)
		elif request.POST['submit'] == 'Automatic Annotation':
			'''
			This block performs the automatic annotations for the selected images
			'''
			#features contains the annotation features to be performed on the selected images
			features = '3:10 4:10 5:10'
			#selectedImages contains the list of all the selected images by the user for automatic annotation
			selectedImages = request.POST.getlist('miasCropImages')
			bucket = None
			miasImagesStorage = storage.Client()
			#result contains the result from automatic annotation
			result = []
			#This block performs the automatic annotation for the selected images
			for image in selectedImages:
				selectedBucket = miasImagesStorage.get_bucket(image.split('+')[0])
				resultDictionary = {'imageUrl': '', 'fileName' : '', 'mediaType' : '', 'advertise' : None, 'logo' : '', 'logoPercent' : '', 'headLine' : '', 'text' : ''}
				resultLabelDictionary = []
				resultDictionary['imageUrl'] = image.split('+')[2]
				response = requests.get(image.split('+')[2])
				selectedImage = base64.b64encode(BytesIO(response.content).getvalue()).decode()
				__resp = __generate_json(selectedImage, features)
				resultDictionary['fileName'] = image.split('+')[1].split('/')[2]
				resultDictionary['mediaType'] = 'Image'
				resultDictionary['headLine'] = 'N/A'
				if __resp == None:
					resultDictionary['text'] = 'No Text in the image'
					resultDictionary['advertise'] = None
					resultDictionary['logo'] = 'No logo in the image'
					resultDictionary['logoPercent'] = '0'
					result.append(resultDictionary)
				else:
					if 'textAnnotations' in __resp:
						for index, ttext in enumerate(__resp['textAnnotations'], start = 0):   # Python indexes start at zero
							if index == 0:
								resultDictionary['text'] = str(ttext['description'])
					else:
						resultDictionary['text'] = 'No Text in the image'
					if 'labelAnnotations' in __resp:
						for index, tlabel in enumerate(__resp['labelAnnotations'], start = 0):
							resultLabelDictionary.append({'labelDescription' : str(tlabel['description']), 'labelPercent' : str(round(tlabel['score'] * 100))})		
						resultDictionary['advertise'] = resultLabelDictionary
					else:
						resultDictionary['advertise'] = 'No label in the image'
					if 'logoAnnotations' in __resp:
						for index, tlogo in enumerate(__resp['logoAnnotations'], start = 0):
							resultDictionary['logo'] = tlogo['description']
							resultDictionary['logoPercent'] = str(round(tlogo['score'] * 100))
					else:
						resultDictionary['logo'] = 'No logo in the image'
						resultDictionary['logoPercent'] = '0'	
					result.append(resultDictionary)
			#context contains the data to be passed to the HTML page for the post request
			context = {
				'loggedIn': True,
				'operationStep' : 'Automatic Annotation',
				'result' : result,
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'workflow.html', context)
		elif request.POST['submit'] == 'List Segments':
			'''
			This block displays all the images after the classification process
			'''
			#totalImages contains the list of all images from the selected bucket
			miasImagesStorage = storage.Client()
			selectedBucket = miasImagesStorage.get_bucket(request.POST['selectedBucket'])
			totalImages = selectedBucket.list_blobs()
			#category contains the category selected by the user
			category = request.POST['selectedCategory']
			#adSegmentedImages contains the list of all the general category advertisement images after classification
			adSegmentedImages = []
			#nonAdSegmentedImages contains the list of all the general category non advertisement images after classification
			nonAdSegmentedImages = []
			#autoAdSegmentedImages contains the list of all the automotive category advertisement images after classification
			autoAdSegmentedImages = []
			#autoNonAdSegmentedImages contains the list of all the automotive category non advertisement images after classification
			autoNonAdSegmentedImages = []
			#totalSegmentedImages contains the list of all the images after classification
			totalSegmentedImages = []
			#This block gets the images and stores it in the corresponding categories
			for individualImage in totalImages:
				if 'segment/ad' in individualImage.name:
					adSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				elif 'segment/nonad' in individualImage.name:
					nonAdSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				elif 'segment/autoad' in individualImage.name:
					autoAdSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				elif 'segment/autononad' in individualImage.name:
					autoNonAdSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
			totalSegmentedImages.append({'segmentType': 'ad', 'adSegmentedImages': adSegmentedImages})
			totalSegmentedImages.append({'segmentType': 'nonad', 'nonAdSegmentedImages': nonAdSegmentedImages})
			totalSegmentedImages.append({'segmentType': 'autoad', 'autoAdSegmentedImages': autoAdSegmentedImages})
			totalSegmentedImages.append({'segmentType': 'autononad','autoNonAdSegmentedImages': autoNonAdSegmentedImages})
			#context contains the data to be passed to the HTML page for the post request
			context = {
				'bucket': selectedBucket.name,
				'loggedIn': True,
				'operationStep': 'ClassifiedImages',
				'totalSegmentedImages': totalSegmentedImages,
				'category' : category,
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'workflow.html', context)
		elif request.POST['submit'] == 'Save':
			miasImagesStorage = storage.Client()
			miasBucket = miasImagesStorage.get_bucket(request.POST['selectedBucket'])
			totalCroppedImage = int(request.POST['totalCount'])
			category = request.POST['selectedCategory']
			for croppedImages in range(totalCroppedImage):
				try:
					imageName = request.POST['imageNameHidden_' + str(croppedImages)]
					if 'segment/ad' in imageName:
						croppedImageData = request.POST['imageDataHidden_' + str(croppedImages)]
						b64CroppedImageData = croppedImageData[22: ]
						blob = miasBucket.blob(imageName)
						blob.upload_from_string(base64.b64decode(b64CroppedImageData), ('image/' + imageName.split('.')[2]))
					elif 'segment/nonad' in imageName:
						croppedImageData = request.POST['imageDataHidden_' + str(croppedImages)]
						b64CroppedImageData = croppedImageData[22: ]
						blob = miasBucket.blob(imageName)
						blob.upload_from_string(base64.b64decode(b64CroppedImageData), ('image/' + imageName.split('.')[2]))
					elif 'segment/autoad' in imageName:
						croppedImageData = request.POST['imageDataHidden_' + str(croppedImages)]
						b64CroppedImageData = croppedImageData[22: ]
						blob = miasBucket.blob(imageName)
						blob.upload_from_string(base64.b64decode(b64CroppedImageData), ('image/' + imageName.split('.')[2]))
					elif 'segment/autononad' in imageName:
						croppedImageData = request.POST['imageDataHidden_' + str(croppedImages)]
						b64CroppedImageData = croppedImageData[22: ]
						blob = miasBucket.blob(imageName)
						blob.upload_from_string(base64.b64decode(b64CroppedImageData), ('image/' + imageName.split('.')[2]))
				except:
					pass
			totalImages = miasBucket.list_blobs()	
			adSegmentedImages = []
			nonAdSegmentedImages = []
			autoAdSegmentedImages = []
			autoNonAdSegmentedImages = []
			totalSegmentedImages = []
			for individualImage in totalImages:
				if 'segment/ad' in individualImage.name:
					adSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				elif 'segment/nonad' in individualImage.name:
					nonAdSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				elif 'segment/autoad' in individualImage.name:
					autoAdSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				elif 'segment/autononad' in individualImage.name:
					autoNonAdSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
			totalSegmentedImages.append({'segmentType': 'ad', 'adSegmentedImages': adSegmentedImages})
			totalSegmentedImages.append({'segmentType': 'nonad','nonAdSegmentedImages': nonAdSegmentedImages})
			totalSegmentedImages.append({'segmentType': 'autoad', 'autoAdSegmentedImages': autoAdSegmentedImages})
			totalSegmentedImages.append({'segmentType': 'autononad','autoNonAdSegmentedImages': autoNonAdSegmentedImages})
			#context contains the data to be passed to the HTML page for the post request
			context = { 
				'loggedIn' : True,
				'operationStep' : 'Save',
				'operationSave' : True,
				'totalSegmentedImages' : totalSegmentedImages,
				'bucket' : request.POST['selectedBucket'],
				'category' : category,
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'workflow.html', context)
		elif request.POST['submit'] == 'Move Segments':
			'''
			 This block moves the images from ad folder to nonad folder and vice versa
			'''
			#selectedImages contains the list of all selected images by the user
			selectedImages = request.POST.getlist('miasCropImages')
			miasImagesStorage = storage.Client()
			#miasBucktet contains the bucket selected by the user
			miasBucket = None
			#category contains the category selected by the user
			category = request.POST['selectedCategory']
			#This statement moves the selected images from ad to nonad and vice versa
			for selectedImage in selectedImages:
				selectedBucket = miasImagesStorage.get_bucket(selectedImage.split('+')[0])
				miasBucket = selectedBucket
				selectedImageName = selectedImage.split('+')[1]
				if 'segment/ad' in selectedImageName:
					response = requests.get(selectedImage.split('+')[2])
					imgBytes = BytesIO(response.content).getvalue()
					oldBlob = miasBucket.blob(selectedImageName)
					oldBlob.delete()
					movedBlob = miasBucket.blob('segment/nonad/' + selectedImageName.split('/')[2])
					movedBlob.upload_from_string(imgBytes, ('image/' + selectedImageName.split('.')[2]))
				elif 'segment/nonad' in selectedImageName:
					response = requests.get(selectedImage.split('+')[2])
					imgBytes = BytesIO(response.content).getvalue()
					oldBlob = miasBucket.blob(selectedImageName)
					oldBlob.delete()
					movedBlob = miasBucket.blob('segment/ad/' + selectedImageName.split('/')[2])
					movedBlob.upload_from_string(imgBytes, ('image/' + selectedImageName.split('.')[2]))
				elif 'segment/autoad' in selectedImageName:
					response = requests.get(selectedImage.split('+')[2])
					imgBytes = BytesIO(response.content).getvalue()
					oldBlob = miasBucket.blob(selectedImageName)
					oldBlob.delete()
					movedBlob = miasBucket.blob('segment/autononad/' + selectedImageName.split('/')[2])
					movedBlob.upload_from_string(imgBytes, ('image/' + selectedImageName.split('.')[2]))
				elif 'segment/autononad' in selectedImageName:
					response = requests.get(selectedImage.split('+')[2])
					imgBytes = BytesIO(response.content).getvalue()
					oldBlob = miasBucket.blob(selectedImageName)
					oldBlob.delete()
					movedBlob = miasBucket.blob('segment/autoad/' + selectedImageName.split('/')[2])
					movedBlob.upload_from_string(imgBytes, ('image/' + selectedImageName.split('.')[2]))
			#totalImages contains the list of all the images from the bucket selected by the user
			totalImages = miasBucket.list_blobs()
			#adSegmentedImages contains the list of all the general category advertisement images after move operation
			adSegmentedImages = []
			#nonAdSegmentedImages contains the list of all the general category non advertisement images after move operation
			nonAdSegmentedImages = []
			#autoAdSegmentedImages contains the list of all the automotive category non advertisement images after move operation
			autoAdSegmentedImages = []
			#autoNonAdSegmentedImages contains the list of all the automotive category non advertisement images after move operation
			autoNonAdSegmentedImages = []
			#totalSegmentedImages contains the list of all the images after move operation
			totalSegmentedImages = []
			#This block gets the images and stores it in the corresponding categories
			for individualImage in totalImages:
				if 'segment/ad' in individualImage.name:
					adSegmentedImages.append(
						{'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				elif 'segment/nonad' in individualImage.name:
					nonAdSegmentedImages.append(
						{'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				elif 'segment/autoad' in individualImage.name:
					autoAdSegmentedImages.append(
						{'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				elif 'segment/autononad' in individualImage.name:
					autoNonAdSegmentedImages.append(
						{'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
			totalSegmentedImages.append({'segmentType': 'ad', 'adSegmentedImages': adSegmentedImages})
			totalSegmentedImages.append({'segmentType': 'nonad', 'nonAdSegmentedImages': nonAdSegmentedImages})
			totalSegmentedImages.append({'segmentType': 'autoad', 'autoAdSegmentedImages': autoAdSegmentedImages})
			totalSegmentedImages.append({'segmentType': 'autononad', 'autoNonAdSegmentedImages': autoNonAdSegmentedImages})
			#context contains the data to be passed to the HTML page for the post request
			context = {
				'bucket': miasBucket.name,
				'loggedIn': True,
				'operationStep': 'ClassifiedImages',
				'totalSegmentedImages': totalSegmentedImages,
				'category' : category,
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'workflow.html', context)
		elif request.POST['submit'] == 'Delete':
			'''
			 This block deletes the images from the corresponding folder
			'''
			#selectedImages contains the list of all selected images by the user
			selectedImages = request.POST.getlist('miasCropImages')
			miasImagesStorage = storage.Client()
			#miasBucktet contains the bucket selected by the user
			miasBucket = None
			#category contains the category selected by the user
			category = request.POST['selectedCategory']
			#This statement deletes the selected images from the respective folders
			for selectedImage in selectedImages:
				selectedBucket = miasImagesStorage.get_bucket(selectedImage.split('+')[0])
				miasBucket = selectedBucket
				selectedImageName = selectedImage.split('+')[1]
				response = requests.get(selectedImage.split('+')[2])
				imgBytes = BytesIO(response.content).getvalue()
				blobToBeDeleted = miasBucket.blob(selectedImageName)
				blobToBeDeleted.delete()
			#totalImages contains the list of all the images from the bucket selected by the user
			totalImages = miasBucket.list_blobs()
			#adSegmentedImages contains the list of all the general category advertisement images after move operation
			adSegmentedImages = []
			#nonAdSegmentedImages contains the list of all the general category non advertisement images after move operation
			nonAdSegmentedImages = []
			#autoAdSegmentedImages contains the list of all the automotive category non advertisement images after move operation
			autoAdSegmentedImages = []
			#autoNonAdSegmentedImages contains the list of all the automotive category non advertisement images after move operation
			autoNonAdSegmentedImages = []
			#totalSegmentedImages contains the list of all the images after move operation
			totalSegmentedImages = []
			#This block gets the images and stores it in the corresponding categories
			for individualImage in totalImages:
				if 'segment/ad' in individualImage.name:
					adSegmentedImages.append(
						{'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				elif 'segment/nonad' in individualImage.name:
					nonAdSegmentedImages.append(
						{'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				elif 'segment/autoad' in individualImage.name:
					autoAdSegmentedImages.append(
						{'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				elif 'segment/autononad' in individualImage.name:
					autoNonAdSegmentedImages.append(
						{'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
			totalSegmentedImages.append({'segmentType': 'ad', 'adSegmentedImages': adSegmentedImages})
			totalSegmentedImages.append({'segmentType': 'nonad', 'nonAdSegmentedImages': nonAdSegmentedImages})
			totalSegmentedImages.append({'segmentType': 'autoad', 'autoAdSegmentedImages': autoAdSegmentedImages})
			totalSegmentedImages.append({'segmentType': 'autononad', 'autoNonAdSegmentedImages': autoNonAdSegmentedImages})
			#context contains the data to be passed to the HTML page for the post request
			context = {
				'bucket': miasBucket.name,
				'loggedIn': True,
				'operationStep': 'ClassifiedImages',
				'totalSegmentedImages': totalSegmentedImages,
				'category' : category,
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'workflow.html', context)
		else:
			#totalImages contains the list of all the images from the bucket selected by the user
			selectedBucket = miasImagesStorage.get_bucket(request.POST['selectedBucket'])
			totalImages = selectedBucket.list_blobs()
			adSegmentedImages = []
			nonAdSegmentedImages = []
			autoAdSegmentedImages = []
			autoNonAdSegmentedImages = []
			totalSegmentedImages = []
			for individualImage in totalImages:
				if 'segment/ad' in individualImage.name:
					adSegmentedImages.append(
						{'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				elif 'segment/nonad' in individualImage.name:
					nonAdSegmentedImages.append(
						{'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				elif 'segment/autoad' in individualImage.name:
					autoAdSegmentedImages.append(
						{'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				elif 'segment/autononad' in individualImage.name:
					autoNonAdSegmentedImages.append(
						{'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
			totalSegmentedImages.append({'segmentType': 'ad', 'adSegmentedImages': adSegmentedImages})
			totalSegmentedImages.append({'segmentType': 'nonad', 'nonAdSegmentedImages': nonAdSegmentedImages})
			totalSegmentedImages.append({'segmentType': 'autoad', 'autoAdSegmentedImages': autoAdSegmentedImages})
			totalSegmentedImages.append({'segmentType': 'autononad', 'autoNonAdSegmentedImages': autoNonAdSegmentedImages})
			#context contains the data to be passed to the HTML page for the post request
			context = {
				'bucket': selectedBucket.name,
				'loggedIn': True,
				'operationStep': 'ClassifiedImages',
				'totalSegmentedImages': totalSegmentedImages,
				'threadCount' : str(threading.active_count()),
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'workflow.html', context)
			
def detection(inputImage, feature, category):
	features = feature
	#selectedImage = base64.b64encode(BytesIO(inputImage.content).getvalue()).decode()
	selectedImage = inputImage.decode()
	__resp = __generate_json(selectedImage, features)
	#print(str(__resp))
	advertisementImage = False
	result = []
	if category == 'Automotive':
		carBrands = ['Alfa Romeo', 'Aston Martin', 'Audi', 'Bentley', 'Benz', 'BMW', 'Bugatti', 'Cadillac', 'Chevrolet', 'Chrysler',
	             'Citroën', 'Corvette', 'DAF', 'Dacia', 'Daewoo', 'Daihatsu', 'Datsun', 'De Lorean', 'Dino', 'Dodge', 'Farboud', 
				 'Ferrari', 'Fiat', 'Ford', 'Honda', 'Hummer', 'Hyundai', 'Jaguar', 'Jeep', 'KIA', 'Koenigsegg', 'Lada',
				 'Lamborghini', 'Lancia', 'Land Rover', 'Lexus', 'Ligier', 'Lincoln', 'Lotus', 'Martini', 'Maserati', 'Maybach',
				 'Mazda', 'McLaren', 'Mercedes-Benz', 'Mini Mitsubishi', 'Nissan', 'Noble', 'Opel', 'Peugeot', 'Pontiac', 'Porsche',
				 'Renault', 'Rolls-Royce', 'Saab', 'Seat', 'Skoda', 'Smart', 'Spyker', 'Subaru', 'Suzuki', 'Toyota', 'Vauxhall',
				 'Volkswagen', 'Volvo']
	
	if category == 'General':
		if __resp != None:
			if 'labelAnnotations' in __resp:
				for index, tlabel in enumerate(__resp['labelAnnotations'], start = 0):
					if (str(tlabel['description']) == 'advertising') or (str(tlabel['description']) == 'brand'):
						advertisementImage = True
			if 'logoAnnotations' in __resp:
				for index, tlogo in enumerate(__resp['logoAnnotations'], start = 0):
					if (str(tlogo['description']) != None):
						advertisementImage = True
	elif category == 'Automotive':
		if __resp != None:
			if 'labelAnnotations' in __resp: # if there exists any Car related words (e.g., "car", "vehicle", "automotive" ...) in [ Label Detection: ]
				for index, tlabel in enumerate(__resp['labelAnnotations'], start = 0):
					#print(tlabel)
					if ('automobile' in str(tlabel['description']).lower()) or \
						('automotive' in str(tlabel['description']).lower())  or \
						('car' == str(tlabel['description']).lower()) or \
						('vehicle' in str(tlabel['description']).lower()):
						#advertisementImage = True
						print("Label automobile")
						#print(str(tlabel['description']))
						if 'logoAnnotations' in __resp: # If there exist any "Car_Brand_Name" in either [ Logo detection ] OR [ Text detection ]
							for index1, tlogo in enumerate(__resp['logoAnnotations'], start=0):
								if (str(tlogo['description']) != None):
									for carBrand in carBrands:
										if (carBrand in str(tlogo['description'])):
											advertisementImage = True
											print("Logo Automobile")
						if 'textAnnotations' in __resp:
							for index2, ttext in enumerate(__resp['textAnnotations'], start = 0):
								if ('automotive' in str(ttext['description']).lower()) or \
									('automobile' in str(ttext['description']).lower()) or \
									('car' in str(ttext['description']).lower()) or \
									('vehicle' in str(ttext['description']).lower()):
									advertisementImage = True
									print("Text Automobile")
								else:
									for carBrand in carBrands:
										if (str(carBrand).lower() in str(ttext['description']).lower()):
											advertisementImage = True
											print("Text Logo Automobile")
						if 'labelAnnotations' in __resp:									 # If there exists "advertising" or "brand" in [ Label detection ]
							for index3, tlabel3 in enumerate(__resp['labelAnnotations'], start = 0):
								if (str(tlabel3['description']) == 'advertising') or (str(tlabel3['description']) == 'brand'):
									advertisementImage = True
									print("Label Advertisement")
	return advertisementImage
	
def onClassification(image, idx, category):
	bucket = image.split('+')[2]
	miasImagesStorage = storage.Client()
	miasBucket = miasImagesStorage.get_bucket(bucket)
	selectedBucketThread = miasBucket
	response = requests.get(image.split('+')[0])
	selectedImage = base64.b64encode(BytesIO(response.content).getvalue())
	img = np.asarray(bytearray(BytesIO(response.content).getvalue()), dtype='uint8')
	convertedImage = cv2.imdecode(img, cv2.IMREAD_COLOR)
	gray = cv2.cvtColor(convertedImage, cv2.COLOR_BGR2GRAY)
	h, w = convertedImage.shape[:2]
	tHreshold = 200  # 235
	minThreshold = 40  # new
	pixMaxThreshold = 15
	topbottomMargin = 10
	leftrightMargin = 5  # 2
	colTemp = 0
	rowTemp = 0
	conTinueYN = True
	minRegionHight = 25
	detectColList = []
	detectRegionOfAD = []
	# colMean =  np.mean(gray,axis=0)
	colStd = np.std(gray, axis=0)
	imgStd = np.std(convertedImage, axis=2)
	for col in range(0, w):
		cnt = 0
		cntB = 0
		if (colStd[col] <= 10):
			for row in range(0, h):
				if (gray[row, col] >= tHreshold) and (imgStd[row, col] <= pixMaxThreshold):
					cnt = cnt + 1
				if (gray[row, col] <= minThreshold) and (imgStd[row, col] <= pixMaxThreshold):
					cntB = cntB + 1
		if (col == w - 1):  ## Last column
			if (cnt >= h - topbottomMargin) or (cntB >= h - topbottomMargin):
				if (conTinueYN == False):
					detectColList.append(col)
				else:
					detectColList.append((colTemp + col) / 2)
			else:
				if (conTinueYN == True):
					detectColList.append((colTemp + col) / 2)
				else:
					detectColList.append(col)
		else:  ## in-between columns
			if (cnt >= h - topbottomMargin) or (cntB >= h - topbottomMargin):
				if (conTinueYN == False):
					colTemp = col
					conTinueYN = True
			else:
				if (conTinueYN == True):
					detectColList.append((colTemp + col) / 2)
					conTinueYN = False
	if len(detectColList) == 0:
		detectColList.append(0)
		detectColList.append(int(w - 1))
	elif len(detectColList) == 1:
		detectColList.append(int(w - 1))
	colNum = len(detectColList)
	conTinueYN = True
	for detectCol in range(0, colNum - 1):
		colX1 = detectColList[detectCol]
		colX2 = detectColList[detectCol + 1]
		rowTemp = 0

		for row in range(0, h):
			cnt = 0
			cntB = 0
			for col in range(int(colX1), int(colX2 + 1)):
				if (gray[row, col] >= tHreshold) and (imgStd[row, col] <= pixMaxThreshold):
					cnt = cnt + 1
				if (gray[row, col] <= minThreshold) and (imgStd[row, col] <= pixMaxThreshold):
					cntB = cntB + 1
			if (row == h - 1):  ## Last row
				if (conTinueYN == True):
					if (row - rowTemp) > minRegionHight:
						detectRegionOfAD.append([colX1, rowTemp, colX2, row])
					# cv2.rectangle(convertedImage, (int(colX1), int(rowTemp)), (int(colX2), int(row)), (0,255,0), 3)
			else:
				if (cnt >= (colX2 - colX1 + 1 - leftrightMargin) or (
							cntB >= (colX2 - colX1 + 1 - leftrightMargin))):  # White line
					if (conTinueYN == True):
						if (row - rowTemp) > minRegionHight:
							detectRegionOfAD.append([colX1, rowTemp, colX2, row])
						# cv2.rectangle(convertedImage, (int(colX1), int(rowTemp)), (int(colX2), int(row)), (0,255,0), 3)
						conTinueYN = False
				else:  # Contents
					if (conTinueYN == False):
						rowTemp = row
						conTinueYN = True
	im = Image.fromarray(cv2.cvtColor(convertedImage, cv2.COLOR_BGR2RGB))
	adSegments = 0
	nonAdSegments = 0
	#print("Selected Bucket is: " + selectedBucket.name)
	for detectReg in range(0, len(detectRegionOfAD)):
		output_img = im.crop(detectRegionOfAD[detectReg])
		inMemory = BytesIO()
		# output_img.save(inMemory, format = image.split('+')[1].split('.')[1])
		output_img.save(inMemory, format='png')
		inMemory.seek(0)
		imgBytes = inMemory.read()
		b64Image = base64.b64encode(imgBytes)
		adNonAd = detection(b64Image, '3:10 4:10 5:10', category)
		if category == 'General':
			if adNonAd:
				segmentedImageName = image.split('+')[1].split('.')[0] + '_segment_' + str(adSegments) + '_ad'
				adSegments += 1
				blob = selectedBucketThread.blob(
					'segment/ad/' + segmentedImageName + '_' + str(time.time()) + '.' + image.split('+')[1].split('.')[1])
				blob.upload_from_string(imgBytes, ('image/' + image.split('+')[1].split('.')[1]))
			else:
				segmentedImageName = image.split('+')[1].split('.')[0] + '_segment_' + str(nonAdSegments) + '_nonad'
				nonAdSegments += 1
				blob = selectedBucketThread.blob(
					'segment/nonad/' + segmentedImageName + '_' + str(time.time()) + '.' + image.split('+')[1].split('.')[
					1])
				blob.upload_from_string(imgBytes, ('image/' + image.split('+')[1].split('.')[1]))
		elif category == 'Automotive':
			if adNonAd:
				segmentedImageName = image.split('+')[1].split('.')[0] + '_segment_' + str(adSegments) + '_auto_ad'
				adSegments += 1
				blob = selectedBucketThread.blob(
					'segment/autoad/' + segmentedImageName + '_' + str(time.time()) + '.' + image.split('+')[1].split('.')[1])
				blob.upload_from_string(imgBytes, ('image/' + image.split('+')[1].split('.')[1]))
			else:
				segmentedImageName = image.split('+')[1].split('.')[0] + '_segment_' + str(nonAdSegments) + '_auto_nonad'
				nonAdSegments += 1
				blob = selectedBucketThread.blob(
					'segment/autononad/' + segmentedImageName + '_' + str(time.time()) + '.' + image.split('+')[1].split('.')[
					1])
				blob.upload_from_string(imgBytes, ('image/' + image.split('+')[1].split('.')[1]))

def __generate_json(img, feat):
	request_list = []
	content_json_obj = {
		#'content': base64.b64encode(img).decode('UTF-8')
		'content': img
    }
	features = feat
	feature_json_obj = []
	for word in features.split(' '):
		feature, max_results = word.split(':', 1)
		feature = int(feature)
		feature_json_obj.append({
			'type': DETECTION_TYPES[feature],
			'maxResults': int(max_results),
        })
		request_list.append({
			'features': feature_json_obj,
			'image': content_json_obj,
        })
	response = requests.post(url = googleapikey, 
		data = json.dumps({'requests': request_list}), 
		headers = {'Content-Type': 'application/json'})
	into = response.text
	if response.status_code != 200 or response.json().get('error'):
           resp = None
	else:
		for idx, resp in enumerate(response.json()['responses']):
			pass
	return resp
	
DETECTION_TYPES = [
    'TYPE_UNSPECIFIED',
    'FACE_DETECTION',
    'LANDMARK_DETECTION',
    'LOGO_DETECTION',
    'LABEL_DETECTION',
    'TEXT_DETECTION',
    'SAFE_SEARCH_DETECTION',
]

