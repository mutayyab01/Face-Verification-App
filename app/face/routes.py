"""Face recognition routes with proper separation of concerns"""

import logging
from flask import request, render_template, flash, Response, jsonify
from app.auth.decorators import require_auth, require_role
from app.database import DatabaseManager
from .models import EmployeeFaceModel
from .camera_service import CameraService
from .face_service import FaceRecognitionService
from .exceptions import FaceRecognitionError, CameraError, DatabaseError
from .utils import generate_video_frames, get_upload_data
from . import face_bp

logger = logging.getLogger(__name__)

# Initialize services
camera_service = CameraService()
face_service = FaceRecognitionService()

@face_bp.route('/cashier/dashboard')
@require_auth
@require_role(['cashier'])
def dashboard():
    """Face recognition dashboard"""
    try:
        
        return render_template('FaceRecognition/face_dashboard.html')
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash('Error loading dashboard.', 'error')
        return render_template('FaceRecognition/face_dashboard.html')
    
@face_bp.route('/cashier/VerifyByCode')
@require_auth
@require_role(['admin', 'cashier'])
def VerifyByCode():
    """Main face matching interface"""
    employee_id = request.args.get('employee_id', type=int)
    upload_data = get_upload_data()
    
    if not employee_id:
        camera_service.stop()
        return render_template('FaceRecognition/VerifyByCode.html', upload_data=upload_data)
    
    try:
        employee = EmployeeFaceModel.get_by_id(employee_id)
        if not employee or not employee.Image:
            print("this is employee exit or not")
            flash("Employee not found or no image available.", "error")
            camera_service.stop()
            return render_template('FaceRecognition/VerifyByCode.html', upload_data=upload_data)
        
        # Load face encoding
        face_service.load_employee_encoding(employee_id, employee.Image)
        
        # Prepare image for display
        import base64
        image_base64 = base64.b64encode(employee.Image).decode('utf-8')
        
        return render_template('FaceRecognition/VerifyByCode.html',
                             employee_id=employee_id,
                             image_base64=image_base64,
                             upload_data=upload_data)
                             
    except FaceRecognitionError as e:
        logger.error(f"Face recognition error: {e}")
        flash(str(e), "error")
        camera_service.stop()
        return render_template('FaceRecognition/VerifyByCode.html', upload_data=upload_data)
    except Exception as e:
        logger.error(f"Unexpected error in match_employee_face: {e}")
        flash("An unexpected error occurred.", "error")
        camera_service.stop()
        return render_template('FaceRecognition/VerifyByCode.html', upload_data=upload_data)

@face_bp.route('/cashier/matchbycode', methods=['GET'])
@require_auth
@require_role(['admin', 'cashier'])
def MatchbyCode():
    """Main face matching interface"""
    employee_id = request.args.get('employee_id', type=int)
    upload_data = get_upload_data()
    
    if not employee_id:
        camera_service.stop()
        return render_template('FaceRecognition/VerifyByCode.html', upload_data=upload_data)
    
    try:
        employee = EmployeeFaceModel.get_by_id(employee_id)
        if not employee or not employee.Image:
            flash("Employee not found or no image available.", "error")
            camera_service.stop()
            return render_template('FaceRecognition/VerifyByCode.html', upload_data=upload_data)
        
        # Load face encoding
        face_service.load_employee_encoding(employee_id, employee.Image)
        
        # Prepare image for display
        import base64
        image_base64 = base64.b64encode(employee.Image).decode('utf-8')
        
        return render_template('FaceRecognition/VerifyByCode.html',
                             employee_id=employee_id,
                             image_base64=image_base64,
                             upload_data=upload_data)
                             
    except FaceRecognitionError as e:
        logger.error(f"Face recognition error: {e}")
        flash(str(e), "error")
        camera_service.stop()
        return render_template('FaceRecognition/VerifyByCode.html', upload_data=upload_data)
    except Exception as e:
        logger.error(f"Unexpected error in match_employee_face: {e}")
        flash("An unexpected error occurred.", "error")
        camera_service.stop()
        return render_template('FaceRecognition/VerifyByCode.html', upload_data=upload_data)


