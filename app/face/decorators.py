"""Custom decorators for face recognition module"""

import functools
import logging
from flask import request, jsonify, render_template
from .exceptions import FaceRecognitionError, ValidationError
from .validators import RequestValidator

logger = logging.getLogger(__name__)

def handle_face_recognition_errors(f):
    """Decorator to handle face recognition errors gracefully"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error in {f.__name__}: {e}")
            if request.is_json:
                return jsonify({"status": "error", "message": str(e)}), 400
            else:
                flash(str(e), "error")
                return render_template('FaceRecognition/face.html')
        except FaceRecognitionError as e:
            logger.error(f"Face recognition error in {f.__name__}: {e}")
            if request.is_json:
                return jsonify({"status": "error", "message": str(e)}), 500
            else:
                flash("Face recognition error occurred", "error")
                return render_template('FaceRecognition/face.html')
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {e}")
            if request.is_json:
                return jsonify({"status": "error", "message": "Internal server error"}), 500
            else:
                flash("An unexpected error occurred", "error")
                return render_template('FaceRecognition/face.html')
    
    return decorated_function

def validate_employee_id(f):
    """Decorator to validate employee ID parameter"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'GET':
            employee_id = request.args.get('employee_id')
        else:
            data = request.get_json() or {}
            employee_id = data.get('employee_id')
        
        if employee_id is not None:
            try:
                validated_id = RequestValidator.validate_employee_id(employee_id)
                # Add validated ID to request context or kwargs
                if request.method == 'GET':
                    request.args = request.args.copy()
                    request.args['employee_id'] = validated_id
                else:
                    request.validated_employee_id = validated_id
            except ValidationError as e:
                if request.is_json:
                    return jsonify({"status": "error", "message": str(e)}), 400
                else:
                    flash(str(e), "error")
                    return render_template('FaceRecognition/face.html')
        
        return f(*args, **kwargs)
    
    return decorated_function