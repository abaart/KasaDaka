from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
from sparqlInterface import executeSparqlQuery, executeSparqlUpdate
import sparqlInterface
from datetime import datetime,date
from werkzeug import secure_filename
import config
from languageVars import LanguageVars, getVoiceLabels
import sparqlHelper
import languageVars

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

@app.route('/admin/reminders')
def showReminders():
    if 'uri' in request.args: userURI = request.args['uri']
    else: userURI = ""
    users = executeSparqlQuery("""SELECT DISTINCT ?subject    WHERE {
       ?subject rdf:type   cv:user .
        }""")
    if len(userURI) != 0: 
        messages = generateReminderMessage(userURI)
        reminder = concatenateWavs(messages)
        reminderURL = reminder.replace(config.audioPath,config.audioURLbase)
    else:
        reminderURL = ""
    return render_template('admin/reminder.html',
        reminderURL = reminderURL,
        users = users,
        uri = userURI)

@app.route('/admin/audio', methods=['GET','POST'])
def adminAudio():
    if 'lang' in request.args and 'uri' in request.args:
        return recordAudio(request.args['lang'],request.args['uri'])
    elif 'lang' in request.args:
        return recordAudio(request.args['lang'])
    elif request.method == 'POST' and request.form['action'] == 'upload':
        return processAudio(request)
    else:
        return adminAudioHome()


def adminAudioHome():
    getLanguagesQuery = """SELECT DISTINCT  ?voicelabel  WHERE {
          ?voicelabel   rdfs:subPropertyOf speakle:voicelabel.}"""
    languages = executeSparqlQuery(getLanguagesQuery)
    for language in languages:
        getNumberMissingVoicelabelsQuery = """SELECT DISTINCT ?subject    WHERE {
       ?subject rdf:type   ?type .
        FILTER(NOT EXISTS {?subject <"""+language[0]+"""> ?voicelabel_en .})
        }"""
        missingVoicelabels=executeSparqlQuery(getNumberMissingVoicelabelsQuery)
        language.append(len(missingVoicelabels))
    getAllResourcesQuery = """SELECT DISTINCT ?subject  WHERE {
    ?subject rdf:type   ?type .}"""
    sparqlResources = executeSparqlQuery(getAllResourcesQuery)
    sparqlNonExistingWaveFiles = []
    for resource in sparqlResources:
        voiceLabels = getVoiceLabels(resource[0],returnEmptyVoiceLabels=False)
        for audioFile in voiceLabels:
            url = audioFile[1]
            if not urllib.urlopen(url).getcode() == 200:
                sparqlNonExistingWaveFiles.append(audioFile[1])
    sparqlNonExistingWaveFiles = sorted(set(sparqlNonExistingWaveFiles))

    finalResultsInterface = []
    pythonFiles = glob.glob(config.pythonFilesDir+'*.py')
    pythonFiles.extend(glob.glob(config.pythonFilesDir+'templates/*.html'))
    pythonFiles.extend(glob.glob(config.pythonFilesDir+'templates/*.vxml'))
    pythonFiles.extend(glob.glob(config.pythonFilesDir+'templates/admin/*.html'))
    waveFilesInterface = []
    wavFilePattern = re.compile("""([^\s\\/+"']+\.wav)""",re.I)
    for pythonFile in pythonFiles:
        text = open(pythonFile).read()
        for match in wavFilePattern.findall(text):
            #ignore match on regex above
            if match != "\.wav":
                waveFilesInterface.append(match)
    #remove duplicates
    waveFilesInterface.extend(['1.wav','2.wav','3.wav','4.wav','5.wav','6.wav','7.wav','8.wav','9.wav','0.wav','hash.wav','star.wav'])
    waveFilesInterface = sorted(set(waveFilesInterface))
    nonExistingInterfaceWaveFiles = []
    for language in languages:
        lang = LanguageVars(language[0])
        for waveFile in waveFilesInterface:
            waveFileURL = lang.getInterfaceAudioURL(waveFile)
            if not urllib.urlopen(waveFileURL).getcode() == 200:
                nonExistingInterfaceWaveFiles.append(waveFileURL)
    nonExistingInterfaceWaveFiles = sorted(set(nonExistingInterfaceWaveFiles))


    return render_template('admin/audio.html',
        languages = languages,
        notAvailableWaveFiles = sparqlNonExistingWaveFiles,
        waveFilesInterface=nonExistingInterfaceWaveFiles)

