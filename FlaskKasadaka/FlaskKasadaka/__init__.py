

from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
from sparqlInterface import executeSparqlQuery, executeSparqlUpdate
from datetime import datetime
import config
import glob
import re
import urllib

app = Flask(__name__)
@app.route('/')
def index():
    """ Index page
	Only used to confirm hosting is working correctly
	"""
    return 'This is the Kasadaka Vxml generator'

@app.route('/admin/user.html', methods=['GET','POST'])
def user():
   # if request.args['update'] == 'yes':
    if 'update' in request.form:
        if request.form['update'] == 'yes':
             return 'yes!!'
    elif 'user' in request.args:
        #list information of a user
        userInfoQuery = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
        PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
        PREFIX lexvo: <http://lexvo.org/ontology#>
        PREFIX cv: <http://example.org/chickenvaccinationsapp/>
        SELECT DISTINCT   ?fname  ?lname ?tel  ?pl ?vl_en WHERE {
                  <"""+request.args['user']+"""> rdf:type cv:user .
                    ?user cv:contact_fname ?fname .
                    ?user cv:contact_lname ?lname .
                    ?user cv:contact_tel ?tel .
                    ?user cv:preferred_language ?pl .
                    ?user speakle:voicelabel_en ?vl_en .
                    }"""
        #TODO add support for voicelabels of all installed languages
        
        fieldNames=['First name','Last name','Tel. no.','Preferred language','English Voicelabel']

        result = executeSparqlQuery(userInfoQuery,giveColumns=True)
        return render_template('admin/user.html',user = result, fieldNames = fieldNames, uri = request.args['user'])
    else:
        return "Error: no user defined."


@app.route('/admin/listusers.html')
def listusers():
    #list all users in the system
    getUsersQuery = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
                PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
                    PREFIX lexvo: <http://lexvo.org/ontology#>
                        PREFIX cv: <http://example.org/chickenvaccinationsapp/>
                        
                            SELECT DISTINCT  ?user ?fname  ?lname ?tel WHERE {
                                              ?user rdf:type cv:user .
                                                 ?user cv:contact_fname ?fname .                                                           ?user cv:contact_lname ?lname .
                                                           ?user cv:contact_tel ?tel .
                                                                             }"""
    outputGetUsersQuery = executeSparqlQuery(getUsersQuery)
    return render_template('admin/listusers.html',users=outputGetUsersQuery)


