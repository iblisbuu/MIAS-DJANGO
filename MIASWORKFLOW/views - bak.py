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

googleapikey = 'https://vision.googleapis.com/v1/images:annotate?key=AIzaSyDQ6OmhEqEKvbIiHmjOz_ZIZW4ZTAwdmKA'
selectedBucket = None

# Create your views here.

def workflowHome(request):
	global selectedBucket
	if request.method == 'GET':
		try:
			loggedInUser = request.session['uEmail']
		except:
			#return redirect('/login')
			return redirect('/welcome')
		context = {
			'loggedIn' : True,
			'operationStep' : 'Workflow',
			'buckets' : None,
		}
		return render(request, 'workflow.html', context)
	else:
		if request.POST['submit'] == 'Start Workflow':
			miasClient = storage.Client()
			availableBuckets = miasClient.list_buckets()
			resultBuckets = []
			for bucket in availableBuckets:
				if bucket.name.startswith('datacore'):
					resultBuckets.append(bucket)					
			context = {
				'loggedIn': True,
				'operationStep' : 'Selection',
				'buckets': resultBuckets,
			}			
			return render(request, 'workflow.html', context)
		elif request.POST['submit'] == 'Step 2: Segmentation':
			# Retrieve number of files in the selected bucket
			#global selectedBucket
			miasImagesStorage = storage.Client()
			miasBucket = miasImagesStorage.get_bucket(request.POST['bucket'])
			selectedBucket = miasBucket
			images = miasBucket.list_blobs()
			filteredImages = []
			segmentedImages = []
			#filteredImageName = None
			for image in images:
				if 'segment/' in image.name:
					pass
					#filteredImageName = image.name.split('/')[2]
					#filteredImages.append({'bucket': request.POST['bucket'],'url': image.public_url, 'name' : image.name, 'filteredName': filteredImageName})
				else:
					#filteredImageName = image.name
					filteredImages.append({'bucket': request.POST['bucket'],'url': image.public_url, 'name' : image.name})
			context = {
				'loggedIn': True,
				'operationStep': 'Classify',
				'miasimages': filteredImages,
			}
			return render(request, 'workflow.html', context)
		elif request.POST['submit'] == 'Step 3: Classification':
			#global selectedBucket
			selectedImages = request.POST.getlist('miasimages')
			# availableImages = selectedBucket.list_blobs()
			# for availableImage in availableImages:
			# 	pass
			#bucket = None
			threads = []
			initThreadsCnt = threading.active_count()
			print("Initial Thread cnt => " + str(initThreadsCnt))

			for index, image in enumerate(selectedImages):
				t = threading.Thread(target=onClassification, args=(image, index))
				threads.append(t)
				t.start()
				print("Thread " + str(index) + " started")

			cnt = 0
			print("After Thread cnt => " + str(threading.active_count()))
			while (initThreadsCnt != threading.active_count()):
				cnt += 1
				#print("Time -> " + str(cnt) + "    Current Thread cnt => " + str(threading.active_count()))
				time.sleep(1)
				# if cnt > 20:
				# 	break

			totalImages = selectedBucket.list_blobs()
			adSegmentedImages = []
			nonAdSegmentedImages = []
			totalSegmentedImages = []
			for individualImage in totalImages:
				if 'segment/ad' in individualImage.name:
					adSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				elif 'segment/nonad' in individualImage.name:
					nonAdSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				else:
					pass
			totalSegmentedImages.append({'segmentType': 'ad', 'adSegmentedImages': adSegmentedImages})
			totalSegmentedImages.append({'segmentType': 'nonad','nonAdSegmentedImages': nonAdSegmentedImages})
			context = {
				'bucket' : selectedBucket.name,
				'loggedIn': True,
				'operationStep' : 'ClassifiedImages',
				'totalSegmentedImages' : totalSegmentedImages,
			}
			return render(request, 'workflow.html', context)
		elif request.POST['submit'] == 'Step 4: QA':
			totalNonAdImages = []
			selectedImagesWf = request.POST.getlist('miasCropImages')
			bucket = None
			count = 0
			for imageWf in selectedImagesWf:
				count += 1
				bucket = imageWf.split('+')[0]
				responseCrop = requests.get(imageWf.split('+')[2])
				cropImage = base64.b64encode(BytesIO(responseCrop.content).getvalue()).decode()
				selectedImageNameWf = imageWf.split('+')[1]
				croppedImageName = selectedImageNameWf.split('/')[0] + '/ad/' + 'cropped_' + selectedImageNameWf.split('/')[2]
				totalNonAdImages.append({'imageName': croppedImageName, 'imageData': cropImage})
			context = {
				'count' : count,
				'loggedIn': True,
				'operationStep': 'CropImage',
				'totalNonAdImages': totalNonAdImages,
				'bucket': bucket,
			}
			return render(request, 'workflow.html', context)
		elif request.POST['submit'] == 'Automatic Annotation':
			features = '3:10 4:10 5:10'
			selectedImages = request.POST.getlist('miasCropImages')
			bucket = None
			result = []
			for image in selectedImages:
				resultDictionary = {'imageUrl': '', 'fileName' : '', 'mediaType' : '', 'advertise' : None, 'logo' : '', 'logoPercent' : '', 'headLine' : '', 'text' : ''}
				resultLabelDictionary = []
				resultDictionary['imageUrl'] = image.split('+')[2]
				response = requests.get(image.split('+')[2])
				selectedImage = base64.b64encode(BytesIO(response.content).getvalue()).decode()
				__resp = __generate_json(selectedImage, features)
				resultDictionary['fileName'] = image.split('+')[1]
				resultDictionary['mediaType'] = 'Image'
				resultDictionary['headLine'] = 'N/A'
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
			context = {
				'loggedIn': True,
				'operationStep' : 'Automatic Annotation',
				'result' : result,
			}
			return render(request, 'workflow.html', context)
		elif request.POST['submit'] == 'List Segments':
			totalImages = selectedBucket.list_blobs()
			adSegmentedImages = []
			nonAdSegmentedImages = []
			totalSegmentedImages = []
			for individualImage in totalImages:
				if 'segment/ad' in individualImage.name:
					adSegmentedImages.append(
						{'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				elif 'segment/nonad' in individualImage.name:
					nonAdSegmentedImages.append(
						{'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				else:
					pass
			totalSegmentedImages.append({'segmentType': 'ad', 'adSegmentedImages': adSegmentedImages})
			totalSegmentedImages.append({'segmentType': 'nonad', 'nonAdSegmentedImages': nonAdSegmentedImages})
			context = {
				'bucket': selectedBucket.name,
				'loggedIn': True,
				'operationStep': 'ClassifiedImages',
				'totalSegmentedImages': totalSegmentedImages,
			}
			return render(request, 'workflow.html', context)
		else:
			miasImagesStorage = storage.Client()
			miasBucket = miasImagesStorage.get_bucket(request.POST['selectedBucket'])
			totalCroppedImage = int(request.POST['totalCount'])
			for croppedImages in range(totalCroppedImage):
				try:
					imageName = request.POST['imageNameHidden_' + str(croppedImages)]
					if 'segment/ad' in imageName:
						croppedImageData = request.POST['imageDataHidden_' + str(croppedImages)]
						b64CroppedImageData = croppedImageData[22: ]
						blob = miasBucket.blob(imageName)
						blob.upload_from_string(base64.b64decode(b64CroppedImageData), ('image/' + imageName.split('.')[2]))
					else:
						croppedImageData = request.POST['imageDataHidden_' + str(croppedImages)]
						b64CroppedImageData = croppedImageData[22: ]
						blob = miasBucket.blob(imageName)
						blob.upload_from_string(base64.b64decode(b64CroppedImageData), ('image/' + imageName.split('.')[2]))
				except:
					pass
			totalImages = miasBucket.list_blobs()	
			adSegmentedImages = []
			nonAdSegmentedImages = []
			totalSegmentedImages = []
			for individualImage in totalImages:
				if 'segment/ad' in individualImage.name:
					adSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				elif 'segment/nonad' in individualImage.name:
					nonAdSegmentedImages.append({'image': individualImage, 'filteredName': individualImage.name.split('/')[2]})
				else:
					pass		
			totalSegmentedImages.append({'segmentType': 'ad', 'adSegmentedImages': adSegmentedImages})
			totalSegmentedImages.append({'segmentType': 'nonad','nonAdSegmentedImages': nonAdSegmentedImages})
			context = { 
				'loggedIn' : True,
				'operationStep' : 'Save',
				'operationSave' : True,
				'totalSegmentedImages' : totalSegmentedImages,
				'bucket' : request.POST['selectedBucket'],
			}
			return render(request, 'workflow.html', context)
			
def labelDetection(inputImage, feature):
	features = feature
	#selectedImage = base64.b64encode(BytesIO(inputImage.content).getvalue()).decode()
	selectedImage = inputImage.decode()
	__label = __generate_json(selectedImage, features)
	advertisementImage = False
	if 'labelAnnotations' in __label:
		for index, tlabel in enumerate(__label['labelAnnotations'], start=0):
			if (str(tlabel['description']) == 'advertising') or (str(tlabel['description']) == 'brand'):
				advertisementImage = True
	return advertisementImage
	
def onClassification(image, idx):
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
		adNonAd = labelDetection(b64Image, '4:10')
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

	return

		#result.insert(idx, {'inputImage': image.split('+')[0], 'resultImage': b64Image})
        # end Added


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

