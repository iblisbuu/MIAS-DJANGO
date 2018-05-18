"""
Process the request and gives back the corresponding response for /login url
Author: Jeonkyu Lee and Murali krishnan
Last Tested: 6/12/2017 by Murali Krishnan
Verified with: Python 3.6, Django 1.11
"""

from django.shortcuts import render, redirect
from MIASREGISTRATION.models import MiasUser

###########################################################################
#  Def Name     : miasLogin
#  Input        : request
#  Output       : response(a html page along with the data processed for each request which is a context)
#  Purpose      : To give response to each request for the url '/login'
#  Author       : Jeonkyu Lee and Murali Krishnan
#  Last Modified: 06/12/2017 by Murali Krishnan
############################################################################
def miasLogin(request, context = None):
	if request.method == 'GET':
		'''
		This block returns the response for the get request which is the login page
		'''
		#This statement returns the response as a HTML page along with the data to be displayed in it
		return render(request, 'login.html', context)
	else:
		'''
		This block checks for the user credentials in the database. 
		If available the user will be redirected to the home page otherwise corresponding messages will be displayed to the user
		'''
		#user_email contains the email of the logged in user
		user_email = request.POST['uEmail']
		#user_password contains the password of the logged in user
		user_password = request.POST['uPassword']
		try:
			#This statement checks whether the user exists in the database
			miasUser = MiasUser.objects.get(eMail = user_email, password = user_password)
			#This statement stores the user email in the session for future references
			request.session['uEmail'] = miasUser.eMail
			#This statement redirects the user to the home page if successful login
			return redirect('/home')
		except:
			#context contains the data to be passed to the HTML page for the get request
			context = {
				'eMessage': 'Invalid Credentials', 
			}
			#This statement returns the response as a HTML page along with the data to be displayed in it
			return render(request, 'login.html', context)