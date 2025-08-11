from flask import Blueprint

face_bp = Blueprint('face', __name__,)

from . import routes  