def recordAudio(language,URI = ""):
    getResourcesMissingVoicelabelQuery = """SELECT DISTINCT ?subject    WHERE {
       ?subject rdf:type   ?type .
        FILTER(NOT EXISTS {?subject <"""+language+"""> ?voicelabel_en .})
        }"""
    resourcesMissingVoicelabels = executeSparqlQuery(getResourcesMissingVoicelabelQuery)
    if len(URI) == 0: URI = resourcesMissingVoicelabels[0][0]
    resourceDataQuery = """SELECT DISTINCT  ?1 ?2  WHERE {
          ?uri   ?1 ?2.
         FILTER(?uri=<"""+URI+""">)}"""
    proposedWavURL = config.audioPath + URI.rsplit('/', 1)[-1] + "_"+language.rsplit('/', 1)[-1] +".wav"

    resourceData = executeSparqlQuery(resourceDataQuery,httpEncode=False)
    languageLabel = sparqlHelper.retrieveLabel(language)
    voiceLabelResults = getVoiceLabels(URI,changeLocalhostIP = request.host)
    return render_template('admin/record.html',uri=URI,data=resourceData,proposedWavURL=proposedWavURL,language=language.rsplit('/', 1)[-1],langURI=language,resourcesMissingVoicelabels=resourcesMissingVoicelabels, languageLabel=languageLabel,voiceLabelResults=voiceLabelResults)

def processAudio(request):
    fileExists = os.path.isfile(request.form['filename'])
    file = request.files['file']
    #if file and allowed_file(file.filename):
        #filename = secure_filename(file.filename)
        #file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    tempFileLocation = "/tmp/"+request.form['filename'].rsplit('/', 1)[-1]
    file.save(tempFileLocation)
    size = os.stat(tempFileLocation).st_size
    subprocess.call(['/usr/bin/sox',tempFileLocation,'-r','8k','-c','1','-e','signed-integer',request.form['filename']])
    if size > 0: flash('File saved successfully! bytes:'+str(size))
    else:
        flash("Error: file "+str(size)+" bytes.")
        return recordAudio(request.form['lang'])

    URL = config.audioURLbase + request.form['filename'].rsplit('/', 1)[-1]
    insertVoicelabelQuery = """INSERT DATA {
    <"""+ request.form['uri'] + """> <"""+ request.form['lang'] +"""> <""" + URL + """>.
    }"""
    insertSuccess = executeSparqlUpdate(insertVoicelabelQuery)
    if insertSuccess: flash("Voicelabel sucessfully inserted in to triple store!")
    else: flash("Error in inserting triples")
    return recordAudio(request.form['lang'],request.form['uri'])


@app.route('/admin')
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
    return render_template(
        'admin/object.html',
        data = result, 
        fieldNames = fieldNames, 
        uri = URI,
        voiceLabelResults = voiceLabels,
        objectTypeLabel=objectTypeLabel)

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

@app.route('/declareBornChickenBatch.vxml',methods=['GET'])
def cvNewChickenBatchVXML():
    if 'user' not in request.args: return errorVXML()
    user = b16decode(request.args['user'])
    lang = LanguageVars(preferredLanguageLookup(user))
    preMessages = [lang.getInterfaceAudioURL('speakChickenBatchName.wav'),
        lang.getInterfaceAudioURL('endRecordingWithAnyPress.wav')]
    postMessages = [lang.getInterfaceAudioURL('press1ToConfirm.wav'),
        lang.getInterfaceAudioURL('press2ToRetry.wav')]
    passOnVariables = [['user',request.args['user']]]
    return render_template('record.vxml',
        preMessages = preMessages,
        postMessages = postMessages,
        passOnVariables = passOnVariables,
        redirect= 'insertBornChickenBatch.vxml')

