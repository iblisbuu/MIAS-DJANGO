from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.conf import settings
from google.cloud import storage as gStorage
from MIASSTORAGE import storage
from datetime import datetime
import numpy as np
import time
import json
import requests
import base64
import cv2
from io import BytesIO, StringIO
# from google.cloud import vision
from google.cloud.vision_v1 import ImageAnnotatorClient
from google.cloud import datastore
import math

#objects contains the total images in the selected bucket
objects = {}

def imageSearchHome(request):
	global objects
	if request.method == 'GET':
		try:
			loggedInUser = request.session['uEmail']
		except:
			return redirect('/welcome')
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
		return render(request, 'imageSearch.html', context)
	else:
		if request.POST['submit'] == 'Image Search':
			#totalSelectedImages contains the list of images selected by the user
			totalSelectedImages = request.POST.getlist('miasImages')
			# client does the required operation on the selected image for annotations
			client = ImageAnnotatorClient()
			image_details = []
			# image_details contains the list of image information such as image url and features that
			# need to be done on the images for annotations
			image_requests = []
			# image_features contains the list of operations that need to be performed on the image
			image_features = [{'type': DETECTION_TYPES[3]}, 
							  {'type': DETECTION_TYPES[4]}, 
			                  {'type': DETECTION_TYPES[5]}]
			# total_images is a counter for counting the total number of images selected by the user
			total_images = 0
			# image_histograms contains the list of histogram information for the selected images
			image_histograms = []
			# This block gets the histogram information as well as the image information
			# for the selected images 
			for eachImage in totalSelectedImages:
				image_requests.append({'image': {'source': {'image_uri': eachImage.split('+')[1]}},
									   'features': image_features,})
				# image_content contains the image data from the url
				image_content = requests.get(eachImage.split('+')[1])
				# print('image_content: ')
				# print(type(image_content.content))
				image_array = np.asarray(bytearray(BytesIO(image_content.content).getvalue()), dtype='uint8')
				# print('image_array: ')
				# print(type(image_array))
				converted_image_array = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
				# print(type('converted_image_array: '))
				# print(type(converted_image_array))
				individual_image_histogram = []
				if converted_image_array.shape[2] != 3:					
					for each_channel in range(0, 3):
						if each_channel == 0:
							individual_image_histogram.append({'redChannel': \
															     cv2.calcHist([converted_image_array], \
																              [0], None, [256], [0, 256]).tolist()
															  })
						elif each_channel == 1:
							individual_image_histogram.append({'greenChannel': \
															     cv2.calcHist([converted_image_array], \
																              [1], None, [256], [0, 256]).tolist()
															  })
						else:
							individual_image_histogram.append({'blueChannel': \
															     cv2.calcHist([converted_image_array], \
																              [2], None, [256], [0, 256]).tolist()
															  })
				else:
					individual_image_histogram.append({'singleChannel': \
					                                    cv2.calcHist([converted_image_array],[0], None, \
														[256], [0, 256]).tolist()
													  })
				
				image_histograms.append({'index': total_images, 'histogram': individual_image_histogram })
				total_images = total_images + 1
			image_response = client.batch_annotate_images(image_requests)
			image_labels = []
			image_logos = []
			for index, eachResponse in enumerate(image_response.responses):
				if len(image_response.responses[index].label_annotations) != 0:
					labels = []
					for eachLabel in range(len(image_response.responses[index].label_annotations)):
						labels.append({'labelDescription': \
						                image_response.responses[index].label_annotations[eachLabel].description, \
									   'labelPercent': \
										str(round(image_response.responses[index].label_annotations[eachLabel].score * 100)),
						              })
					image_labels.append({'index': index, 'labels': labels})
				else:
					image_labels.append({'index': index, 'labels': []})
			for index, eachResponse in enumerate(image_response.responses):
				if len(image_response.responses[index].logo_annotations) != 0:
					logos = []
					for eachLogo in range(len(image_response.responses[index].logo_annotations)):
						logos.append({'logoDescription': \
						               image_response.responses[index].logo_annotations[eachLogo].description, \
									  'logoPercent': \
									   str(round(image_response.responses[index].logo_annotations[eachLogo].score * 100)),
						             })
					image_logos.append({'index': index, 'logos': logos})
				else:
					image_logos.append({'index': index, 'logos': []})
			# datastore_client contains methods for accessing GCP's datastore
			datastore_client = datastore.Client()
			# This block creates entity in the datastore kind MIASJSON for storing image information as a
			# JSON format
			for index, eachImage in enumerate(totalSelectedImages, 0):
				# key creates a key for the kind MIASJSON in the datastore
				key = datastore_client.key('MIASJSON', eachImage.split('+')[0])
				# entity creates an entity in the MIASJSON kind in the datastore
				entity = datastore.entity.Entity(key, ('image_info', 'text_info', \
				                                       'label_info', 'logo_info', \
													   'histogram_info'))
				# This statement creates a property named image_info which stores image data 
				# such as image name and its uri
				entity['image_info'] = json.dumps({'image_name': eachImage.split('+')[0], 
				                                   'image_url': eachImage.split('+')[1],
												  })
				# This statement creates a property named text_info which stores text data 
				# if available in the image
				entity['text_info'] = json.dumps({'text_data': image_response.responses[index].text_annotations[0].description \
 								                  if (len(image_response.responses[index].text_annotations) != 0) \
								                  else 'No text in the image',
											     })
				# This statement creates a property named label_info which stores label data 
				# if available in the image
				entity['label_info'] = json.dumps({'label_data': 'No label in the image' \
										                         if (len(image_labels[index]['labels']) == 0) \
													             else image_labels[index]['labels'],
												  })
				# This statement creates a property named logo_info which stores logo data 
				# if available in the image
				entity['logo_info'] = json.dumps({'logo_data': 'No logo in the image' \
										                       if (len(image_logos[index]['logos']) == 0) \
													           else image_logos[index]['logos'],
												 })
				# This statement creates a property named histogram_info which stores histogram data 
				# if available in the image
				entity['histogram_info'] = json.dumps({'histogram_data': image_histograms[index]['histogram']})
				datastore_client.put(entity)
			# context contains the data to be passed to the HTML page for the post request
			context = {
				'loggedIn': True,
				'operation': 'ImageSearch',
				'objects': objects,
				'result': True,
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'imageSearch.html', context)
		elif request.POST['submit'] == 'Similarity':
			#totalSelectedImages contains the list of images selected by the user
			totalSelectedImages = request.POST.getlist('miasImages')
			ed_result = []
			for eachImage in totalSelectedImages:
				image_content = requests.get(eachImage.split('+')[1])
				image_array = np.asarray(bytearray(BytesIO(image_content.content).getvalue()), dtype='uint8')
				converted_image_array = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
				selected_image_histogram = cv2.calcHist([converted_image_array],[0], None, \
														[256], [0, 256])										
				# datastore_client contains methods for accessing GCP's datastore
				datastore_client = datastore.Client()
				datastore_query = datastore_client.query(kind = 'MIASJSON')
				result = list(datastore_query.fetch())
				similarity_result = []
				for eachResult in result:
					individual_result = json.loads(dict(eachResult)['histogram_info'])
					histogram_data = np.array(individual_result['histogram_data'][0]['singleChannel'])
					euclidean_distance = np.sqrt(np.sum((selected_image_histogram - histogram_data) ** 2))
					similarity_result.append({'image_name': eachResult.key.name, 'distance': euclidean_distance})
					# print(euclidean_distance)
				ed_result.append({'image_name': eachImage.split('+')[0], 'similarity_result': similarity_result})
			# context contains the data to be passed to the HTML page for the post request
			context = {
				'loggedIn': True,
				'operation': 'Similarity',
				'objects': objects,
				'ed_result': ed_result,
				'result': True,
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'imageSearch.html', context)
				
				
			
				
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