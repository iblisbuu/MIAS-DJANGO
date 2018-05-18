from django.shortcuts import render, redirect
from MIASREGISTRATION.models import MiasUser

# Create your views here.

def miasRegistration(request):
	if request.method == 'GET':
		return render(request, 'registration.html', {})
	else:
		miasUser = MiasUser.objects.filter(eMail=request.POST['uEmail'])
		print(miasUser)
		if len(miasUser) == 0:
			#MiasUser.objects.create(firstName=request.POST['uFrstName'], lastName=request.POST['uLstName'], 
		                            #eMail=request.POST['uEmail'], password=request.POST['uPassword'])
			newUser = MiasUser()
			newUser.firstName = request.POST['uFrstName']
			newUser.lastName = request.POST['uLstName']
			newUser.eMail = request.POST['uEmail']
			newUser.password = request.POST['uPassword']
			newUser.save()
			context = {
				'sMessage': 'You have successfully registered. Please Login to continue.',
			}
			#print('Successfully registered')
			#return render(request, 'login.html', context)
			return redirect('/login', context)
		else:
			context = {
				'eMessage': 'Email already exists',
			}
			print('Email already exists')
			return render(request, 'registration.html', context)
