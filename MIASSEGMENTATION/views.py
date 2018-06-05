"""
Process the request and gives back the corresponding response for /segmentation url
Author: Jeonkyu Lee and Murali krishnan
Last Tested: 6/12/2017 by Murali Krishnan
Verified with: Python 3.6, Django 1.11
"""

from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.conf import settings
from google.cloud import storage as gstorage
from MIASSTORAGE import storage
from datetime import datetime
from google.cloud import vision
from PIL import Image, ImageDraw
import json
import cv2
import time
import base64
import requests
from io import BytesIO, StringIO
import numpy as np
import os
import threading

#result contains the result for each request
result = []

###########################################################################
#  Def Name     : segmentationHome
#  Input        : request
#  Output       : response(a html page along with the data processed for each request which is a context)
#  Purpose      : To give response to each request for the url '/segmentation'
#  Author       : Jeonkyu Lee, Murali Krishnan and Umang Patel
#  Last Modified: 06/12/2017 by Murali Krishnan
############################################################################
def segmentationHome(request):
	global result
	if request.method == 'GET':
		'''
		This block returns the response for the get request for /segmentation url
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
				blobs = []
				respobject = storage.list_objects(lstbct['name'])
				filteredImageName = None
				#This statement extracts the images in the root folder of each bucket
				for index, bct in enumerate(respobject):
					if 'segment/' in str(bct['name']):
						pass
					else:
						filteredImageName = str(bct['name'])
						blobs.append({'index': index, 'name': str(bct['name']), 'filteredName': filteredImageName,
                                      'public_url': 'https://storage.googleapis.com/' + lstbct['name'] + '/' + str(
                                          bct['name']),
                                      'timecreated': datetime.strptime(str(bct['timeCreated']),
                                                                       '%Y-%m-%dT%H:%M:%S.%fZ'),
                                      'type': str(bct['contentType'])})
				objects.update({lstbct['name']: blobs})
		#context contains the data to be passed to the HTML page for the get request
		context = {
            'loggedIn': True,
            'objects': objects,
        }
		#This statement returns the response as a HTML page along with the data to be displayed in it
		return render(request, 'segmentationHome.html', context)
	else:
		'''
		This block returns the response for the post request for /segmentation url
		'''
		if request.POST['submit'] == 'AD Segment':
			'''
			This block performs the segmentation in the image
			'''
			#selectedImages contains the list of images selected by the user
			selectedImages = request.POST.getlist('miasimages')
			result = []
			#threads contains the list of threads being created
			threads = []
			#initThreadsCnt gives the total number of threads currently available
			initThreadsCnt = threading.active_count()
			sensitivity_type = request.POST['Sensitivity']
			# sensitivity_point = int(request.POST['sPoint'])
			print("Initial Thread cnt => " + str(initThreadsCnt))

			for index, image in enumerate(selectedImages):
				t = threading.Thread(target=onAdSegment,args=(image,index))
				threads.append(t)
				t.start()
			cnt = 0
			print("After Thread cnt => " + str(threading.active_count()))
			while (initThreadsCnt != threading.active_count()):
				cnt += 1
				time.sleep(1)
				if cnt > 20:
					break
			#context contains the data to be passed to the HTML page for the post request
			context = {
                'loggedIn': True,
                'result': result,
            }
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'segmentationResult.html', context)
		elif request.POST['submit'] == 'Contour Segment':
			'''
			This block performs the contour segment in the image
			'''
			selectedImages = request.POST.getlist('miasimages')
			result = []
			for image in selectedImages:
				response = requests.get(image.split('+')[0])
				selectedImage = base64.b64encode(BytesIO(response.content).getvalue())
				img = np.asarray(bytearray(BytesIO(response.content).getvalue()), dtype='uint8')
				convertedImage = cv2.imdecode(img, cv2.IMREAD_COLOR)
				gray = cv2.cvtColor(convertedImage, cv2.COLOR_BGR2GRAY)
				edges = cv2.Canny(gray, 10, 100, apertureSize=3)
				_, contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
				for i, c in enumerate(contours):
					area = cv2.contourArea(c)
					if area > 1000:
						cv2.drawContours(convertedImage, contours, i, (255, 0, 0), 3)
				im = Image.fromarray(cv2.cvtColor(convertedImage, cv2.COLOR_BGR2RGB))
				inMemory = BytesIO()
				im.save(inMemory, format='jpeg')
				inMemory.seek(0)
				imgBytes = inMemory.read()
				b64Image = base64.b64encode(imgBytes)
				result.append({'inputImage': image.split('+')[0], 'resultImage': b64Image})
			#context contains the data to be passed to the HTML page for the post request
			context = {
                'loggedIn': True,
                'result': result,
            }
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'segmentationResult.html', context)
		else:
			'''
			This block performs the hough lines in the image
			'''
			#selectedImages contains the list of images selected by the user
			selectedImages = request.POST.getlist('miasimages')
			result = []
			for image in selectedImages:
				response = requests.get(image.split('+')[0])
				selectedImage = base64.b64encode(BytesIO(response.content).getvalue())
				img = np.asarray(bytearray(BytesIO(response.content).getvalue()), dtype='uint8')
				convertedImage = cv2.imdecode(img, cv2.IMREAD_COLOR)
				gray = cv2.cvtColor(convertedImage, cv2.COLOR_BGR2GRAY)
				edges = cv2.Canny(gray, 10, 100, apertureSize=3)
				lines1 = cv2.HoughLinesP(edges, 1, np.pi, threshold=100, minLineLength=100, maxLineGap=1)
				for x in range(0, len(lines1)):
					for x1, y1, x2, y2 in lines1[x]:
						cv2.line(convertedImage, (x1, y1), (x2, y2), (255, 0, 0), 3)
				lines2 = cv2.HoughLinesP(edges, 1, np.pi / 2, threshold=100, minLineLength=100, maxLineGap=1)
				for x in range(0, len(lines2)):
					for x1, y1, x2, y2 in lines2[x]:
						cv2.line(convertedImage, (x1, y1), (x2, y2), (255, 0, 0), 3)
				im = Image.fromarray(cv2.cvtColor(convertedImage, cv2.COLOR_BGR2RGB))
				inMemory = BytesIO()
				im.save(inMemory, format='jpeg')
				inMemory.seek(0)
				imgBytes = inMemory.read()
				b64Image = base64.b64encode(imgBytes)
				result.append({'inputImage': image.split('+')[0], 'resultImage': b64Image})
			#context contains the data to be passed to the HTML page for the post request
			context = {
                'loggedIn': True,
                'result': result,
            }
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'segmentationResult.html', context)

###########################################################################
#  Def Name     : onAdSegment
#  Input        : image to be segmented and index of the image in the list
#  Output       : segmented images
#  Purpose      : To segment an image
#  Author       : Jeonkyu Lee, Murali Krishnan and Umang Patel
#  Last Modified: 06/12/2017 by Murali Krishnan
############################################################################
def onAdSegment(image, idx):
    bucket = image.split('+')[2]
    miasImagesStorage = gstorage.Client()
    miasBucket = miasImagesStorage.get_bucket(bucket)
    selectedBucket = miasBucket
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
                        cv2.rectangle(convertedImage, (int(colX1), int(rowTemp)), (int(colX2), int(row)),
                                      (0, 255, 0), 3)
            else:
                if (cnt >= (colX2 - colX1 + 1 - leftrightMargin) or (
                    cntB >= (colX2 - colX1 + 1 - leftrightMargin))):  # White line
                    if (conTinueYN == True):
                        if (row - rowTemp) > minRegionHight:
                            detectRegionOfAD.append([colX1, rowTemp, colX2, row])
                            cv2.rectangle(convertedImage, (int(colX1), int(rowTemp)),
                                          (int(colX2), int(row)), (0, 255, 0), 3)
                        conTinueYN = False
                else:  # Contents
                    if (conTinueYN == False):
                        rowTemp = row
                        conTinueYN = True
    im = Image.fromarray(cv2.cvtColor(convertedImage, cv2.COLOR_BGR2RGB))
    inMemory = BytesIO()
    im.save(inMemory, format='jpeg')
    inMemory.seek(0)
    imgBytes = inMemory.read()
    b64Image = base64.b64encode(imgBytes)
    adSegments = 0
    for detectReg in range(0, len(detectRegionOfAD)):
        output_img = im.crop(detectRegionOfAD[detectReg])
        inMemorySeg = BytesIO()
        output_img.save(inMemorySeg, format='png')
        inMemorySeg.seek(0)
        imgBytesSeg = inMemorySeg.read()
        b64ImageSeg = base64.b64encode(imgBytesSeg)
        segmentedImageName = image.split('+')[1].split('.')[0] + '_segment_' + str(adSegments)
        adSegments += 1
        blob = selectedBucket.blob(
            segmentedImageName + '_' + str(time.time()) + '.' + image.split('+')[1].split('.')[1])
        blob.upload_from_string(imgBytesSeg, ('image/' + image.split('+')[1].split('.')[1]))
    result.insert(idx, {'inputImage': image.split('+')[0], 'resultImage': b64Image})
    return
