"""
Process the request and gives back the corresponding response for /detection url
Author: Jeonkyu Lee, Murali krishnan and Umang Patel
Last Tested: 6/12/2017 by Murali Krishnan
Verified with: Python 3.6, Django 1.11
"""

from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.conf import settings
from MIASSTORAGE import storage
from datetime import datetime
from google.cloud import vision
from PIL import Image, ImageDraw
import json
import base64
import requests
from io import BytesIO, StringIO
import os

#google cloud vision api key for authentication
googleapikey = 'https://vision.googleapis.com/v1/images:annotate?key=AIzaSyDQ6OmhEqEKvbIiHmjOz_ZIZW4ZTAwdmKA'

###########################################################################
#  Def Name     : detectionHome
#  Input        : request
#  Output       : response(a html page along with the data processed for each request which is a context)
#  Purpose      : To give response to each request for the url '/detection'
#  Author       : Jeonkyu Lee, Murali Krishnan and Umang Patel
#  Last Modified: 06/12/2017 by Murali Krishnan
############################################################################
def detectionHome(request):
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
		#response contains the list of buckets corresponding to the cloud project ID
		response = storage.list_buckets(settings.CLOUD_PROJECT_ID)
		#objects contains only the list of buckets whose name starts with datacore
		objects = {}
		#This statement extracts the buckets whose name starts with datacore and its blobs
		for lstbct in response['items']:
			if lstbct['name'].startswith('datacore'):
				#blobs contain the list of objects(images) in each bucket
				total_blobs = []
				original_blobs = []
				segment_nonad_blobs = []
				segment_ad_blobs = []
				respobject = storage.list_objects(lstbct['name'])
				#This statement extracts the images in the root folder of each bucket
				for index, bct in enumerate(respobject):
					if 'segment/ad' in str(bct['name']):
						segment_ad_blobs.append({'bucketType': 'segmentAd', 'index': index, 'name': str(bct['name']),
									  'public_url': 'https://storage.googleapis.com/' + lstbct['name'] + '/' + str(bct['name']),
									  'timecreated': datetime.strptime(str(bct['timeCreated']), '%Y-%m-%dT%H:%M:%S.%fZ'),
									  'type': str(bct['contentType'])})
					elif 'segment/nonad/' in str(bct['name']):
						segment_nonad_blobs.append({'bucketType': 'segmentNonAd', 'index': index, 'name': str(bct['name']),
									  'public_url': 'https://storage.googleapis.com/' + lstbct['name'] + '/' + str(bct['name']),
									  'timecreated': datetime.strptime(str(bct['timeCreated']), '%Y-%m-%dT%H:%M:%S.%fZ'),
									  'type': str(bct['contentType'])})
					else:
						original_blobs.append({'bucketType': 'original', 'index': index, 'name': str(bct['name']),
									  'public_url': 'https://storage.googleapis.com/' + lstbct['name'] + '/' + str(bct['name']),
									  'timecreated': datetime.strptime(str(bct['timeCreated']), '%Y-%m-%dT%H:%M:%S.%fZ'),
									  'type': str(bct['contentType'])})
				total_blobs.append(original_blobs)
				total_blobs.append(segment_nonad_blobs)
				total_blobs.append(segment_ad_blobs)
				objects.update({lstbct['name']: total_blobs})
		#context contains the data to be passed to the HTML page for the get request
		context = {
			'loggedIn': True,
			'objects': objects,
		}
		#This statement returns the response as a HTML page along with the data to be displayed in it
		return render(request, 'detectionHome.html', context)
	else:
		'''
		This block returns the response for the post request
		'''
		if request.POST['submit'] == 'Image View':
			selectedImages = request.POST.getlist('miasimages')
			miasImagesStorage = storage.Client()
			miasBucket = miasImagesStorage.get_bucket(settings.CLOUD_STORAGE_BUCKET)
			images = miasBucket.list_blobs()
			filteredImages = []
			for image in images:
				if 'segment/' in image.name:
					pass
				else:
					filteredImages.append({'url': image.public_url, 'name': image.name})

			result = []
			for eachImage in selectedImages:
				fname = str(os.path.basename(eachImage))
				result.append({'imageUrl': eachImage, 'name': fname})
			#context contains the data to be passed to the HTML page for the post request
			context = {
				'loggedIn': True,
				'operation' : 'Image View',
				'miasimages': filteredImages,
				'result' : result,
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'detectionHome.html', context)
		elif request.POST['submit'] == 'Text Detection':
			'''
			This block performs the text detection for the selected images
			'''
			#features represent the process that needs to be done on the images
			features = '5:10'
			#selectedImages contain the list of images selected by the user
			selectedImages = request.POST.getlist('miasimages')
			#result contains the detected text in the image
			result = {}
			#This statement performs the text detection operation in the images
			for image in selectedImages:
				#response contains the image data from the google cloud storage bucket
				response = requests.get(image)
				#selectedImage contains the data of the image in base64 format
				selectedImage = base64.b64encode(BytesIO(response.content).getvalue()).decode()
				#__text contains the text detected in the image if any
				__text = __generate_json(selectedImage, features)
				if 'textAnnotations' in __text:
					for index, ttext in enumerate(__text['textAnnotations'], start = 0):
						if index == 0:
							result[image] = str(ttext['description'])
				else:
					result[image] = 'No text in the image'
			#context contains the data to be passed to the HTML page for the post request
			context = {
				'loggedIn': True,
				'operation' : 'Text Detection',
				'resultKeys' : result.keys(),
				'result' : result,
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'detectionresult.html', context)
		elif request.POST['submit'] == 'Logo Detection' :
			'''
			This block performs the logo detection for the selected images
			'''
			#features represent the process that needs to be done on the images
			features = '3:10'
			#selectedImages contain the list of images selected by the user
			selectedImages = request.POST.getlist('miasimages')
			#result contains the detected logo in the image
			result = []
			#This statement performs the logo detection operation in the images
			for image in selectedImages:
				#response contains the image data from the google cloud storage bucket
				response = requests.get(image)
				#selectedImage contains the data of the image in base64 format
				selectedImage = base64.b64encode(BytesIO(response.content).getvalue()).decode()
				#__logo contains the logo detected in the image if any
				__logo = __generate_json(selectedImage, features)
				if 'logoAnnotations' in __logo:
					for index, tlogo in enumerate(__logo['logoAnnotations'], start = 0):
						result.append({ 'imageUrl': image, 'logoDescription': str(tlogo['description']), 'percent': str(round(tlogo['score'] * 100)) })						
				else:
					result.append({ 'imageUrl': image, 'logoDescription': 'No Logo in the image', 'percent': '0' })
			#context contains the data to be passed to the HTML page for the post request
			context = {
				'loggedIn': True,
				'operation' : 'Logo Detection',
				'result' : result,
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'detectionresult.html', context)
		elif request.POST['submit'] == 'Text Display':
			'''
			This block performs the text detection and gets the location of the detected text in the selected images
			'''
			#features represent the process that needs to be done on the images
			features = '5:10'
			#selectedImages contain the list of images selected by the user
			selectedImages = request.POST.getlist('miasimages')
			#result contains the detected text location in the image
			result = []
			#This statement performs the text detection operation in the images
			for image in selectedImages:
				#response contains the image data from the google cloud storage bucket
				response = requests.get(image)
				#selectedImage contains the data of the image in base64 format
				selectedImage = base64.b64encode(BytesIO(response.content).getvalue()).decode()	
				#text contains the text detected in the image if any
				text = __generate_json(selectedImage, features)
				im = Image.open(BytesIO(response.content))	
				draw = ImageDraw.Draw(im)
				#This statement gets the detected text location in the image and draws a rectangular box around it
				if 'textAnnotations' in text:
					for index, ttext in enumerate(text['textAnnotations'], start=0):   
						if index != 0:
							boundpoly = ttext['boundingPoly']['vertices'][0]           
							x = boundpoly['x']
							y = boundpoly['y']           
							boundpolyvert = ttext['boundingPoly']['vertices'][1]
							xh = boundpolyvert['x']
							yh = boundpolyvert['y']         
							__boundpolyvert_2 = ttext['boundingPoly']['vertices'][2]          
							yh = __boundpolyvert_2['y']
							__boundpolyvert_2 = ttext['boundingPoly']['vertices'][3] 							
							cor = (x,y, xh,yh)
							for i in range(3):
								draw.rectangle(cor, outline="red")   
								cor = (cor[0]+1,cor[1]+1, cor[2]+1,cor[3]+1)
					inMemory = BytesIO()
					im.save(inMemory, format='jpeg')
					inMemory.seek(0)
					imgBytes = inMemory.read()
					b64Image = base64.b64encode(imgBytes)
					result.append({'originalImage' : image, 'modifiedImage' : b64Image})
				else:
					result.append({'originalImage' : image, 'modifiedImage' : '0'})
			#context contains the data to be passed to the HTML page for the post request
			context = {
				'loggedIn': True,
				'operation' : 'Text Display',
				'result': result,
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'detectionresult.html', context)
		elif request.POST['submit'] == 'Logo Display':
			'''
			This block performs the logo detection and gets the location of the detected logo in the selected images
			'''
			#features represent the process that needs to be done on the images
			features = '3:10'
			#selectedImages contain the list of images selected by the user
			selectedImages = request.POST.getlist('miasimages')
			#result contains the detected logo in the image
			result = []
			#This statement performs the logo detection operation in the images
			for image in selectedImages:
				#response contains the image data from the google cloud storage bucket
				response = requests.get(image)
				#selectedImage contains the data of the image in base64 format
				selectedImage = base64.b64encode(BytesIO(response.content).getvalue()).decode()
				#t contains the logo detected in the image if any
				t = __generate_json(selectedImage, features)
				#This statement gets the detected logo location in the image and draws a rectangular box around it
				if 'logoAnnotations' in t:
					t = t['logoAnnotations'][0]            
					boundpoly = t['boundingPoly']['vertices'][0]           
					x = boundpoly['x']
					y = boundpoly['y']           
					boundpolyvert = t['boundingPoly']['vertices'][1]
					xh = boundpolyvert['x']
					yh = boundpolyvert['y']         
					__boundpolyvert_2 = t['boundingPoly']['vertices'][2]          
					yh = __boundpolyvert_2['y']
					__boundpolyvert_2 = t['boundingPoly']['vertices'][3]	
					im = Image.open(BytesIO(response.content))	
					draw = ImageDraw.Draw(im)
					cor = (x,y, xh,yh)
					for i in range(5):
						draw.rectangle(cor, outline = 'red')   
						cor = (cor[0]+1, cor[1]+1, cor[2]+1, cor[3]+1)
					inMemory = BytesIO()
					im.save(inMemory, format='png')
					inMemory.seek(0)
					imgBytes = inMemory.read()
					b64Image = base64.b64encode(imgBytes)
					result.append({'originalImage' : image, 'modifiedImage' : b64Image})
				else:
					result.append({'originalImage' : image, 'modifiedImage' : '0'})
			#context contains the data to be passed to the HTML page for the post request
			context = {
				'loggedIn': True,
				'operation' : 'Logo Display',
				'result': result,
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'detectionresult.html', context)
		elif request.POST['submit'] == 'Label Detection':
			'''
			This block performs the label detection in the selected images
			'''
			#features represent the process that needs to be done on the images
			features = '4:10'
			#selectedImages contain the list of images selected by the user
			selectedImages = request.POST.getlist('miasimages')
			#result contains the detected label in the image
			result = []		
			#This statement performs the label detection operation in the images
			for image in selectedImages:
				#labelDetectionResult contains the list of detected labels in the image
				labelDetectionResult = []
				#response contains the image data from the google cloud storage bucket
				response = requests.get(image)
				#selectedImage contains the data of the image in base64 format
				selectedImage = base64.b64encode(BytesIO(response.content).getvalue()).decode()
				#__label contains the label detected in the image if any
				__label = __generate_json(selectedImage, features)
				#This statement extracts the label in the image
				if 'labelAnnotations' in __label:
					for index, tlabel in enumerate(__label['labelAnnotations'], start=0):
						labelDetectionResult.append({'labelDescription' : str(tlabel['description']), 'percent' : str(round(tlabel['score'] * 100))})
					result.append({'imageUrl' : image, 'labelDetectionResult' : labelDetectionResult })
				else:
					labelDetectionResult.append({'labelDescription' : 'No label in the image', 'percent' : '0'})
					result.append({ 'imageUrl': image, 'labelDetectionResult': labelDetectionResult })
			#context contains the data to be passed to the HTML page for the post request
			context = {
				'loggedIn': True,
				'operation' : 'Label Detection',
				'result' : result,
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'detectionresult.html', context)
		elif request.POST['submit'] == 'Automatic Annotation':	
			'''
			This block performs the text, logo and label detections in the selected images in a single request
			'''
			#features represent the process that needs to be done on the images
			features = '3:10 4:10 5:10'
			#selectedImages contain the list of images selected by the user
			selectedImages = request.POST.getlist('miasimages')
			#result contains the detected label in the image
			result = []			
			#This statement performs the text, label and logo detection operations in the images
			for image in selectedImages:
				resultDictionary = {'imageUrl': '', 'fileName' : '', 'mediaType' : '', 'advertise' : None, 'logo' : '', 'logoPercent' : '', 'headLine' : '', 'text' : ''}
				resultLabelDictionary = []
				resultDictionary['imageUrl'] = image
				response = requests.get(image)
				selectedImage = base64.b64encode(BytesIO(response.content).getvalue()).decode()
				__resp = __generate_json(selectedImage, features)
				resultDictionary['fileName'] = image.split('/')[4]
				resultDictionary['mediaType'] = 'Image'
				resultDictionary['headLine'] = 'N/A'
				#This statement extracts the detected text in the image if any
				if 'textAnnotations' in __resp:
					for index, ttext in enumerate(__resp['textAnnotations'], start = 0):   # Python indexes start at zero
						if index == 0:
							resultDictionary['text'] = str(ttext['description'])
				else:
					resultDictionary['text'] = 'No Text in the image'
				#This statement extracts the detected label in the image if any
				if 'labelAnnotations' in __resp:
					for index, tlabel in enumerate(__resp['labelAnnotations'], start = 0):
						resultLabelDictionary.append({'labelDescription' : str(tlabel['description']), 'labelPercent' : str(round(tlabel['score'] * 100))})		
					resultDictionary['advertise'] = resultLabelDictionary
				else:
					resultDictionary['advertise'] = 'No label in the image'
				#This statement extracts the detected logo in the image if any
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
				'operation' : 'Automatic Annotation',
				'result' : result,
			}
			return render(request, 'detectionresult.html', context)
		else:
			#context contains the data to be passed to the HTML page for the post request
			context = {
				'loggedIn': True,
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'detectionresult.html', context)
		
	
def __generate_json(img, feat):
	'''
	This function gets the json response for each operation for the selected images
	'''
	request_list = []
	#content_json_obj contains the image data on which operation needs to be done
	content_json_obj = {
		'content': img
    }
	#features represent the process that needs to be done on the images
	features = feat
	#feature_json_obj contains the process that needs to be done on the image as well as other parameters for the result
	feature_json_obj = []
	#This statement prepares the request list and detection type
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
	#This statement prepares the request and post the request to the google client
	response = requests.post(url = googleapikey, 
		data = json.dumps({'requests': request_list}), 
		headers = {'Content-Type': 'application/json'})
	into = response.text
	#This statement checks the whether the request is successful or not
	if response.status_code != 200 or response.json().get('error'):
		resp = None
	else:
		for idx, resp in enumerate(response.json()['responses']):
			pass
	#This statement returns the response for each mentioned operation on the image
	return resp

#DETECTION_TYPES contains the list of opearations to be performed on the images
DETECTION_TYPES = [
    'TYPE_UNSPECIFIED',
    'FACE_DETECTION',
    'LANDMARK_DETECTION',
    'LOGO_DETECTION',
    'LABEL_DETECTION',
    'TEXT_DETECTION',
    'SAFE_SEARCH_DETECTION',
]
