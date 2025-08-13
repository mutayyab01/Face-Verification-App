from flask import Blueprint

face_bp = Blueprint('face', __name__, url_prefix='/face')

from . import routes, camera_service, face_service, models, utils