from pycall import CallFile, Call, Application

def placeCall(number,URL):
	"""Places an outgoing call to the given number through the dongle. 
	When picked up, it redirects to the given VXML URL."""
	c = Call('Dongle/dongle0/%s' % number)
	a = Application('Vxml',URL)
	cf = CallFile(c, a)
	cf.spool()
	return

