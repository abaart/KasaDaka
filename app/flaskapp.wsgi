#!/usr/bin/python
import sys
import logging
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/var/www/KasaDaka/")

from KasaDaka import app as application
application.secret_key = "n\xe6\xeb\xf5\x0c\xf7&\xffu\xc7\x1a\xe5@\xc8\xdf\xff\xef>l'\x85 Nk" 
