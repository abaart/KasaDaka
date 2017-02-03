from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, send_from_directory
from sparqlInterface import executeSparqlQuery, executeSparqlUpdate
import sparqlInterface
from datetime import datetime, date, timedelta
import calendar
from werkzeug import secure_filename
import config
from languageVars import LanguageVars, getVoiceLabels
import sparqlHelper
import languageVars
import random
import subprocess
import shutil
import glob
import re
import urllib
import copy
import os.path
import os
from base64 import b16encode , b16decode

app = Flask(__name__)
app.secret_key = 'asdfbjarbja;kfbejkfbasjkfbslhjvbhcxgxui328'
app.config['UPLOAD_FOLDER'] = config.audioPath



@app.route('/')
def index():
    """ Index page
	Only used to confirm hosting is working correctly
	"""
    return 'This is the Kasadaka Vxml generator'



@app.route('/admin/')
def adminIndex():
    return render_template('admin/index.html')

@app.route('/admin/object')
def objectInfo():
    """
    Presents a page with all information about an object from the HTTP GET (base16 encoded).
    """
    if 'uri' not in request.args: return "Error, no uri specified"
    URI = b16decode(request.args['uri'])
    voiceLabels = getVoiceLabels(URI,changeLocalhostIP = request.host)
    objectType = sparqlHelper.determineObjectType(URI)
    fieldNames = sparqlHelper.propertyLabels(objectType)
    result = sparqlHelper.objectInfo(URI)
    objectTypeLabel = sparqlHelper.retrieveLabel(objectType)
    editable = False
    return render_template(
        'admin/object.html',
        data = result, 
        fieldNames = fieldNames, 
        uri = URI,
        voiceLabelResults = voiceLabels,
        objectTypeLabel=objectTypeLabel,
        editable = editable)

@app.route('/admin/list')
def objectList(objectType = ""):
    """
    Presents a page with a list of all objects of a given type from the HTTP GET (base16 encoded)
    """
    if 'uri' not in request.args and len(objectType) == 0: return "Error, no uri specified"
    if len(objectType) == 0:
        objectTypeBaseEncoded = request.args['uri']
        objectType = b16decode(objectTypeBaseEncoded)
    else:
        objectTypeBaseEncoded = b16encode(objectType)
    output = sparqlHelper.objectList(objectType)
    fieldNames = sparqlHelper.propertyLabels(objectType,firstColumnIsURI=True)
    recordURIs = sparqlHelper.createURIarray(output)
    objectTypeLabel = sparqlHelper.retrieveLabel(objectType)
    return render_template('admin/list.html',
        data=output,
        fieldNames = fieldNames,
        objectTypeLabel = objectTypeLabel,
        objectTypeBaseEncoded = objectTypeBaseEncoded,
        recordURIs = recordURIs
        )

@app.route('/admin/new')
def showNewObjectPage():
    if 'uri' not in request.args: return "Error, no uri specified"
    objectTypeBaseEncoded = request.args['uri']
    objectType = b16decode(objectTypeBaseEncoded)
    fieldNames = sparqlHelper.propertyLabels(objectType)
    properties = [[]]
    for prop in sparqlHelper.getDataStructure(objectType):
        properties[0].append(b16encode(prop))
    objectTypeLabel = sparqlHelper.retrieveLabel(objectType)
    return render_template(
                    'admin/object.html',
                    data = properties, 
                    fieldNames = fieldNames, 
                    uri = 'NEW ' + objectTypeLabel,
                    new=True,
                    objectTypeLabel = objectTypeLabel,
                    objectType = objectType)

@app.route('/admin/insert', methods=['POST'])
def insertNewObject():
    if 'objectType' not in request.form: return "Error, no objectType specified"
    if 'uri' not in request.form: return "Error, no uri for new object specified"
    URI = request.form['uri']
    objectType = request.form['objectType']
    properties = sparqlHelper.getDataStructure(objectType)
    dataTuples = createDataTuples(properties,request)
    success = len(sparqlHelper.insertObjectTriples(URI,objectType,dataTuples))
    if success: 
        flash(objectType+" successfully inserted! Please record audio for new "+objectType+" on audio page!")
    else: 
        flash("Error inserting "+objectType)
    return objectList(objectType)

@app.route('/admin/delete', methods=['POST'])
def deleteObject():
    if 'uri' not in request.form: return "Error, no uri specified"
    URI = request.form['uri']
    objectType = sparqlHelper.determineObjectType(URI)
    success = sparqlInterface.deleteObject(URI)
    if success:
        flash("URI:" + URI +' deleted!')
    else:
        flash('Error in deleting '+URI)
    return objectList(objectType)

