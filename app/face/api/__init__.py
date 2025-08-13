"""API endpoints for face recognition module"""

from flask import Blueprint

face_api_bp = Blueprint('face_api', __name__, url_prefix='/api/face')

from . import routes