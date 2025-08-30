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
import face_recognition
import base64
import io

logger = logging.getLogger(__name__)


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
    
@face_bp.route('/cashier/testfaceapp')
@require_auth
@require_role(['admin', 'cashier'])
def testfaceapp():
    upload_data=get_upload_data()
    return render_template("FaceRecognition/testface.html",upload_data=upload_data)


# ===== Match Face & Update Wages =====
@face_bp.route('/cashier/matchFace', methods=["POST"])
@require_auth
@require_role(['admin', 'cashier'])
def match_face():
    try:
        data = request.get_json(force=True)
        neclusid = data.get("neclusid")
        live_image_data = data.get("live_image")  # optional

        if not neclusid:
            return jsonify({"status": "error", "message": "Employee Code (Neclusid) required"}), 400

        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1 NucleusId, Name, Image
            FROM Employee
            WHERE NucleusId = ?
        """, (neclusid,))
        row = cursor.fetchone()

        if not row:
            return jsonify({"status": "error", "message": "Employee not found"}), 404

        nucleus_id, name, image_bytes = row
        if not image_bytes:
            return jsonify({"status": "error", "message": "Employee has no stored face image"}), 404

        # Convert DB image to Base64 for frontend
        image_base64 = "data:image/png;base64," + base64.b64encode(image_bytes).decode('utf-8')

        # If no live image sent → return employee info
        if not live_image_data:
            return jsonify({
                "status": "success",
                "neclusid": nucleus_id,
                "employee_name": name,
                "employee_image": image_base64,
                "message": "Employee fetched"
            })

        # ===== Face Recognition =====
        db_image = face_recognition.load_image_file(io.BytesIO(image_bytes))
        db_encodings = face_recognition.face_encodings(db_image)
        if not db_encodings:
            return jsonify({"status": "error", "message": "No face detected in stored employee image"}), 400
        db_encoding = db_encodings[0]

        header, encoded = live_image_data.split(",", 1)
        live_image_bytes = base64.b64decode(encoded)
        live_image = face_recognition.load_image_file(io.BytesIO(live_image_bytes))
        live_encodings = face_recognition.face_encodings(live_image)
        if not live_encodings:
            return jsonify({"status": "error", "message": "No face detected in live image"}), 400
        live_encoding = live_encodings[0]

        matched = face_recognition.compare_faces([db_encoding], live_encoding, tolerance=0.5)[0]
        message = "Matched ✅" if matched else "Unknown ❌"
        # ===== Update WagesUpload if matched =====
        if matched:
            try:
                cursor.execute("""
                    SELECT NucleusId, Name, FatherName 
                    FROM Employee 
                    WHERE NucleusId = ? AND IsActive = 1
                """, (neclusid,))
                employee = cursor.fetchone()
                print(employee)
                if not employee:
                    return {"status": "error", "message": "Employee not found or inactive"}, 404

                nucleus_id, employee_name, contractor_name = employee

                cursor.execute("""
                    SELECT TOP 1 Id, LabourName, ContractorName, Amount, IsPaid, CreatedAt
                    FROM WagesUpload 
                    WHERE NucleusId = ?
                    ORDER BY CreatedAt DESC
                """, (nucleus_id,))
                wage_record = cursor.fetchone()
                if not wage_record:
                    return {
                        "status": "error",
                        "message": f"No wages record found for Employee NucleusId: {nucleus_id}"
                    }, 404

                wage_id, wage_labour_name, wage_contractor_name, amount, is_already_paid, created_at = wage_record

                if is_already_paid == 1:
                    return {
                        "status": "warning",
                        "message": "Wages already paid for this employee",
                        "ContractorName": contractor_name,
                        "LabourName": employee_name,
                        "nucleus_id": nucleus_id,
                        "amount": amount,
                        "wage_id": wage_id
                    }, 200

                cursor.execute("""
                    UPDATE WagesUpload
                    SET IsPaid = 1
                    WHERE Id = ?
                """, (wage_id,))
                conn.commit()

                return {
                    "status": "success",
                    "message": "✅ Face and Employee Code matched! Wages payment confirmed.",
                    "employee_name": employee_name,
                    "contractor_name": contractor_name,
                    "nucleus_id": nucleus_id,
                    "amount": amount,
                    "wage_id": wage_id
                }, 200
            except Exception as e:
                logger.error(f"Error in verify_employee: {e}")
                return {"status": "error", "message": "Verification failed"}, 500
        else:
            return {"status": "error", "message": "Face did not match"}, 400
    finally:
        if 'conn' in locals():
            conn.close()
    
    
    
    
    
    

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
        
        face_service.load_employee_encoding(employee_id, employee.Image)
        
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
        # Fetch employee face
        employee = EmployeeFaceModel.get_by_id(employee_id)
        if not employee or not employee.Image:
            flash("Employee not found or no image available.", "error")
            camera_service.stop()
            return render_template('FaceRecognition/VerifyByCode.html', upload_data=upload_data)
        
        # Load face encoding
        face_service.load_employee_encoding(employee_id, employee.Image)
        
        # Convert image to base64
        import base64
        image_base64 = base64.b64encode(employee.Image).decode('utf-8')
        
        # Fetch amount from WagesUpload
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1 Amount,LabourName
            FROM WagesUpload
            WHERE NucleusId = ?
            ORDER BY CreatedAt DESC
        """, (employee_id,))
        row = cursor.fetchone()
        
        return render_template('FaceRecognition/VerifyByCode.html',
                               employee_id=employee_id,
                               image_base64=image_base64,
                               employeObject = row,
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
    try:
        data = request.get_json(silent=True) or {}
        employee_id = data.get("employee_id")

        if not employee_id:
            return jsonify({"status": "error", "message": "Employee ID is required"}), 400

        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT TOP 1 NucleusId, LabourName, ContractorName, Amount, IsPaid
            FROM WagesUpload
            WHERE NucleusId = ?
            ORDER BY CreatedAt DESC
        """, (employee_id,))
        row = cursor.fetchone()

        if not row:
            return jsonify({"status": "error", "message": "Employee not found"})

        nucleus_id, name, father_name, amount, is_paid = row

        if is_paid == 1:
            return jsonify({
                "status": "warning",
                "message": "Already paid!",
                "employee_name": name,
                "father_name": father_name,
                "nucleus_id": nucleus_id,
                "amount": amount
            })

        cursor.execute("""
            UPDATE WagesUpload
            SET IsPaid = 1
            WHERE NucleusId = ?
              AND CreatedAt = (
                  SELECT MAX(CreatedAt)
                  FROM WagesUpload
                  WHERE NucleusId = ?
              )
        """, (employee_id, employee_id))
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Verification successful",
            "employee_name": name,
            "father_name": father_name,
            "nucleus_id": nucleus_id,
            "amount": amount
        })

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

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
        face_service.load_employee_encoding(employee_id, employee.Image)

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
        print(employee_id, "this is employee id")

        if not employee_id:
            return {"status": "error", "message": "Employee ID is required"}, 400

        if not face_service._is_face_verified():
            return {
                "status": "error",
                "message": "Face does not match the stored employee image. Please try again."
            }, 400

        conn = DatabaseManager.get_connection()
        if not conn:
            return {"status": "error", "message": "Database connection failed"}, 500

        cursor = conn.cursor()

        cursor.execute("""
            SELECT NucleusId, Name, FatherName 
            FROM Employee 
            WHERE NucleusId = ? AND IsActive = 1
        """, (employee_id,))

        employee = cursor.fetchone()
        print(employee)
        if not employee:
            return {"status": "error", "message": "Employee not found or inactive"}, 404

        nucleus_id, employee_name, contractor_name = employee

        cursor.execute("""
            SELECT TOP 1 Id, LabourName, ContractorName, Amount, IsPaid, CreatedAt
            FROM WagesUpload 
            WHERE NucleusId = ?
            ORDER BY CreatedAt DESC
        """, (nucleus_id,))

        wage_record = cursor.fetchone()
        if not wage_record:
            return {
                "status": "error", 
                "message": f"No wages record found for Employee NucleusId: {nucleus_id}"
            }, 404

        wage_id, wage_labour_name, wage_contractor_name, amount, is_already_paid, created_at = wage_record

        if is_already_paid == 1:
            return {
                "status": "warning", 
                "message": "Wages already paid for this employee",
                "ContractorName": contractor_name,
                "LabourName": employee_name,
                "nucleus_id": nucleus_id,
                "amount": amount,
                "wage_id": wage_id
            }, 200

        cursor.execute("""
            UPDATE WagesUpload
            SET IsPaid = 1
            WHERE Id = ?
        """, (wage_id,))
        conn.commit()

        return {
            "status": "success", 
            "message": "✅ Face and Employee Code matched! Wages payment confirmed.",
            "employee_name": employee_name,
            "contractor_name": contractor_name,
            "nucleus_id": nucleus_id,
            "amount": amount,
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


import atexit

def cleanup_resources():
    """Cleanup resources on shutdown"""
    logger.info("Cleaning up face recognition resources...")
    camera_service.stop()
    face_service.clear_cache()

atexit.register(cleanup_resources)

    