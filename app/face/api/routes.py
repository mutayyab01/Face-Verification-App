"""API routes for face recognition module"""

import logging
from flask import request, jsonify
from app.auth.decorators import require_auth, require_role
from ..services import VerificationService, CameraService, FaceRecognitionService
from ..decorators import handle_face_recognition_errors, validate_employee_id
from ..exceptions import FaceRecognitionError
from . import face_api_bp

logger = logging.getLogger(__name__)

# Initialize services
verification_service = VerificationService()
camera_service = CameraService()
face_service = FaceRecognitionService()

@face_api_bp.route('/employee/<int:employee_id>/status', methods=['GET'])
@require_auth
@require_role(['admin', 'cashier'])
@handle_face_recognition_errors
@validate_employee_id
def get_employee_status(employee_id: int):
    """Get employee verification status"""
    result = verification_service.get_employee_verification_status(employee_id)
    return jsonify(result)

@face_api_bp.route('/employee/<int:employee_id>/verify', methods=['POST'])
@require_auth
@require_role(['admin', 'cashier'])
@handle_face_recognition_errors
@validate_employee_id
def verify_employee_api(employee_id: int):
    """Verify employee and process payment"""
    result = verification_service.verify_and_pay_employee(employee_id)
    return jsonify(result)

@face_api_bp.route('/camera/start', methods=['POST'])
@require_auth
@require_role(['admin', 'cashier'])
@handle_face_recognition_errors
def start_camera_api():
    """Start camera for employee"""
    data = request.get_json()
    employee_id = data.get('employee_id')
    
    if not employee_id:
        return jsonify({"status": "error", "message": "Employee ID required"}), 400
    
    try:
        camera_service.start(employee_id)
        face_service.reset_verification_state()
        return jsonify({"status": "success", "message": "Camera started"})
    except Exception as e:
        logger.error(f"Failed to start camera: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@face_api_bp.route('/camera/stop', methods=['POST'])
@require_auth
@require_role(['admin', 'cashier'])
@handle_face_recognition_errors
def stop_camera_api():
    """Stop camera"""
    try:
        camera_service.stop()
        return jsonify({"status": "success", "message": "Camera stopped"})
    except Exception as e:
        logger.error(f"Failed to stop camera: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@face_api_bp.route('/cache/clear', methods=['POST'])
@require_auth
@require_role(['admin'])
@handle_face_recognition_errors
def clear_cache_api():
    """Clear face encoding cache"""
    try:
        face_service.clear_cache()
        return jsonify({"status": "success", "message": "Cache cleared"})
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500