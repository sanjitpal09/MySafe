from flask import Flask, render_template, request, flash, Response
from forms import ContactForm,SubmitField
from watson_developer_cloud import ToneAnalyzerV3

from smartystreets import Client
import os
app = Flask(__name__)
app.secret_key = 'development key'

# Code for Foursquare API support
from geopy.geocoders import Nominatim # module to convert an address into latitude and longitude values
import requests # library to handle requests\n",
import pandas as pd # library for data analsysis\n",
import numpy as np # library to handle data in a vectorized manner\n",
import random # library for random number generation\n",
import re
from pandas.io.json import json_normalize
import json


#FS Credentials
CLIENT_ID= "FOURSQUARE_CLIENT_ID_HERE"
CLIENT_SECRET="FOURSQUARE_CLIENT_SECRET_HERE"
VERSION = 20170511
LIMIT = 30
search_query = "Apartments"
radius = 3218.69
category_id = "4d954b06a243a5684965b473" # ID for Apartments

#@app.route('/')
#def root():
#   return app.send_static_file('contact.html')

def get_category_type(row):
       try:
           categories_list = row["categories"]
       except:
           categories_list = row["venue.categories"]

       if len(categories_list) == 0:
           return None
       else:
           return categories_list[0]["name"].encode('ascii',errors='ignore')

def numberOfCrimeInstances(jasonCrimeData):
        client = Client('7d546824-690e-8777-5189-f36a22c60a96', 'EUOIlgeMMcwI3HmnLXFw')
        zipCodeJasonCrimeData = []
        for item in jasonCrimeData:
                address = str(item.get('address')) + ", Austin, Texas"
                address = address.upper().replace(' BLOCK', '')
                properAddress = client.street_address(address)
                if properAddress != None:
					zipCode = str(properAddress['components']['zipcode'])
					zipCodeJasonCrimeData.append(zipCode)
		return zipCodeJasonCrimeData#.count(str(inputZipCode))


def getFinalScore(finalAddresses):
	url = "https://data.austintexas.gov/resource/e6ir-dgdv.json"
	response = requests.get(url)

	jasonCrimeData = (response.json())
	numberOfCI = numberOfCrimeInstances(jasonCrimeData)

	ultimateAddressList = {}
	for index in finalAddresses:
		#from IPython import embed
		#embed()
		inputZipCode = finalAddresses[index][2]
		toneScore = getToneScore(finalAddresses[index][3])
		crimeScore = numberOfCI.count(str(inputZipCode))

		ultimateAddressList[index]=(finalAddresses[index][0],finalAddresses[index][1],toneScore,crimeScore)
		#finalAddresses[index] = finalAddresses[index] + (crimeScore,)  + (toneScore,)
	return ultimateAddressList

def getToneScore(text):
        tone_analyser = ToneAnalyzerV3(username='764d55b0-ca85-4bb4-9ff9-9e4b0161d681', password='KEOzscgHHsCC', version='2017-05-19')
	#from IPython import embed
	#embed()
	total = 0.0
	for line in text:
	        tone = tone_analyser.tone(line)
        	anger = tone["document_tone"]['tone_categories'][0]['tones'][0]['score']
	        disgust = tone["document_tone"]['tone_categories'][0]['tones'][1]['score']
        	fear = tone["document_tone"]['tone_categories'][0]['tones'][2]['score']
	        joy = tone["document_tone"]['tone_categories'][0]['tones'][3]['score']
        	sadness = tone["document_tone"]['tone_categories'][0]['tones'][4]['score']

        	total += -(1.6412086*anger) -(1.18552992*disgust) - (0.59426252*fear)  - (0.04731881*joy) - (0.79980865*sadness) + 0.60702012189486587
	if total > 0:
		happy = "Happy :)"
	else:
		happy = "Unhappy :("
	return str(happy)


