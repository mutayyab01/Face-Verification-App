"""Face recognition routes with proper separation of concerns"""

import logging
from flask import request, render_template, flash,Response, jsonify
from app.auth.decorators import require_auth, require_role
from app.database import DatabaseManager
from .models import EmployeeFaceModel
from .models import EmployeeModel
from .face_service import FaceRecognitionService
from .exceptions import FaceRecognitionError
from .utils import  get_upload_data
from . import face_bp
import face_recognition
import base64
import io

logger = logging.getLogger(__name__)


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
    
@face_bp.route('/cashier/RenderFacePage')
@require_auth
@require_role(['admin', 'cashier'])
def RenderFacePage():
    upload_data=get_upload_data()
    return render_template("FaceRecognition/VerifyByFace.html",upload_data=upload_data)

@face_bp.route('/cashier/GetEmployeeByIdOnFacePage', methods=['GET',"POST"])
@require_auth
@require_role(['admin', 'cashier'])
def GetEmployeeById_onFacePage():
    """Main face matching interface"""
    data = request.get_json(force=True)
    employee_id = data.get("neclusid")
    
    if not employee_id:
        return jsonify({'message': 'Please Enter Number'})
    
    try:
        employee_id = int(employee_id)  #
    except (ValueError, TypeError):
        return jsonify({'message': 'ID must be a valid integer'})
    try:
        employee = EmployeeFaceModel.get_by_id(employee_id)
        row = EmployeeModel.getNameandAmount(employee_id)
        
        if not employee or not employee.Image:
            flash("Employee not found or no image available.", "error")
            return jsonify({'message': 'Employee not found or no image available.'})
        face_service.load_employee_encoding(employee_id, employee.Image)

        import base64
        image_base64 = "data:image/png;base64," + base64.b64encode(employee.Image).decode('utf-8')
        return jsonify({
            "status": "success",
            "employee_id": employee_id,
            "employee_name": row[0],
            "employee_amount": row[1],
            "employee_image": image_base64,
            "message": "Employee fetched"
        })
                             
    except FaceRecognitionError as e:
        logger.error(f"Face recognition error: {e}")
        flash(str(e), "error")
        return jsonify({'message': 'Face recognition error occurred.'})
    except Exception as e:
        logger.error(f"Unexpected error in match_employee_face: {e}")
        flash("An unexpected error occurred.", "error")
        return jsonify({'message': 'Unexpected error occurred.'})

@face_bp.route('/cashier/GetWagesData')
@require_auth
@require_role(['admin', 'cashier'])
def get_wages_data():
    upload_data = get_upload_data()
    rows = []
    for row in upload_data:
        rows.append({
            "labour_code": row[0],
            "labour_name": row[2],
            "contractor_name": row[3],
            "amount": row[4],
            "paid": bool(row[5])
        })
    return jsonify({"data": rows})

# ===== Match Face & Update Wages =====
@face_bp.route('/cashier/VerifyEmployeeOnFacePage', methods=["POST"])
@require_auth
@require_role(['admin', 'cashier'])
def VerifyEmployee_onFacePage():
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
                    return jsonify({"status": "error", "message": "Employee not found or inactive"}), 404

                nucleus_id, employee_name, contractor_name = employee

                cursor.execute("""
                    SELECT TOP 1 Id, LabourName, ContractorName, Amount, IsPaid, CreatedAt
                    FROM WagesUpload 
                    WHERE NucleusId = ?
                    ORDER BY CreatedAt DESC
                """, (nucleus_id,))
                wage_record = cursor.fetchone()
                if not wage_record:
                    return jsonify({
                        "status": "error",
                        "message": f"No wages record found for Employee NucleusId: {nucleus_id}"
                    }), 404

                wage_id, wage_labour_name, wage_contractor_name, amount, is_already_paid, created_at = wage_record

                if is_already_paid == 1:
                    return jsonify({
                        "status": "warning",
                        "message": "Wages already paid for this employee",
                        "ContractorName": contractor_name,
                        "LabourName": employee_name,
                        "nucleus_id": nucleus_id,
                        "amount": amount,
                        "wage_id": wage_id
                    }), 200

                cursor.execute("""
                    UPDATE WagesUpload
                    SET IsPaid = 1
                    WHERE Id = ?
                """, (wage_id,))
                conn.commit()

                return jsonify({
                    "status": "success",
                    "message": "✅ Face and Employee Code matched! Wages payment confirmed.",
                    "employee_name": employee_name,
                    "contractor_name": contractor_name,
                    "nucleus_id": nucleus_id,
                    "amount": amount,
                    "wage_id": wage_id
                }), 200
            except Exception as e:
                logger.error(f"Error in verify_employee: {e}")
                return jsonify({"status": "error", "message": "Verification failed"}), 500
        else:
            return jsonify({"status": "error", "message": "Face did not match"}), 400
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
        return render_template('FaceRecognition/VerifyByCode.html', upload_data=upload_data)
    
    try:
        employee = EmployeeFaceModel.get_by_id(employee_id)
        if not employee or not employee.Image:
            print("this is employee exit or not")
            flash("Employee not found or no image available.", "error")
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
        return render_template('FaceRecognition/VerifyByCode.html', upload_data=upload_data)
    except Exception as e:
        logger.error(f"Unexpected error in match_employee_face: {e}")
        flash("An unexpected error occurred.", "error")
        return render_template('FaceRecognition/VerifyByCode.html', upload_data=upload_data)

@face_bp.route('/cashier/matchbycode', methods=['GET'])
@require_auth
@require_role(['admin', 'cashier'])
def MatchbyCode():
    """Main face matching interface"""
    employee_id = request.args.get('employee_id', type=int)
    upload_data = get_upload_data()
    
    if not employee_id:
        return render_template('FaceRecognition/VerifyByCode.html', upload_data=upload_data)
    
    try:
        # Fetch employee face
        # Fetch employee face
        employee = EmployeeFaceModel.get_by_id(employee_id)
        if not employee or not employee.Image:
            flash("Employee not found or no image available.", "error")
            return render_template('FaceRecognition/VerifyByCode.html', upload_data=upload_data)
        
        # Load face encoding
        face_service.load_employee_encoding(employee_id, employee.Image)
        
        # Convert image to base64
        # Convert image to base64
        import base64
        image_base64 = base64.b64encode(employee.Image).decode('utf-8')
        row = EmployeeModel.getNameandAmount(employee_id)
        print("Employee Data:", row)

        return render_template('FaceRecognition/VerifyByCode.html',
                             employee_id=employee_id,
                             employeObject=row,
                             image_base64=image_base64,
                             upload_data=upload_data)
                             
    except FaceRecognitionError as e:
        logger.error(f"Face recognition error: {e}")
        flash(str(e), "error")
        return render_template('FaceRecognition/VerifyByCode.html', upload_data=upload_data)
    except Exception as e:
        logger.error(f"Unexpected error in match_employee_face: {e}")
        flash("An unexpected error occurred.", "error")
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




    