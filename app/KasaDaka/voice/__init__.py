from flask import Blueprint

voice = Blueprint(
    'voice',
    __name__,
    template_folder='templates',
    static_folder='static'
)

from . import views