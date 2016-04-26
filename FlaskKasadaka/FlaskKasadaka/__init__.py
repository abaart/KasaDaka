from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash
from sparqlInterface import executeSparqlQuery, executeSparqlUpdate
from datetime import datetime
import config
import glob
import re
import urllib
import copy

app = Flask(__name__)
@app.route('/')
def index():
    """ Index page
	Only used to confirm hosting is working correctly
	"""
    return 'This is the Kasadaka Vxml generator'

@app.route('/admin/vaccination.html', methods=['GET','POST'])
def vaccinationScheme():
	if 'uri' not in request.args: return "Error, no uri specified"

	getVaccinationInfoQuery = """
	SELECT DISTINCT  ?uri  ?dab ?description ?disease ?vl_en WHERE {
                ?uri rdf:type cv:vaccination .
  				?uri cv:days_after_birth ?dab .
  				?uri cv:description ?description .
  				?uri cv:treats ?disease .
  				?uri speakle:voicelabel_en ?vl_en .
  FILTER(?uri=<INSERTURI>)
                }
	"""
	fieldNames=['URI','Days after birth','Description','Treats disease','Voicelabel_en']
	getVaccinationInfoQuery = getVaccinationInfoQuery.replace("<INSERTURI>","<"+request.args['uri']+">")
        result = executeSparqlQuery(getVaccinationInfoQuery,giveColumns=True, httpEncode=False)

	
	return render_template('admin/vaccination.html',user=result,fieldNames = fieldNames,
		uri = request.args['uri'],voiceLabelResults = getVoiceLabels(request.args['uri']))

@app.route('/admin/disease.html', methods=['GET','POST'])
def disease():
	if 'uri' not in request.args: return "Error, no uri specified"
	getDiseaseInfoQuery = """
		SELECT DISTINCT    ?label ?vl_en WHERE {
                ?uri rdf:type cv:disease .
                ?uri rdfs:label ?label .
		?uri speakle:voicelabel_en ?vl_en .
		FILTER(?uri = <INSERTURI>)
                }
	"""
	fieldNames=['Disease label','Voicelabel_en']
	getDiseaseInfoQuery = getDiseaseInfoQuery.replace("<INSERTURI>","<"+request.args['uri']+">")
        result = executeSparqlQuery(getDiseaseInfoQuery,giveColumns=True, httpEncode=False)

	getVaccinationsQuery = """SELECT DISTINCT  ?disease_label ?vac_uri ?dab ?description  WHERE {
                ?vac_uri cv:treats ?uri .
  				?vac_uri cv:days_after_birth ?dab .
  				?vac_uri cv:description ?description .
				?uri rdfs:label ?disease_label
  FILTER(?uri=<INSERTURI>)
                }"""
	getVaccinationsQuery = getVaccinationsQuery.replace("<INSERTURI>","<"+request.args['uri']+">")
	vaccinations = executeSparqlQuery(getVaccinationsQuery,httpEncode=False)


	return render_template('admin/disease.html',
		user = result,
		vaccinations = vaccinations,
		fieldNames = fieldNames,
		uri = request.args['uri'],
		voiceLabelResults = getVoiceLabels(request.args['uri']))

@app.route('/admin/listdiseases.html')
def listDiseases():
	getDiseasesQuery = """SELECT DISTINCT   ?uri  ?label  WHERE {
                ?uri rdf:type cv:disease .
                ?uri rdfs:label ?label .
                }"""

	result = executeSparqlQuery(getDiseasesQuery,httpEncode=False)
	
	return render_template('admin/listdiseases.html',diseases=result)


@app.route('/admin/chicken.html',methods=['GET','POST'])
def chicken():
	if 'uri' not in request.args: return "Error, no uri specified"

	getBatchInfoQuery = """
	 SELECT DISTINCT   ?uri  ?bdate ?owner ?vl_en WHERE {
                <INSERTURI> rdf:type cv:chicken_batch .
                ?uri cv:birth_date ?bdate .
                ?uri cv:owned_by ?owner .
                ?uri speakle:voicelabel_en ?vl_en .
                }
	"""
	getBatchInfoQuery = getBatchInfoQuery.replace("<INSERTURI>","<"+request.args['uri']+">")
        result = executeSparqlQuery(getBatchInfoQuery,giveColumns=True, httpEncode=False)
	fieldNames=['Batch URI','Birth date','Owner','English Voicelabel']
	return render_template('admin/chicken.html',
		user = result,
		fieldNames = fieldNames,
		uri = request.args['uri'],
		voiceLabelResults = getVoiceLabels(request.args['uri']))
	

@app.route('/admin/listchickens.html', methods=['GET','POST'])
def listchickens():
	getBatchesQuery = """SELECT DISTINCT  ?cbatch ?date ?owner_label  WHERE {
              ?cbatch rdf:type cv:chicken_batch .
             ?cbatch cv:birth_date ?date .
		?cbatch cv:owned_by ?owner .
		?owner rdfs:label ?owner_label .
                 }"""

	result = executeSparqlQuery(getBatchesQuery,httpEncode=False)
	
	return render_template('admin/listchickens.html',chickens=result)

@app.route('/admin')
def adminIndex():
	return render_template('admin/index.html')