@app.route('/admin/update', methods=['POST'])
def updateObject():
    if 'uri' not in request.form: return "Error, no uri specified"    
    URI = request.form['uri']
    objectType = sparqlHelper.determineObjectType(URI)
    properties = sparqlHelper.getDataStructure(objectType)
    insertTuples = createDataTuples(properties,request)
    deleteProperties = properties
    success = sparqlHelper.objectUpdate(URI,deleteProperties,insertTuples)
    if success:
        flash(objectType+' data successfully updated!')
    else:
        flash('Error in updating '+objectType)
    return objectList(objectType)

def createDataTuples(properties, request):
    dataTuples = []
    for prop in properties:
        encodedProp = b16encode(prop)
        if encodedProp not in request.form: raise ValueError("Not all nessecary properties given! Missing: " + prop)
        if len(prop) == 0 or len(request.form[encodedProp]) == 0: raise ValueError('Empty tuple!')
        dataTuples.append([prop,request.form[encodedProp]])
    return dataTuples

@app.route('/saymessage.vxml',methods=['GET'])
def sayMessageVXML():
    if 'callerid' not in request.args: return errorVXML()
    lang = LanguageVars("http://purl.org/collections/w4ra/speakle/voicelabel_fr")
    preMessages = [lang.getInterfaceAudioURL('speakYourMessage.wav'),
        lang.getInterfaceAudioURL('endRecordingWithAnyPress.wav')]
    postMessages = [lang.getInterfaceAudioURL('press1ToConfirm.wav'),
        lang.getInterfaceAudioURL('press2ToRetry.wav')]
    passOnVariables =   [['callerid',request.args['callerid']],['language',str(lang)]]
    return render_template('record.vxml',
        preMessages = preMessages,
        postMessages = postMessages,
        passOnVariables = passOnVariables,
        redirect= 'insertMessage.vxml')

@app.route('/insertMessage.vxml',methods=['GET'])
def insertMessageVXML():
    if 'callerid' not in request.args or 'language' not in request.args or 'recording' not in request.args: return errorVXML()
    lang = LanguageVars("http://purl.org/collections/w4ra/speakle/voicelabel_fr")
    callerid = request.args['callerid']
    recordingLocation = request.args['recording']
    recordingLocation = saveRecording(recordingLocation)
    success = insertNewMessage(recordingLocation,callerid,lang)
    if success:
        messages = [lang.getInterfaceAudioURL('insertMessageSuccess.wav')]
        return render_template('message.vxml',
            messages = messages,
            redirect = "")
    else: return errorVXML()

def insertNewMessage(recordingLocation,callerid,lang):
    voicelabelLanguage = str(lang)
    voicelabelLanguage =  "http://purl.org/collections/w4ra/speakle/voicelabel_fr"
    if len(callerid) == 0: callerid = "unknown"
    objectType =  "http://example.org/foroba-blon/message"
    preferredURI = objectType
    currentDate = datetime.now().strftime(config.dateFormat)
    recordingLocation = recordingLocation.replace(config.audioPath,config.audioURLbase)
    tuples = [["http://example.org/foroba-blon/date",currentDate],
        ["http://example.org/foroba-blon/contact_tel",callerid],
        [voicelabelLanguage,recordingLocation]]
    return len(sparqlHelper.insertObjectTriples(preferredURI,objectType,tuples)) != 0


def saveRecording(path):
    #remove file:// if present
    #a lot of %00 stuff to remove
    path =  path.replace("\00","")
    path = re.sub(r"(file:\/\/)?(.*)",r"\2",path)
    dest = findFreshFilePath(config.recordingsPath+ "recording.wav")
    #convert to format that is good for vxml as well as web interface
    subprocess.call(['/usr/bin/sox',path,'-r','8k','-c','1','-e','signed-integer',dest])
    #shutil.copy(path,dest)
    return dest

def findFreshFilePath(preferredPath):
    addition = 1
    path = re.sub(r"(.*\/)(\w*)(\.\w{3})",r"\1\2" + "_" + str(addition) + r"\3",preferredPath)
    while os.path.isfile(path):
        addition = addition + 1
        path = re.sub(r"(.*\/)(\w*)(\.\w{3})",r"\1\2" + "_" + str(addition) + r"\3",preferredPath)
    return path