@app.route('/main.vxml')
def main():
    if 'lang' in request.args:
        lang = config.LanguageVars(request.args)
        #list of options in initial menu: link to file, and audio description of the choice
        options = [
                ['requestProductOfferings.vxml?lang='+lang.language,    lang.audioInterfaceURL+'requestProductOfferings.wav'],
                ['placeProductOffer.vxml?lang='+lang.language,   lang.audioInterfaceURL+'placeProductOffer.wav']
                ]


        return render_template(
        'main.vxml',
        interfaceAudioDir = lang.audioInterfaceURL,
        welcomeAudio = 'welcome.wav',
        questionAudio = "mainMenuQuestion.wav",
        options = options)
    else:
        #give your language
        languagesQuery = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
        PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
        PREFIX lexvo: <http://lexvo.org/ontology#>

        SELECT DISTINCT  ?voicelabel  WHERE {
              ?voicelabel   rdfs:subPropertyOf speakle:voicelabel.

        }"""
        languages = executeSparqlQuery(languagesQuery)
        for language in languages:
            language.append(config.audioURLbase + language[0].rsplit('_', 1)[-1] + "/interface/" + language[0].rsplit('/', 1)[-1] + ".wav")
            language.append(language[0].rsplit('_', 1)[-1])
            language[0] = "main.vxml?lang=" + language[0].rsplit('_', 1)[-1]


        return render_template(
        'language.vxml',
        options = languages,
        audioDir = config.audioURLbase,
        questionAudio = config.audioURLbase+config.defaultLanguage+"/interface/chooseLanguage.wav"

        )


@app.route('/requestProductOfferings.vxml')
def requestProductOfferings():
    #process the language
    lang = config.LanguageVars(request.args)

    #if the chosen product has been entered, show results
    if 'product' in request.args:
        choice = request.args['product']

        query = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
        PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
        SELECT DISTINCT  ?quantity_voicelabel ?contact_voicelabel ?price_voicelabel ?currency_voicelabel WHERE {
        #get offers of selected product
        ?offering rdf:type	radiomarche:Offering.
        ?offering radiomarche:prod_name <"""+choice+ """>.

        #get contact
        ?offering radiomarche:has_contact ?contact.
        ?contact speakle:voicelabel_en ?contact_voicelabel.
        #get quantity
        ?offering radiomarche:quantity ?quantity.
        ?quantity speakle:voicelabel_en ?quantity_voicelabel.

        #get price
        ?offering radiomarche:price ?price.
        ?price speakle:voicelabel_en ?price_voicelabel.

        #get currency
        ?offering radiomarche:currency ?currency.
        ?currency speakle:voicelabel_en ?currency_voicelabel
        }"""
        query = lang.replaceVoicelabels(query)

        results = executeSparqlQuery(query)

        return render_template(
            'result.vxml',
            interfaceAudioDir = lang.audioInterfaceURL,
            messageAudio = 'presentProductOfferings.wav',
            redirect = 'main.vxml?lang='+lang.language,
            results = results)


    #if no choice was made, offer choices of products to get offerings from
    query = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
    PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
    SELECT DISTINCT ?product ?voicelabel_en  WHERE {
    ?product rdf:type	radiomarche:Product.
    ?product speakle:voicelabel_en ?voicelabel_en
    }"""
    query = lang.replaceVoicelabels(query)
    choices = executeSparqlQuery(query)
    #add the url of this page to the links, so the user gets the results
    #also keep the language
    for choice in choices:
        choice[0] = 'requestProductOfferings.vxml?lang='+lang.language+'&amp;product=' + choice[0]

    return render_template(
    'menu.vxml',
    options = choices,
    interfaceAudioDir = lang.audioInterfaceURL,
    questionAudio = "chooseYourProduct.wav"
    )

@app.route('/placeProductOffer.vxml')
def placeProductOffer():
#for this function, a lot of things are defined in the template 'placeProductOffer.vxml'. You will need to edit this file as well.
    #process the language

    lang = config.LanguageVars(request.args)

    #if all the nessecary variables are set, update data in store
    if 'user' in request.args and 'product' in request.args and 'location' in request.args and 'price' in request.args and 'currency' in request.args and 'quantity' in request.args:
        user = request.args['user']
        product = request.args['product']
        location = request.args['location']
        price = request.args['price']
        currency = request.args['currency']
        quantity = request.args['quantity']


        #determine next number for offering (add to the already existing offerings)
        allOfferings = executeSparqlQuery("""PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
        PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
        SELECT DISTINCT ?offering   WHERE {
        ?offering rdf:type	radiomarche:Offering.
        }""")
        highestCurrentOfferingNumber = 0
        for offering in allOfferings:
            #check the highest current offering in database
            if int(offering[0].rsplit('_', 1)[-1]) > highestCurrentOfferingNumber:
                highestCurrentOfferingNumber = int(offering[0].rsplit('_', 1)[-1])
        dateTime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        #TODO confirm eerst doen
        offeringNumber = str(highestCurrentOfferingNumber + 1)
        insertQuery = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
            PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
        	INSERT  DATA
        { radiomarche:offering_xxxxx rdf:type  <http://purl.org/collections/w4ra/radiomarche/Offering> .
        radiomarche:offering_xxxxx radiomarche:currency  <"""+ currency +"""> .
        radiomarche:offering_xxxxx radiomarche:has_contact  <"""+ user +"""> .
        radiomarche:offering_xxxxx radiomarche:price  <http://purl.org/collections/w4ra/radiomarche/price-"""+ price +"""> .
        radiomarche:offering_xxxxx radiomarche:prod_name  <"""+ product +"""> .
        radiomarche:offering_xxxxx radiomarche:quantity  <http://purl.org/collections/w4ra/radiomarche/quantity-"""+ quantity +"""> .
        radiomarche:offering_xxxxx radiomarche:ts_date_entered  '"""+ dateTime +"""' .
        radiomarche:offering_xxxxx radiomarche:zone <"""+ location +"""> .
        }"""
        insertQuery = insertQuery.replace("offering_xxxxx","offering_"+offeringNumber)
        result = executeSparqlUpdate(insertQuery)
        #TODO doe een message dat alles gelukt is en terug naar main menu
        if result:
            return render_template(
                'message.vxml',
                redirect ="main.vxml?lang=" + lang.language,
                messageAudio = 'placeProductOffer_success.wav',
                interfaceAudioDir = lang.audioInterfaceURL)
        else:
            return render_template(
                'message.vxml',
                redirect ="main.vxml?lang=" + lang.language,
                messageAudio = 'error.wav',
                interfaceAudioDir = lang.audioInterfaceURL)


    #if no choice was made, present choice menu
    userChoices = executeSparqlQuery(
        """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
        PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
        SELECT DISTINCT ?person ?voicelabel_en  WHERE {
                 ?person  rdf:type radiomarche:Person  .
                 ?person radiomarche:contact_fname ?fname .
                 ?person radiomarche:contact_lname ?lname.
                 ?person speakle:voicelabel_en ?voicelabel_en
        }""")

    productChoices = executeSparqlQuery(
            """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
            PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
            SELECT DISTINCT ?product ?voicelabel_en  WHERE {
            ?product rdf:type	radiomarche:Product.
            ?product speakle:voicelabel_en ?voicelabel_en
            }""")
    locationChoices = executeSparqlQuery(
            """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
    PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
    SELECT DISTINCT ?zone ?voicelabel  WHERE {
    ?zone rdf:type	radiomarche:Zone.
	?zone speakle:voicelabel_en ?voicelabel
    }""")
    currencyChoices = executeSparqlQuery(
            """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
    PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
    SELECT DISTINCT ?currency ?voicelabel  WHERE {
    ?currency rdf:type	radiomarche:Currency.
	?currency speakle:voicelabel_en ?voicelabel
    }""")

    return render_template(
    'placeProductOffer.vxml',
    personOptions = userChoices,
    personQuestionAudio = "placeProductOffer_person.wav",
    productOptions = productChoices,
    productQuestionAudio = "placeProductOffer_product.wav",
    locationOptions = locationChoices,
    locationQuestionAudio = "placeProductOffer_location.wav",
    currencyOptions = currencyChoices,
    currencyQuestionAudio = "placeProductOffer_currency.wav",
    quantityQuestionAudio = "placeProductOffer_quantity.wav",
    priceQuestionAudio = "placeProductOffer_price.wav",
    interfaceAudioDir = lang.audioInterfaceURL,
    language = lang.language
    )