@face_bp.route('/verify_employeebyCode', methods=['POST'])
@require_auth
@require_role(['admin', 'cashier'])
def verify_employeebyCode():
    """Verify employee face match AND employee code before marking wages paid"""
    try:
        data = request.get_json()
        employee_id = data.get('employee_id')
        print(employee_id,"this is employee id")

        if not employee_id:
            return {"status": "error", "message": "Employee ID is required"}, 400

        # 2️⃣ Database operations
        conn = DatabaseManager.get_connection()
        if not conn:
            return {"status": "error", "message": "Database connection failed"}, 500

        cursor = conn.cursor()

        # Get employee details
        cursor.execute("""
            SELECT NucleusId, Name, FatherName 
            FROM Employee 
            WHERE NucleusId = ? AND IsActive = 1
        """, (employee_id,))
        
        employee = cursor.fetchone()
        if not employee:
            return {"status": "error", "message": "Employee not found or inactive"}, 404

        nucleus_id = employee[0]
        employee_name = employee[1]
        father_name = employee[2]

        # Get wages record
        cursor.execute("""
            SELECT Id, Name, FatherName, Amount, IsPaid 
            FROM WagesUpload 
            WHERE NucleusId = ?
        """, (nucleus_id,))
        
        wage_record = cursor.fetchone()
        if not wage_record:
            return {
                "status": "error", 
                "message": f"No wages record found for Employee NucleusId: {nucleus_id}"
            }, 404

        wage_id = wage_record[0]
        is_already_paid = wage_record[4]

        if is_already_paid:
            return {
                "status": "warning", 
                "message": "Wages already paid for this employee",
                "employee_name": employee_name,
                "amount": wage_record[3]
            }, 200

        # Mark wages as paid
        cursor.execute("""
            UPDATE WagesUpload
            SET IsPaid = 1 
            WHERE NucleusId = ?
        """, (nucleus_id,))
        conn.commit()

        return {
            "status": "success", 
            "message": "✅ Face and Employee Code matched! Wages payment confirmed.",
            "employee_name": employee_name,
            "father_name": father_name,
            "nucleus_id": nucleus_id,
            "amount": wage_record[3],
            "wage_id": wage_id
        }, 200

    except Exception as e:
        logger.error(f"Error in verify_employee: {e}")
        return {"status": "error", "message": "Verification failed"}, 500
    finally:
        if 'conn' in locals():
            conn.close()





@face_bp.route('/cashier/matchFace', methods=['GET'])
@require_auth
@require_role(['admin', 'cashier'])
def MatchEmpFace():
    """Main face matching interface"""
    employee_id = request.args.get('employee_id', type=int)
    upload_data = get_upload_data()
    
    if not employee_id:
        camera_service.stop()
        return render_template('FaceRecognition/face.html', upload_data=upload_data)
    
    try:
        employee = EmployeeFaceModel.get_by_id(employee_id)
        if not employee or not employee.Image:
            flash("Employee not found or no image available.", "error")
            camera_service.stop()
            return render_template('FaceRecognition/face.html', upload_data=upload_data)
        
        # Load face encoding
        face_service.load_employee_encoding(employee_id, employee.Image)
        
        # Prepare image for display
        import base64
        image_base64 = base64.b64encode(employee.Image).decode('utf-8')
        
        return render_template('FaceRecognition/face.html',
                             employee_id=employee_id,
                             image_base64=image_base64,
                             upload_data=upload_data)
                             
    except FaceRecognitionError as e:
        logger.error(f"Face recognition error: {e}")
        flash(str(e), "error")
        camera_service.stop()
        return render_template('FaceRecognition/face.html', upload_data=upload_data)
    except Exception as e:
        logger.error(f"Unexpected error in match_employee_face: {e}")
        flash("An unexpected error occurred.", "error")
        camera_service.stop()
        return render_template('FaceRecognition/face.html', upload_data=upload_data)