@app.route('/rainfall-start.vxml',methods=['GET'])
def rainfallStart():
	interfaceAudioDir = 'static/audio/rainfallaudio/'
	communes = [['rainfall-location.vxml?commune=bassi',interfaceAudioDir + 'bassi.wav'],
			['rainfall-location.vxml?commune=tougo',interfaceAudioDir + 'tougo.wav'],
			['rainfall-location.vxml?commune=leba',interfaceAudioDir + 'leba.wav'],
			['rainfall-location.vxml?commune=gourcy',interfaceAudioDir + 'gourcy.wav'],
			['rainfall-location.vxml?commune=ziniare-oubritenga',interfaceAudioDir + 'ziniare-oubritenga.wav'],
			['rainfall-location.vxml?commune=ziniare-plateau',interfaceAudioDir + 'ziniare-plateau.wav']
]
	return render_template('menu.vxml',
		menuID = 'communemenu',
		interfaceAudioDir = interfaceAudioDir,
		questionAudio='welcome.wav',
		options = communes)


@app.route('/rainfall-location.vxml',methods=['GET'])
def rainfallSelectLocation():
	userSelectedCommune = request.args.get('commune')
	interfaceAudioDir = 'static/audio/rainfallaudio/'
	locations = {
			'bassi' :[
					['rainfall-days.vxml?location=bassi-lintiba',interfaceAudioDir + 'bassi-lintiba.wav'],
					['rainfall-days.vxml?location=bassi-ouetigue',interfaceAudioDir + 'bassi-ouetigue.wav'],
					['rainfall-days.vxml?location=bassi-kera-doure',interfaceAudioDir + 'bassi-kera-doure.wav'],
					['rainfall-days.vxml?location=bassi-saye',interfaceAudioDir + 'bassi-saye.wav'],
					['rainfall-days.vxml?location=bassi-guiri-guiri',interfaceAudioDir + 'bassi-guiri-guiri.wav']
				],
			'leba' :[
					['rainfall-days.vxml?location=leba-masbore',interfaceAudioDir + 'leba-masbore.wav'],
					['rainfall-days.vxml?location=leba-bouloulou',interfaceAudioDir + 'leba-bouloulou.wav']
				],
			'gourcy':[
					['rainfall-days.vxml?location=gourcy-secteur-4',interfaceAudioDir + 'gourcy-secteur-4.wav'],
					['rainfall-days.vxml?location=gourcy-danaoua',interfaceAudioDir + 'gourcy-danaoua.wav']
				],
			'ziniare-oubritenga':[
					['rainfall-days.vxml?location=ziniare-oubritenga-sawana',interfaceAudioDir + 'ziniare-oubritenga-sawana.wav']
				],
			'tougo' :[
					['rainfall-days.vxml?location=tougo-ridimbo',interfaceAudioDir + 'tougo-ridimbo.wav']
				],
			'ziniare-plateau':[
					['rainfall-days.vxml?location=ziniare-plateau-ziga',interfaceAudioDir + 'ziniare-plateau-ziga.wav']
				]	
			}
	locationOptions = locations[userSelectedCommune]
	
	return render_template('menu.vxml',
		menuID = 'locationmenu',
		interfaceAudioDir = interfaceAudioDir,
		questionAudio='select-region.wav',
		options = locationOptions)


@app.route('/rainfall-days.vxml',methods=['GET'])
def rainfallSelectDays():	
	userSelectedLocation = request.args.get('location')
	interfaceAudioDir = 'static/audio/rainfallaudio/'
	
	#make array for 1 to 9 days with redirect
	dayOptions = []
	for x in range(1,9):
		dayOptions.append(['rainfall.vxml?location=' + userSelectedLocation + '&amp;days=' + str(x) , 
					interfaceAudioDir + str(x) + '.wav', 
					interfaceAudioDir + 'days-ago.wav'])
		
	return render_template('menu.vxml',
		menuID = 'daysmenu',
		interfaceAudioDir = interfaceAudioDir,
		questionAudio='select-days.wav',
		options = dayOptions)


@app.route('/rainfall.vxml',methods=['GET'])
def rainfallPresentData():	
	userSelectedLocation = request.args.get('location')
	userSelectedDays = int(request.args.get('days'))
	interfaceAudioDir = 'static/audio/rainfallaudio/'
	
	#make array for 1 to x days with random data
	rainResults = []
	for x in range(0,userSelectedDays):

		#set random amount of rain, no greater than 25 (speech recording limited)
		amountOfRain = int(abs(random.normalvariate(0,6.5)))
		if amountOfRain > 25:
			amountOfRain = 25

		weekday = calendar.day_name[(date.today()-timedelta(x)).weekday()].lower()

		rainResults.extend([	interfaceAudioDir + userSelectedLocation + '.wav',
					interfaceAudioDir + 'it-was.wav',
					interfaceAudioDir + weekday + '.wav',
					interfaceAudioDir + str(x) + '.wav', 
					interfaceAudioDir + 'days-ago.wav',
					interfaceAudioDir + 'there-was.wav',
					interfaceAudioDir + str(amountOfRain) + '.wav',
					interfaceAudioDir + 'mmOfRain.wav'])
	#add ending message
	rainResults.extend([interfaceAudioDir + 'end.wav'])

	return render_template('message.vxml',
		interfaceAudioDir = interfaceAudioDir,
		messages = rainResults)


