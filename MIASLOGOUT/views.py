"""
Process the request and gives back the corresponding response for logout operation
Author: Jeonkyu Lee and Murali krishnan
Last Tested: 6/12/2017 by Murali Krishnan
Verified with: Python 3.6, Django 1.11
"""
from django.shortcuts import render, redirect
from django.http import HttpResponse

###########################################################################
#  Def Name     : logout
#  Input        : request
#  Output       : response(a html page along with the data processed for each request which is a context)
#  Purpose      : To give response to each request for logout operation
#  Author       : Jeonkyu Lee and Murali Krishnan
#  Last Modified: 06/12/2017 by Murali Krishnan
###########################################################################
def logout(request):
	#This statement deletes the logged in user email in the session
	del request.session['uEmail']
	#This statement redirects the user to the welcome page for logout operation
	return redirect('/welcome')
