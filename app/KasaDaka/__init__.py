from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
from sparqlInterface import executeSparqlQuery, executeSparqlUpdate
import sparqlInterface
from datetime import datetime,date
from werkzeug import secure_filename
from languageVars import LanguageVars, getVoiceLabels
import sparqlHelper
import languageVars
import callhelper
import subprocess
import shutil
import glob
import re
import urllib
import copy
import os.path
import os
import random
from base64 import b16encode , b16decode
from admin import admin


app = Flask(__name__, instance_relative_config=True)
app.config.from_object('config')
app.config.from_pyfile('config.py')
app.secret_key = 'asdfbjarbja;kfbejkfbasjkfbslhjvbhcxgxui328'

app.config['UPLOAD_FOLDER'] = app.config['AUDIOPATH']

app.register_blueprint(admin, url_prefix='/admin')

@app.route('/')
def index():
    """ Index page
	Only used to confirm hosting is working correctly
	"""
    return 'This is the Kasadaka Vxml generator'

@app.route('/outgoing')
def createOutgoingCalls():
    """Creates an random outgoing reminder call.
    Respects the times as set in the config"""
    if not insideOfOutgoingCallsHours():
        return datetime.now().isoformat() + " Outside of outgoing call hours"
    users = sparqlHelper.objectList("http://example.org/chickenvaccinationsapp/user")
    usersWithReminders = getUsersWithReminders(users)
    #choose a random user from the users with reminders (this is to prevent having multiple outgoing calls at once)
    if len(usersWithReminders) >0:
        randomChosenUser = random.choice(usersWithReminders)
        placeResult = placeOutgoingReminderCall(randomChosenUser)
        return placeResult + " Users with reminders left (out of total users):" + str(len(usersWithReminders)) +"/"+str(len(users))
    else:
        return datetime.now().isoformat() + " No users with reminders (left)"

def placeOutgoingReminderCall(userURI):
    #TODO genereer een uitgaande call naar het nummer van de user:
    userNumber = getUserTelNumber(userURI)
    vxmlURL = "http://127.0.0.1/FlaskKasadaka/reminder.vxml?user=" + b16encode(userURI)
    if validTelNumber(userNumber):
        userNumber = "+" + userNumber

        callhelper.placeCall(userNumber,vxmlURL)
        return datetime.now().isoformat() +" Placed outgoing call to: " + userURI + " (" + userNumber + ") URL: " + vxmlURL
    #"reminder.vxml?user=" + b16encode(userURI)
    else: return  "invalid user telephone number"

def validTelNumber(number):
    return number.isdigit()


def getUserTelNumber(userURI):
    """
    Returns the telephone number of the specified user.
    """
    field = ['tel']
    triples = [[userURI,'http://www.w3.org/1999/02/22-rdf-syntax-ns#type','http://example.org/chickenvaccinationsapp/user'],
    [userURI,'http://example.org/chickenvaccinationsapp/contact_tel','?tel']]
    result = sparqlInterface.selectTriples(field,triples)
    if len(result) == 0: return ""
    else: return result[0][0]

def insideOfOutgoingCallsHours():
    currentHour = datetime.now().hour
    return currentHour > config.reminderCallHours[0] and currentHour < config.reminderCallHours[1]


def getUsersWithReminders(users):
    usersWithReminders = []
    for user in users:
        reminders = lookupVaccinationReminders(user[0])
        if len(reminders) > 0:
            if not checkIfReminderAlreadySent(user[0]):
                usersWithReminders.append(user[0])
    return usersWithReminders

def checkIfReminderAlreadySent(userURI):
    """Returns whether the user already received reminders today, or has been called in the last couple of hours"""
    pastReminders = getPastReminders(userURI)
    for reminder in pastReminders:
        reminderDateTime = datetime.strptime(reminder[2], "%Y-%m-%dT%H:%M:%S.%f")
        reminderDate = reminderDateTime.date()
        currentDateTime = datetime.now()
        currentDate = currentDateTime.date()
        if int((currentDate - reminderDate).days) == 0:
            if reminder[3] == 'True':
                return True
            if int((currentDateTime - reminderDateTime).seconds) // 3600 < 3:
                return True
    return False