def gettips(a):
    venue_id = a
    limit = 150 # set limit to be greater than the total number of tips\n",
    url="https://api.foursquare.com/v2/venues/{}/tips?client_id={}&client_secret={}&v={}&limit={}".format(venue_id, CLIENT_ID, CLIENT_SECRET, VERSION, limit)
    results = requests.get(url).json()
    if (results["response"]["tips"]["count"]==0):
        return ['No tip']
    else :
        tips = results["response"]["tips"]["items"]
     	pd.set_option('display.max_colwidth', -1)
        tips_df = json_normalize(tips) # json normalize tips
        tips_filtered = tips_df.ix[:,['text']]
        dfList = tips_filtered['text'].tolist()
        return dfList


"""def my_form_post():
    text = request.form['text']
    processed_text = text.upper()
    return processed_text"""

def my_form_post():
    text = request.form['text']
    processed_text = text.upper()
    return processed_text
	#print("asdsa")

@app.route('/click')
def onClick(address='78613'):
    	geolocator = Nominatim()
    	location = geolocator.geocode(address)
    	latitude = location.latitude
    	longitude = location.longitude

	url='https://api.foursquare.com/v2/venues/search?client_id={}&client_secret={}&ll={},{}&v={}&radius={}&query={}&categoryId={}&limit={}'.format(CLIENT_ID, CLIENT_SECRET, latitude, longitude, VERSION, radius, search_query, category_id, LIMIT)
	results = requests.get(url).json()
	venues = results["response"]["venues"]
	dataframe = json_normalize(venues)
	filtered_columns = ['name', 'url', 'categories', 'verified'] + [col for col in dataframe.columns if col.startswith('location.')] + ['id']
	dataframe_filtered = dataframe.ix[:, filtered_columns]

	dataframe_filtered['categories'] = dataframe_filtered.apply(get_category_type, axis=1)
	dataframe_filtered.columns = [column.split(".")[-1] for column in dataframe_filtered.columns]


	dataframe_apartments = dataframe_filtered.ix[:,['name','formattedAddress','id']]
	limit = min(LIMIT, len(dataframe_apartments))
    	for i in range(limit):
        	dataframe_apartments['formattedAddress'][i]= ','.join(map(str, dataframe_apartments['formattedAddress'][i] ))
        	dataframe_apartments['name'][i]=dataframe_apartments['name'][i].encode('utf-8')

	regex = re.compile(r'7\\d\\d\\d\\d')


	finalAddresses = {}

    	for index, item in enumerate(dataframe_apartments['formattedAddress']):
        	try:
            		regex = re.compile(r'7\d\d\d\d')
            		zipCode = regex.search(item).group()
            		Address = dataframe_apartments['formattedAddress'][index]
            		aptName = dataframe_apartments['name'][index]
			tips = gettips(dataframe_apartments['id'][index])
            		finalAddresses[index] = (aptName, Address, zipCode, tips)
        	except AttributeError:
            		pass
	finalScores = getFinalScore(finalAddresses)
	#final_df = pd.DataFrame(finalScores)
	#return json.dumps(finalScores, sort_keys=True, indent=4)
	return render_template('contact2.html',json=finalScores)

"""@app.route('/contact', methods = ['GET', 'POST'])
def contact():
   form = ContactForm()

   if request.method == 'POST':
		if form.validate() == False:
			flash('All fields are required.')
			return render_template('contact.html', form = form)

		elif request.method == 'GET':
			return render_template('contact.html', form = form)

		else:
			return render_template('success.html')"""

#if __name__ == '__main__':
#	app.run(debug = True)
@app.route('/', methods=['GET','POST'])
def home():
	path = os.path.abspath(os.path.dirname(__file__))
	src = os.path.join(path, 'contact.html')
	content = open(src).read()
	#form = ContactForm()
	#----Modified by selva
	"""if request.method == 'POST':
		return render_template('contact.html', form = form)
	elif request.method == 'GET':
		return render_template('contact.html', form = form)
	else:
		return render_template('success.html')"""
	return Response(content, mimetype="text/html")#----Madhu
	#return render_template('contact.html')


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='127.0.0.1', port=port)
