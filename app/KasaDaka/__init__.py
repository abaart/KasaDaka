from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, send_from_directory, current_app
#with current_app.app_context():
#from sparqlInterface import executeSparqlQuery, executeSparqlUpdate
import sparqlInterface
from datetime import datetime,date
from werkzeug import secure_filename
#from languageVars import LanguageVars, getVoiceLabels
#import sparqlHelper
#import languageVars
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

#import blueprints
from admin import admin
from voice import voice


app = Flask(__name__, instance_relative_config=True)
app.config.from_object('config')
app.config.from_pyfile('config.py')
app.secret_key = 'asdfbjarbja;kfbejkfbasjkfbslhjvbhcxgxui328'
app.config['UPLOAD_FOLDER'] = app.config['AUDIOPATH']
app.register_blueprint(admin, url_prefix='/admin')
app.register_blueprint(voice, url_prefix='/voice')


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
    return currentHour > app.config['REMINDERCALLHOURS'][0] and currentHour < app.config['REMINDERCALLHOURS'][1]


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



@app.route('/static/<path:path>')
def send_static(path):
        return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=app.config['DEBUG'])