@app.route('/admin/user.html', methods=['GET','POST'])
def user():
    userInfoQuery = """
    SELECT DISTINCT   ?fname  ?lname ?tel  ?pl ?vl_en WHERE {
                <INSERTUSER> rdf:type cv:user .
                ?user cv:contact_fname ?fname .
                ?user cv:contact_lname ?lname .
                ?user cv:contact_tel ?tel .
                ?user cv:preferred_language ?pl .
                ?user speakle:voicelabel_en ?vl_en .
                FILTER(?user=<INSERTUSER>) } """
    fieldNames=['First name','Last name','Tel. no.','Preferred language','English Voicelabel']
    
    updateUserInfoQuery = """
    DELETE WHERE
    {
    <INSERTUSER> cv:contact_fname <fname>.
    <INSERTUSER> cv:contact_lname <lname>.
    <INSERTUSER> cv:contact_tel <tel>.
    <INSERTUSER> cv:preferred_language <pl>.
    <INSERTUSER> speakle:voicelabel_en <vl_en>.
    };

    INSERT DATA 
    { 
    <INSERTUSER> cv:contact_fname <FNAME>.
    <INSERTUSER> cv:contact_lname <LNAME>.
    <INSERTUSER> cv:contact_tel <TEL>.
    <INSERTUSER> cv:preferred_language <PL>.
    <INSERTUSER> speakle:voicelabel_en <VL_EN>.
    }
    """
    #if insert request is received, insert triples
    if 'action' in request.args and request.args['action'] == 'new' :
	result = []        
	result.append(['FNAME','LNAME','TEL','PL','VL_EN'])
        return render_template(
                    'admin/user.html',
                    user = result, 
                    fieldNames = fieldNames, 
                    uri = 'new user',
		    new=True)
 
    #if update request is received, update triples
    elif 'action' in request.form and request.form['action'] == 'update' :
        #check whether all nessecary fields are sent with the request
        #fetch the columns to check
        userInfoQuery = userInfoQuery.replace("<INSERTUSER>","<"+request.form['user']+">")    
        result = executeSparqlQuery(userInfoQuery,giveColumns=True)
        columns = copy.deepcopy(result[0])
        columns.append('action')
        columns.append('user')
        #only proceed if all nessecary fields are present in the POST request
        if set(columns) == set(request.form):
            updateUserInfoQuery = updateUserInfoQuery.replace("<INSERTUSER>","<"+request.form['user']+">")
            for index, column in enumerate(result[0]):
                if re.search("(https?:\/\/(?:www\.|(?!www))[^\s\.]+\.[^\s]{2,}|www\.[^\s]+\.[^\s]{2,})",request.form[column]):
                    updateUserInfoQuery = updateUserInfoQuery.replace("<"+column.upper()+">","<"+request.form[column]+">")
                    updateUserInfoQuery = updateUserInfoQuery.replace("<"+column+">","<"+result[1][index]+">")

                else:
                    updateUserInfoQuery = updateUserInfoQuery.replace("<"+column.upper()+">","'"+request.form[column]+"'")
                    updateUserInfoQuery = updateUserInfoQuery.replace("<"+column+">","'"+result[1][index]+"'")

            #TODO removing triples does not work in ClioPatria? Mail Jan!
            success = executeSparqlUpdate(updateUserInfoQuery)
            if success:
                #TODO use Flask Flashing here
                return 'success!!'
        else:
            return "error: provided data in HTTP request does not match requirements."
    
    #if user received, look up user information
    elif 'user' in request.args:
	voiceLabels = getVoiceLabels(request.args['user'])
        #list information of a user
        userInfoQuery = userInfoQuery.replace("<INSERTUSER>","<"+request.args['user']+">")
        #TODO add support for voicelabels of all installed languages
        result = executeSparqlQuery(userInfoQuery,giveColumns=True)
        if len(fieldNames) == len(result[0]):
            return render_template(
                    'admin/user.html',
                    user = result, 
                    fieldNames = fieldNames, 
                    uri = request.args['user'],
		    voiceLabelResults = voiceLabels)
        else:
            return "Error: number of triples returned is not correct."
    return "Error: no user defined."


@app.route('/admin/listusers.html')
def listusers():
    #list all users in the system
    getUsersQuery = """SELECT DISTINCT  ?user ?fname  ?lname ?tel WHERE {
                                     ?user rdf:type cv:user .
                                     ?user cv:contact_fname ?fname .
                                      ?user cv:contact_lname ?lname .
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

def getVoiceLabels(uri):
	print "hai"
	languagesQuery =""" SELECT DISTINCT  ?voicelabel  WHERE {
          ?voicelabel   rdfs:subPropertyOf speakle:voicelabel.    }"""
	outputLanguagesQuery = executeSparqlQuery(languagesQuery)
	queryBuilder1 = """ SELECT DISTINCT """
	queryBuilder2 = """ """
	queryBuilder3 = """  WHERE {"""
	queryBuilder4 = """ """
	queryBuilder5 = """ FILTER(?uri=<""" + uri +""">) }"""
	voiceLabels = []
	for language in outputLanguagesQuery:
		queryBuilder2 =  " ?" + language[0].rsplit('/', 1)[-1]
		queryBuilder4 = " " + "OPTIONAL{?uri <"+language[0]+"> ?" + language[0].rsplit('/', 1)[-1] + " } "
		voiceLabelQuery = queryBuilder1 + queryBuilder2 + queryBuilder3 + queryBuilder4 + queryBuilder5
		voiceLabelResult = executeSparqlQuery(voiceLabelQuery,giveColumns=True,httpEncode=False)
		if len(voiceLabelResult[1]) is not 0: audio = voiceLabelResult[1][0]
		else: audio = ""
		voiceLabels.append([voiceLabelResult[0][0],audio])
	return voiceLabels
	


if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=config.debug)
