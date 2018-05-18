"""
Process the request and gives back the corresponding response for /home url
Author: Jeonkyu Lee and Murali krishnan
Last Tested: 6/12/2017 by Murali Krishnan
Verified with: Python 3.6, Django 1.11
"""

from django.shortcuts import render

###########################################################################
#  Def Name     : home
#  Input        : request
#  Output       : response(a html page along with the data processed for each request which is a context)
#  Purpose      : To give response to each request for the url '/home'
#  Author       : Jeonkyu Lee and Murali Krishnan
#  Last Modified: 06/12/2017 by Murali Krishnan
############################################################################
def home(request):
	'''
	This block returns the response for the get request for the /home url
	If user has logged in, the user will be redirected to the home page 
	otherwise the user will be redirected to the welcome page
	'''
	try:
		#loggedInUser contains the email of the user if he/she has logged in
		loggedInUser = request.session['uEmail']
		#context contains the data to be passed to the HTML page for the get request
		context = {
			'loggedIn' : True,
		}
		#This statement returns the response as a HTML page along with the data to be displayed in it
		return render(request, 'home.html', context)
	except:
		#context contains the data to be passed to the HTML page for the get request
		context = {
			'loggedIn' : False,
		}
		#This statement returns the response as a HTML page along with the data to be displayed in it
		return render(request, 'datacore.html', context)
	
	
###########################################################################
#  Def Name     : home
#  Input        : request
#  Output       : response(a html page along with the data processed for each request which is a context)
#  Purpose      : To give response to the request for the url '/welcome'
#  Author       : Jeonkyu Lee and Murali Krishnan
#  Last Modified: 06/12/2017 by Murali Krishnan
############################################################################
def welcome(request):
	#This statement returns the response as a HTML page along with the data to be displayed in it
	return render(request, 'datacore.html', {})