@face_bp.route('/video_feed')
@require_auth
@require_role(['admin', 'cashier'])
def video_feed():
    """Video streaming endpoint"""
    employee_id = request.args.get('employee_id', type=int)
    
    if not employee_id:
        return jsonify({"error": "Employee ID required"}), 400
    
    if employee_id not in face_service.encoding_cache:
        return jsonify({"error": "Face encoding not loaded"}), 400
    
    try:
        camera_service.start(employee_id)
        face_service.reset_verification_state()
        
        return Response(
            generate_video_frames(camera_service, face_service, employee_id),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )
        
    except CameraError as e:
        logger.error(f"Camera error: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"Video feed error: {e}")
        camera_service.stop()
        return jsonify({"error": "Video feed failed"}), 500

@face_bp.route('/verify_employee', methods=['POST'])
@require_auth
@require_role(['admin', 'cashier'])
def verify_employee():
    """Verify employee face match AND employee code before marking wages paid"""
    try:
        data = request.get_json()
        employee_id = data.get('employee_id')
        print(employee_id,"this is employee id")

        if not employee_id:
            return {"status": "error", "message": "Employee ID is required"}, 400

        # 1️⃣ Check if face verification was successful
        if not face_service._is_face_verified():
            return {
                "status": "error",
                "message": "Face does not match the stored employee image. Please try again."
            }, 400

        # 2️⃣ Database operations
        conn = DatabaseManager.get_connection()
        if not conn:
            return {"status": "error", "message": "Database connection failed"}, 500

        cursor = conn.cursor()

        # Get employee details
        cursor.execute("""
            SELECT NucleusId, Name, FatherName 
            FROM Employee 
            WHERE NucleusId = ? AND IsActive = 1
        """, (employee_id,))
        
        employee = cursor.fetchone()
        if not employee:
            return {"status": "error", "message": "Employee not found or inactive"}, 404

        nucleus_id = employee[0]
        employee_name = employee[1]
        father_name = employee[2]

        # Get wages record
        cursor.execute("""
            SELECT Id, Name, FatherName, Amount, IsPaid 
            FROM WagesUpload 
            WHERE NucleusId = ?
        """, (nucleus_id,))
        
        wage_record = cursor.fetchone()
        if not wage_record:
            return {
                "status": "error", 
                "message": f"No wages record found for Employee NucleusId: {nucleus_id}"
            }, 404

        wage_id = wage_record[0]
        is_already_paid = wage_record[4]

        if is_already_paid:
            return {
                "status": "warning", 
                "message": "Wages already paid for this employee",
                "employee_name": employee_name,
                "amount": wage_record[3]
            }, 200

        # Mark wages as paid
        cursor.execute("""
            UPDATE WagesUpload
            SET IsPaid = 1 
            WHERE NucleusId = ?
        """, (nucleus_id,))
        conn.commit()

        return {
            "status": "success", 
            "message": "✅ Face and Employee Code matched! Wages payment confirmed.",
            "employee_name": employee_name,
            "father_name": father_name,
            "nucleus_id": nucleus_id,
            "amount": wage_record[3],
            "wage_id": wage_id
        }, 200

    except Exception as e:
        logger.error(f"Error in verify_employee: {e}")
        return {"status": "error", "message": "Verification failed"}, 500
    finally:
        if 'conn' in locals():
            conn.close()
@face_bp.route('/stop_camera', methods=['POST'])
@require_auth
@require_role(['admin', 'cashier'])
def stop_camera_endpoint():
    """Stop camera endpoint"""
    try:
        camera_service.stop()
        return jsonify({"status": "success", "message": "Camera stopped"})
    except Exception as e:
        logger.error(f"Error stopping camera: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Cleanup on module shutdown
import atexit

def cleanup_resources():
    """Cleanup resources on shutdown"""
    logger.info("Cleaning up face recognition resources...")
    camera_service.stop()
    face_service.clear_cache()

atexit.register(cleanup_resources)



