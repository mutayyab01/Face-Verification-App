from flask import Blueprint

contractors_bp = Blueprint('contractors', __name__, url_prefix='/contractors')

from . import routes