@app.route('/chickenvaccination.vxml',methods=['GET'])
def callerID():
    if 'callerid' in request.args:
        callerID = preProcessCallerID(request.args['callerid'])
        user = callerIDLookup(callerID)
        if len(user) != 0:
            preferredLanguage = preferredLanguageLookup(user)
            lang = LanguageVars(preferredLanguage.rsplit('_', 1)[-1])
            userVoiceLabel = lang.getVoiceLabel(user) 
            welcomeMessage = lang.getInterfaceAudioURL('welcome_cv.wav')
            return render_template('message.vxml',
                messages = [welcomeMessage,userVoiceLabel],
                redirect = "chickenvaccination_main.vxml?user=" + b16encode(user))
        else:
            return newUserVXML(callerID)
    else:
        return errorVXML()

def preProcessCallerID(callerID):
    """
    remove any spaces or plus signs from the callerID
    """
    processed = re.sub(r"(\s*\+*)(\d+)",r"\2",callerID)
    return processed



@app.route('/recordUserName.vxml',methods=['GET'])
def recordUserName():
    if 'callerid' not in request.args or 'lang' not in request.args: return errorVXML()
    lang = LanguageVars(b16decode(request.args['lang']))
    preMessages = [lang.getInterfaceAudioURL('speakUserName.wav'),
        lang.getInterfaceAudioURL('endRecordingWithAnyPress.wav')]
    postMessages = [lang.getInterfaceAudioURL('press1ToConfirm.wav'),
        lang.getInterfaceAudioURL('press2ToRetry.wav')]
    passOnVariables = [['callerid',request.args['callerid']],
        ['lang',request.args['lang']]]
    return render_template('record.vxml',
        preMessages = preMessages,
        postMessages = postMessages,
        passOnVariables = passOnVariables,
        redirect= 'insertNewUser.vxml')

@app.route('/insertNewUser.vxml',methods=['GET'])
def insertNewUserVXML():
    if 'callerid' not in request.args or 'lang' not in request.args or 'recording' not in request.args: return errorVXML()
    lang = LanguageVars(b16decode(request.args['lang']))
    callerID = b16decode(request.args['callerid'])
    recordingLocation = request.args['recording']
    recordingLocation = saveRecording(recordingLocation)
    newUserURI = insertNewUser(recordingLocation,callerID,str(lang))
    if len(newUserURI) != 0:
        messages = [lang.getInterfaceAudioURL('registerUserSuccess.wav')]
        return render_template('message.vxml',
            messages = messages,
            redirect = "chickenvaccination_main.vxml?user="+b16encode(newUserURI))
    else: return errorVXML()

def insertNewUser(recordingLocation,callerID,lang):
    objectType = "http://example.org/chickenvaccinationsapp/user"
    preferredURI = objectType
    recordingLocation = recordingLocation.replace(config.audioPath,config.audioURLbase)
    tuples = [["http://example.org/chickenvaccinationsapp/contact_fname","unknown"],
        ["http://example.org/chickenvaccinationsapp/contact_lname","unknown"],
        ["http://example.org/chickenvaccinationsapp/contact_tel",callerID],
        ["http://example.org/chickenvaccinationsapp/preferred_language",lang],
        [lang,recordingLocation]]
    return sparqlHelper.insertObjectTriples(preferredURI,objectType,tuples)

def callerIDLookup(callerID):
    """
    Returns the URI of the user associated with the caller ID. Returns an empty string if no match.
    """
    callerID = callerID.replace(" ","+")
    field = ['userURI']
    triples = [['?userURI','http://www.w3.org/1999/02/22-rdf-syntax-ns#type','http://example.org/chickenvaccinationsapp/user'],
    ['?userURI','http://example.org/chickenvaccinationsapp/contact_tel',callerID]]
    result = sparqlInterface.selectTriples(field,triples)
    if len(result) == 0: return ""
    else: return result[0][0]
    
@app.route('/error.vxml')
def errorVXML(language="en"):
    lang = LanguageVars(language)
    return render_template('message.vxml',
        messages = [lang.audioInterfaceURL + 'error.wav'],
            redirect = 'error.vxml')



@app.route('/static/<path:path>')
def send_static(path):
        return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=config.debug)