def getPastReminders(userURI):
    """Gets all past reminders sent to an user"""
    reminders = sparqlHelper.objectList('http://example.org/chickenvaccinationsapp/outgoing_reminder')
    result = []
    for reminder in reminders:
        if reminder[1] == userURI:
            result.append(reminder)
    return result


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
            if int(vaccinationDays) == int((currentDate - birthDate).days):
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


@app.route('/reminder.vxml',methods=['GET'])
def reminderVXML():
    if 'user' not in request.args: return errorVXML(error="No user defined to look up reminders")
    user = b16decode(request.args['user'])
    if 'action' in request.args and request.args['action'] == 'received':
        return markReminderResult(user,True)
    if 'action' in request.args and request.args['action'] == 'failed':
        return markReminderResult(user,False)
    return generateReminderMessage(user)

def markReminderResult(userURI,received):
    lang = LanguageVars(preferredLanguageLookup(userURI))
    receivedURI = "http://example.org/chickenvaccinationsapp/reminder"
    objectType = 'http://example.org/chickenvaccinationsapp/outgoing_reminder'
    tuples = [['http://example.org/chickenvaccinationsapp/user',userURI],['http://example.org/chickenvaccinationsapp/date',str(datetime.now().isoformat())],['http://example.org/chickenvaccinationsapp/received',str(received)]]
    success = sparqlHelper.insertObjectTriples(receivedURI,objectType,tuples)
    messages = [lang.getInterfaceAudioURL('userDidNotConfirm.wav')]
    if received: messages = [lang.getInterfaceAudioURL('reminderMarkedReceived.wav'),lang.getInterfaceAudioURL('thanks.wav')]
    return render_template('message.vxml',
        messages = messages)

def generateReminderMessage(userURI):
    lang = LanguageVars(preferredLanguageLookup(userURI))
    batchVaccinations = lookupVaccinationReminders(userURI)
    welcomeMessage = lang.getInterfaceAudioURL('welcome_cv.wav')
    userVoiceLabel = lang.getVoiceLabel(userURI)
    messages = [welcomeMessage,userVoiceLabel]
    reminders = []
    if len(batchVaccinations) == 0:
        messages.append(lang.getInterfaceAudioURL('currentlyNoVaccinationsNeeded.wav'))
    else:
        messages.append(lang.getInterfaceAudioURL('reminderIntro.wav'))
        for batchVaccination in batchVaccinations:
            batchVoicelabel = lang.getVoiceLabel(batchVaccination[0])
            vaccinationVoicelabel = lang.getVoiceLabel(batchVaccination[1])
            diseaseVoicelabel = lang.getVoiceLabel(batchVaccination[2])
            if len(batchVoicelabel) == 0 or len(vaccinationVoicelabel) == 0 or len(diseaseVoicelabel) == 0:
                return errorVXML(error="Voicelabel does not exist: " + str(batchVaccination))
            reminder = [lang.getInterfaceAudioURL('for.wav'),batchVoicelabel,lang.getInterfaceAudioURL('toPreventDisease.wav'),diseaseVoicelabel,lang.getInterfaceAudioURL('useVaccination.wav'),vaccinationVoicelabel,lang.getInterfaceAudioURL('press1ToConfirm.wav')]
            reminders.append(reminder)
    return render_template('reminder.vxml',
        messages = messages,
        reminders=reminders,
        userURI = b16encode(userURI))
    #return messages



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
def errorVXML(error="undefined error",language="en"):
    lang = LanguageVars(language)
    return render_template('message.vxml',
        messages = [lang.audioInterfaceURL + 'error.wav'],
            redirect = '',
            error=error)

@app.route('/static/<path:path>')
def send_static(path):
        return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=app.config['DEBUG'])