@app.route('/audioreferences.html')
def audioReferences():
    finalResultsInterface = []
    finalResultsSparql = []
    pythonFiles = glob.glob(config.pythonFilesDir+'*.py')
    pythonFiles.extend(glob.glob(config.pythonFilesDir+'templates/*'))
    resultsInterface = []
    wavFilePattern = re.compile("""([^\s\\/+"']+\.wav)""",re.I)
    for pythonFile in pythonFiles:
        text = open(pythonFile).read()
        for match in wavFilePattern.findall(text):
            #ignore match on regex above
            if match != "\.wav":
                resultsInterface.append(match)
    #remove duplicates
    resultsInterface.extend(['1.wav','2.wav','3.wav','4.wav','5.wav','6.wav','7.wav','8.wav','9.wav','0.wav','hash.wav','star.wav'])


    languages = []
    getLanguagesQuery = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
    PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
    PREFIX lexvo: <http://lexvo.org/ontology#>

    SELECT DISTINCT  ?voicelabel  WHERE {
          ?voicelabel   rdfs:subPropertyOf speakle:voicelabel.



    }"""
    outputGetLanguagesQuery = executeSparqlQuery(getLanguagesQuery)
    #get the language code behind the last slash
    for string in outputGetLanguagesQuery:
        #also add the language itself to choose language
        resultsInterface.append(string[0].rsplit('/', 1)[-1]+".wav")
        #add the langauges
        languages.append(string[0].rsplit('_', 1)[-1])

    usedWaveFiles = set(resultsInterface)
    for lang in languages:
        nonExistingWaveFiles = []
        existingWaveFiles = []
        for waveFile in usedWaveFiles:

            url = config.audioURLbase +"/"+lang+"/interface/"+ waveFile
            if urllib.urlopen(url).getcode() == 200:
                existingWaveFiles.append(waveFile)
            else:
                nonExistingWaveFiles.append(waveFile)
                existingWaveFiles = sorted(existingWaveFiles)
                nonExistingWaveFiles = sorted(nonExistingWaveFiles)
        finalResultsInterface.append([lang,existingWaveFiles,nonExistingWaveFiles])

    #check the DB for subjects without a voicelabel
    noVoicelabelQuery = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
    PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
	PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT DISTINCT ?subject   WHERE {
    ?subject rdf:type	rdfs:Resource .
    FILTER(NOT EXISTS {?subject speakle:voicelabel_en ?voicelabel_en .})
    }"""
    subjectsWithoutVoicelabel = executeSparqlQuery(noVoicelabelQuery)
    subjectsWithoutVoicelabel = sorted(subjectsWithoutVoicelabel)
            #TODO: implement language


    #check the DB for subjects with a voicelabel, to check whether it exists or not
    voicelabelQuery = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX speakle: <http://purl.org/collections/w4ra/speakle/>
    PREFIX radiomarche: <http://purl.org/collections/w4ra/radiomarche/>
	PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT DISTINCT ?subject ?voicelabel_en  WHERE {
    ?subject rdf:type	rdfs:Resource .
    ?subject speakle:voicelabel_en ?voicelabel_en .
    }"""




    for lang in languages:


        voicelabelQuery = voicelabelQuery.replace("voicelabel_en","voicelabel_"+lang)
        subjectsWithVoicelabel = executeSparqlQuery(voicelabelQuery)
        sparqlNonExistingWaveFiles = []
        sparqlExistingWaveFiles = []
        for subject in subjectsWithVoicelabel:

            url = subject[1]
            if urllib.urlopen(url).getcode() == 200:
                sparqlExistingWaveFiles.append(subject[1])
            else:
                sparqlNonExistingWaveFiles.append(subject[1])
                sparqlExistingWaveFiles = sorted(sparqlExistingWaveFiles)
                sparqlNonExistingWaveFiles = sorted(sparqlNonExistingWaveFiles)
        finalResultsSparql.append([lang,sparqlExistingWaveFiles,sparqlNonExistingWaveFiles])



    return render_template(
    'audiofiles.html',
    scannedFiles = pythonFiles,
    interfaceResults = finalResultsInterface,
    subjectsWithoutVoicelabel = subjectsWithoutVoicelabel,
    sparqlResults = finalResultsSparql)


if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=config.debug)