@app.route('/insertBornChickenBatch.vxml',methods=['GET'])
def cvInsertNewChickenBatchVXML():
    if 'user' not in request.args or 'recording' not in request.args: return errorVXML()
    user = b16decode(request.args['user'])
    lang = LanguageVars(preferredLanguageLookup(user))
    recordingLocation = request.args['recording']
    recordingLocation = saveRecording(recordingLocation)
    success = insertNewChickenBatch(recordingLocation,user)
    if success:
        messages = [lang.getInterfaceAudioURL('insertChickenBatchSuccess.wav')]
        return render_template('message.vxml',
            messages = messages,
            redirect = "chickenvaccination_main.vxml?user="+request.args['user'])
    else: return errorVXML()

def insertNewChickenBatch(recordingLocation,user):
    voicelabelLanguage = preferredLanguageLookup(user)
    objectType =  "http://example.org/chickenvaccinationsapp/chicken_batch"
    preferredURI = objectType
    currentDate = date.today().strftime(config.dateFormat)
    recordingLocation = recordingLocation.replace(config.audioPath,config.audioURLbase)
    tuples = [["http://example.org/chickenvaccinationsapp/birth_date",currentDate],
        ["http://example.org/chickenvaccinationsapp/owned_by",user],
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



@app.route('/chickenvaccination_main.vxml',methods=['GET'])
def cvMainMenuVXML():
    if 'user' not in request.args: return errorVXML()
    user = b16decode(request.args['user'])
    lang = LanguageVars(preferredLanguageLookup(user))
    #list of options in initial menu: link to file, and audio description of the choice
    options = [
            ['declareBornChickenBatch.vxml?user='+request.args['user'],lang.getInterfaceAudioURL('declareBornChickenBatch.wav')]
            ]
    return render_template(
        'main.vxml',
        interfaceAudioDir = lang.audioInterfaceURL,
        welcomeAudio = 'welcomeMainMenu.wav',
        questionAudio = "mainMenuQuestion.wav",
        options = options)

@app.route('/reminder.vxml',methods=['GET'])
def reminderVXML():
    if 'user' not in request.args: return errorVXML()
    user = b16decode(request.args['user'])
    return str(generateReminderWav(generateReminderMessage(user)))
    return str(generateReminderMessage(user))

def concatenateWavs(messages):
    path = config.recordingsPath + "reminder.wav"
    path = findFreshFilePath(path)
    wavs = []
    for wav in messages:
        wavs.append(wav.replace(config.audioURLbase,config.audioPath))
    command = ['/usr/bin/sox']
    command.extend(wavs)
    command.append(path)
    #command.extend(['-r','8k','-c','1','-e','signed-integer',path])
    subprocess.call(command)
    flash(" ".join(messages))
    return path

def generateReminderMessage(userURI):
    lang = LanguageVars(preferredLanguageLookup(userURI))

    #TODO look up actual chicken batches that need a reminder today
    batchVaccinations = lookupVaccinationReminders(userURI)

    welcomeMessage = lang.getInterfaceAudioURL('welcome_cv.wav')
    userVoiceLabel = lang.getVoiceLabel(userURI) 
    messages = [welcomeMessage,userVoiceLabel]
    if len(batchVaccinations) == 0:
        messages.append(lang.getInterfaceAudioURL('currentlyNoVaccinationsNeeded.wav'))
    else:
        messages.append(lang.getInterfaceAudioURL('reminderIntro.wav'))
        for batchVaccination in batchVaccinations:
            batchVoicelabel = lang.getVoiceLabel(batchVaccination[0])
            vaccinationVoicelabel = lang.getVoiceLabel(batchVaccination[1])
            diseaseVoicelabel = lang.getVoiceLabel(batchVaccination[2])
            if len(batchVoicelabel) == 0 or len(vaccinationVoicelabel) == 0 or len(diseaseVoicelabel) == 0: 
                flash('unable to create reminder, voicelabel not defined!')
                return []
            messages.extend([lang.getInterfaceAudioURL('for.wav'),batchVoicelabel,lang.getInterfaceAudioURL('toPreventDisease.wav'),diseaseVoicelabel,lang.getInterfaceAudioURL('useVaccination.wav'),vaccinationVoicelabel])
    #return render_template('message.vxml',
    #    messages = messages,
    #    redirect = 'chickenvaccination_main.vxml?user=' + b16encode(userURI))
    return messages


def lookupVaccinationReminders(userURI):
    """
    Returns an array of triples (chicken batch URI, vaccination URI,disease URI)
    Of the vaccination needed for an user's chicken batches
    """
    date_format = config.dateFormat
    chickenBatches = lookupChickenBatches(userURI,giveBirthDates = True)
    vaccinations = lookupVaccinations()
    results = []
    for chickenBatch in chickenBatches:
        birthDate = datetime.strptime(chickenBatch[1],date_format)
        currentDate = datetime.now()
        for index, vaccination in enumerate(vaccinations):
            vaccinationDays = vaccination[1]
            if vaccinationDays == (currentDate - birthDate).days or index == 0:
                results.append([chickenBatch[0],vaccination[0],vaccination[3]])
    return results

def lookupVaccinations():
    """
    Returns array of vaccinations, with properties in order as in second argument of objectList call.
    """
    return sparqlHelper.objectList('http://example.org/chickenvaccinationsapp/vaccination',['http://example.org/chickenvaccinationsapp/days_after_birth','http://example.org/chickenvaccinationsapp/description','http://example.org/chickenvaccinationsapp/treats'])

def lookupChickenBatches(userURI,giveBirthDates = False):
    """
    Returns an array of chicken batches belonging to an user.
    """
    field = ['chicken_batch']
    triples = [['?userURI','http://www.w3.org/1999/02/22-rdf-syntax-ns#type','http://example.org/chickenvaccinationsapp/user'],
    ['?chicken_batch','http://example.org/chickenvaccinationsapp/owned_by','?userURI']]
    filter = ['userURI',userURI]
    if giveBirthDates:
        field.append('birth_date')
        triples.append(['?chicken_batch','http://example.org/chickenvaccinationsapp/birth_date','?birth_date'])
    return sparqlInterface.selectTriples(field,triples,filter)




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

#TODO tidying
def askLanguageVXML(redirect,passOnVariables):
    languages = languageVars.getVoiceLabelPossibilities()
    for language in languages:
        language.append(config.audioURLbase + language[0].rsplit('_', 1)[-1] + "/interface/" + language[0].rsplit('/', 1)[-1] + ".wav")
        language.append(language[0].rsplit('_', 1)[-1])
        language[0] = b16encode(language[0])
    return render_template(
    'language.vxml',
    options = languages,
    audioDir = config.audioURLbase,
    questionAudio = config.audioURLbase+config.defaultLanguage+"/interface/chooseLanguage.wav",
    passOnVariables = passOnVariables,
    redirect = redirect
    )

def newUserVXML(callerID,lang=""):
    if len(callerID) == 0 : return errorVXML()
    if len(lang) == 0: return askLanguageVXML('recordUserName.vxml',[['callerid',b16encode(callerID)]])
    lang = LanguageVars(lang)
    preMessages = [lang.getInterfaceAudioURL('speakUserName.wav'),
        lang.getInterfaceAudioURL('endRecordingWithAnyPress.wav')]
    postMessages = [lang.getInterfaceAudioURL('press1ToConfirm.wav'),
        lang.getInterfaceAudioURL('press2ToRetry.wav')]
    passOnVariables = [['callerid',callerID],['lang', lang]]
    return render_template('record.vxml',
        preMessages = preMessages,
        postMessages = postMessages,
        passOnVariables = passOnVariables,
        redirect= 'recordUserName.vxml')

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

def preferredLanguageLookup(userURI):
    """
    Returns the URI of the preferred voicelabel (language) for an user.
    """
    field = ['preferred_language']
    triples = [['?userURI','http://www.w3.org/1999/02/22-rdf-syntax-ns#type','http://example.org/chickenvaccinationsapp/user'],
    ['?userURI','http://example.org/chickenvaccinationsapp/preferred_language','?preferred_language']]
    filter = ['userURI',userURI]
    result = sparqlInterface.selectTriples(field,triples,filter)
    if len(result) == 0: return config.defaultLanguageURI
    else: return result[0][0]

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


if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=config.debug)
