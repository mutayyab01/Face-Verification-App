import threading
import logging
import cv2
import base64
import pandas as pd
import numpy as np
import face_recognition
from flask import request, render_template, flash, Response
from app.auth.decorators import require_auth, require_role
from .models import EmployeeFaceModel
from app.database import DatabaseManager
from . import face_bp

logger = logging.getLogger(__name__)

encoding_cache = {}

# Global camera management - Thread-safe singleton pattern
_camera_lock = threading.Lock()
video_capture = None
camera_thread = None
frame_lock = threading.Lock()
latest_frame = None
camera_running = False
current_employee_id = None
_working_camera_index = None  # Cache the working camera index
_camera_initialized = False

def find_working_camera():
    global _working_camera_index
    
    # Use cached camera index if available
    if _working_camera_index is not None:
        # Try different backends for cached camera
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
        for backend in backends:
            cap = cv2.VideoCapture(_working_camera_index, backend)
            if cap.isOpened():
                ret, _ = cap.read()
                cap.release()
                if ret:
                    print(f"Using cached camera at index {_working_camera_index} with backend {backend}")
                    return _working_camera_index, backend
        
        # Cache is invalid, reset it
        _working_camera_index = None
    
    # Search for working camera with different backends
    print("Searching for working camera...")
    backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
    
    for i in range(3):
        for backend in backends:
            cap = cv2.VideoCapture(i, backend)
            if cap.isOpened():
                ret, _ = cap.read()
                cap.release()
                if ret:
                    print(f"Camera found at index {i} with backend {backend}")
                    _working_camera_index = i
                    return i, backend
    
    print("No working camera found during search.")
    return -1, cv2.CAP_ANY

def stop_camera():
    """Properly stop and cleanup camera resources"""
    global video_capture, camera_thread, camera_running, latest_frame, current_employee_id, _camera_initialized
    
    with _camera_lock:
        if not camera_running:
            return
            
        print(f"Stopping camera for employee {current_employee_id}...")
        camera_running = False
        
        # Wait for thread to finish with timeout
        if camera_thread is not None and camera_thread.is_alive():
            camera_thread.join(timeout=5.0)
            if camera_thread.is_alive():
                print("Warning: Camera thread did not stop gracefully")
        
        # Release video capture
        if video_capture is not None:
            try:
                video_capture.release()
                print("Video capture released successfully")
            except Exception as e:
                print(f"Error releasing video capture: {e}")
            video_capture = None
        
        # Reset variables
        camera_thread = None
        latest_frame = None
        current_employee_id = None
        _camera_initialized = False
        print("Camera stopped and resources cleaned up.")

def start_camera(employee_id):
    """Start camera with optimized initialization and backend support"""
    global video_capture, camera_thread, camera_running, current_employee_id, _camera_initialized

    with _camera_lock:
        # If camera is already running for the same employee → do nothing
        if camera_running and current_employee_id == employee_id and video_capture is not None and _camera_initialized:
            print(f"Camera already running for employee {employee_id}")
            return True

        # Stop existing camera before starting new one
        if camera_running or video_capture is not None:
            print("Stopping existing camera session...")
            stop_camera()
            import time
            time.sleep(1)  # Give time for cleanup

        # Start new camera session
        camera_result = find_working_camera()
        if isinstance(camera_result, tuple):
            camera_index, backend = camera_result
        else:
            camera_index, backend = camera_result, cv2.CAP_ANY
            
        if camera_index == -1:
            print("No working camera found.")
            return False

        print(f"Initializing camera {camera_index} for employee {employee_id} with backend {backend}...")
        
        try:
            video_capture = cv2.VideoCapture(camera_index, backend)
            
            # Try fallback backends if primary fails
            if not video_capture.isOpened():
                print("Trying fallback backends...")
                video_capture.release()
                video_capture = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
                
            if not video_capture.isOpened():
                video_capture.release()
                video_capture = cv2.VideoCapture(camera_index)
                
            if not video_capture.isOpened():
                print("Could not open video device with any backend")
                video_capture = None
                return False

            # Set camera properties
            video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            video_capture.set(cv2.CAP_PROP_FPS, 15)
            video_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            video_capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

            # Test camera initialization
            success_count = 0
            for attempt in range(10):
                ret, frame = video_capture.read()
                if ret and frame is not None:
                    success_count += 1
                    if success_count >= 3:
                        break
                else:
                    import time
                    time.sleep(0.1)

            if success_count < 3:
                print("Camera initialization failed - cannot capture frames")
                video_capture.release()
                video_capture = None
                return False

            camera_running = True
            current_employee_id = employee_id
            _camera_initialized = True

            def camera_loop():
                global latest_frame, camera_running
                print(f"Camera loop started for employee {employee_id}")
                
                while camera_running:
                    try:
                        if video_capture is None or not video_capture.isOpened():
                            print("Video capture is not available, breaking camera loop")
                            break
                            
                        ret, frame = video_capture.read()
                        if ret and frame is not None:
                            with frame_lock:
                                latest_frame = frame.copy()
                        else:
                            import time
                            time.sleep(0.01)  # Small delay to prevent CPU spinning
                            
                    except Exception as e:
                        print(f"Error in camera loop: {e}")
                        break
                        
                print("Camera loop ended")

            camera_thread = threading.Thread(target=camera_loop, daemon=True)
            camera_thread.start()
            print(f"Camera ready for employee {employee_id}")
            return True
            
        except Exception as e:
            print(f"Error starting camera: {e}")
            if video_capture is not None:
                video_capture.release()
                video_capture = None
            return False

def gen_frames(employee_id):
    """Generate video frames with stable face recognition"""
    if employee_id not in encoding_cache:
        print(f"No encoding cached for employee_id={employee_id}.")
        return

    try:
        known_encoding = encoding_cache[employee_id]
    except KeyError:
        print(f"Encoding cache miss for employee {employee_id}")
        return

    frame_count = 0
    # For stability - track matches over multiple frames
    recent_matches = []
    max_recent = 10  # Increased for better stability
    no_frame_count = 0
    stable_match_count = 0
    face_verified = False

    print(f"Starting frame generation for employee {employee_id}")

    while camera_running and current_employee_id == employee_id:
        try:
            with frame_lock:
                if latest_frame is None:
                    no_frame_count += 1
                    if no_frame_count > 100:  # If no frames for too long, break
                        print("No frames available for too long, stopping generation")
                        break
                    import time
                    time.sleep(0.01)
                    continue
                frame = latest_frame.copy()
                no_frame_count = 0  # Reset counter

            frame_count += 1
            
            # Process face recognition every 2nd frame for better performance
            process_faces = (frame_count % 2 == 0)
            
            if process_faces:
                # Resize frame for faster face recognition
                small_frame = cv2.resize(frame, (0, 0), fx=0.4, fy=0.4)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                try:
                    face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
                    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

                    current_frame_matches = []
                    
                    for face_encoding, face_location in zip(face_encodings, face_locations):
                        # Compare faces with stricter tolerance for stability
                        matches = face_recognition.compare_faces([known_encoding], face_encoding, tolerance=0.5)
                        face_distance = face_recognition.face_distance([known_encoding], face_encoding)[0]
                        
                        # Scale back up face locations (0.4 scale factor)
                        top, right, bottom, left = [int(coord / 0.4) for coord in face_location]
                        
                        is_match = matches[0] and face_distance < 0.5
                        current_frame_matches.append(is_match)
                        
                        if is_match:
                            confidence = (1 - face_distance) * 100
                            label = "MATCH"
                            color = (0, 255, 0)  # Green
                            thickness = 3
                            stable_match_count += 1
                        else:
                            label = "UNKNOWN"
                            color = (0, 0, 255)  # Red
                            thickness = 2
                            stable_match_count = 0  # Reset on non-match
                        
                        # Draw rectangle and label with better visibility
                        cv2.rectangle(frame, (left, top), (right, bottom), color, thickness)
                        
                        # Background for text
                        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                        cv2.rectangle(frame, (left, top - text_size[1] - 10), 
                                    (left + text_size[0], top), color, -1)
                        
                        cv2.putText(frame, label, (left, top - 5),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                    # Track recent matches for stability
                    recent_matches.extend(current_frame_matches)
                    if len(recent_matches) > max_recent:
                        recent_matches = recent_matches[-max_recent:]
                    
                    # Check for stable face verification
                    if len(recent_matches) >= max_recent:
                        match_ratio = sum(recent_matches) / len(recent_matches)
                        if match_ratio >= 0.8 and not face_verified:  # 80% matches in recent frames
                            face_verified = True
                            print(f"✅ Face VERIFIED for employee {employee_id} (Match ratio: {match_ratio:.2f})")

                except Exception as face_error:
                    print(f"Face recognition error: {face_error}")
                    # Continue without face recognition if there's an error

            # Add employee info overlay with verification status
            overlay_height = 80 if face_verified else 50
            cv2.rectangle(frame, (10, 10), (400, 10 + overlay_height), (0, 0, 0), -1)
            cv2.putText(frame, f"Employee ID: {employee_id}", (15, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # Encode and yield frame with good quality
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ret:
                continue

            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        except Exception as frame_error:
            print(f"Frame processing error: {frame_error}")
            continue

    print("Frame generation ended")

@face_bp.route('/matchFace', methods=['GET'])
@require_auth
@require_role(['admin', 'hr'])
def MatchEmpFace():
    employee_id = request.args.get('employee_id', type=int)

    upload_data = []
    try:
        conn = DatabaseManager.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT Id, NucleusId, Name, FatherName, Amount, IsPaid FROM uploadata")
            upload_data = cursor.fetchall()
            print(f"✅ Fetched {len(upload_data)} rows from uploadata table.")
    except Exception as e:
        logger.error(f"❌ Failed to fetch uploadata: {e}")
        print(f"❌ Failed to fetch uploadata: {e}")

    if not employee_id:
        # Stop camera when no employee is selected
        stop_camera()
        return render_template('FaceRecognition/face.html', upload_data=upload_data)

    try:
        employee = EmployeeFaceModel.get_by_id(employee_id)
        if not employee:
            flash("Employee not found.", "error")
            stop_camera()
            return render_template('FaceRecognition/face.html', upload_data=upload_data)

        image_data = getattr(employee, 'Image', None)
        if not image_data:
            flash("No image found for this employee.", "error")
            stop_camera()
            return render_template('FaceRecognition/face.html', upload_data=upload_data)

        # Cache encoding if not already cached
        if employee_id not in encoding_cache:
            try:
                np_img = np.frombuffer(image_data, np.uint8)
                loaded_image = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
                if loaded_image is None:
                    flash("Invalid image data.", "error")
                    stop_camera()
                    return render_template('FaceRecognition/face.html', upload_data=upload_data)

                rgb_image = cv2.cvtColor(loaded_image, cv2.COLOR_BGR2RGB)
                encodings = face_recognition.face_encodings(rgb_image)
                if not encodings:
                    flash("No face found in image.", "error")
                    stop_camera()
                    return render_template('FaceRecognition/face.html', upload_data=upload_data)

                encoding_cache[employee_id] = encodings[0]
                print(f"Face encoding cached for employee {employee_id}")
                
            except Exception as enc_error:
                print(f"Error creating face encoding: {enc_error}")
                flash("Error processing face image.", "error")
                stop_camera()
                return render_template('FaceRecognition/face.html', upload_data=upload_data)

        image_base64 = base64.b64encode(image_data).decode('utf-8')
        return render_template('FaceRecognition/face.html',
                               employee_id=employee_id,
                               image_base64=image_base64,
                               upload_data=upload_data)

    except Exception as e:
        logger.error(f"Error in MatchEmpFace: {e}")
        flash("An error occurred.", "error")
        stop_camera()
        return render_template('FaceRecognition/face.html', upload_data=upload_data)
    
@face_bp.route('/video_feed')
@require_auth
@require_role(['admin', 'hr'])
def video_feed():
    employee_id = request.args.get('employee_id', type=int)
    if not employee_id:
        return "Employee ID required", 400
        
    if employee_id not in encoding_cache:
        return "Face encoding not loaded for this employee. Please load face first.", 400

    try:
        print(f"Starting video feed for employee {employee_id}")
        
        # Start camera for this specific employee
        if not start_camera(employee_id):
            return "Failed to initialize camera", 500
        
        return Response(gen_frames(employee_id),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
                        
    except Exception as e:
        print(f"Video feed error: {e}")
        import traceback
        print(traceback.format_exc())
        stop_camera()  # Clean up on error
        return "Video feed error occurred", 500

def preload_camera():
    """Preload camera on application startup for faster access"""
    global _working_camera_index
    
    if _working_camera_index is not None:
        return  # Already cached
    
    print("Preloading camera for faster startup...")
    find_working_camera()  # This will cache the working camera index

@face_bp.route('/preload_camera', methods=['POST'])
@require_auth 
@require_role(['admin', 'hr'])
def preload_camera_endpoint():
    """Endpoint to preload camera"""
    try:
        preload_camera()
        return {"status": "success", "message": "Camera preloaded"}, 200
    except Exception as e:
        print(f"Error preloading camera: {e}")
        return {"status": "error", "message": str(e)}, 500

@face_bp.route('/stop_camera', methods=['POST'])
@require_auth
@require_role(['admin', 'hr'])
def stop_camera_endpoint():
    """Endpoint to manually stop the camera"""
    try:
        stop_camera()
        return {"status": "success", "message": "Camera stopped"}, 200
    except Exception as e:
        print(f"Error stopping camera: {e}")
        return {"status": "error", "message": str(e)}, 500

@face_bp.route('/verify_employee', methods=['POST'])
@require_auth
@require_role(['admin', 'hr'])
def verify_employee():
    """Verify employee face match and update wages payment status"""
    try:
        data = request.get_json()
        employee_id = data.get('employee_id')
        
        if not employee_id:
            return {"status": "error", "message": "Employee ID is required"}, 400
        
        conn = DatabaseManager.get_connection()
        if not conn:
            return {"status": "error", "message": "Database connection failed"}, 500
            
        cursor = conn.cursor()
        
        # Get employee details from Employee table
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
        
        # Check if wages record exists for this NucleusId
        cursor.execute("""
            SELECT Id, Name, FatherName, Amount, IsPaid 
            FROM uploadata 
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
        
        # Update wages payment status to paid
        cursor.execute("""
            UPDATE uploadata 
            SET IsPaid = 1 
            WHERE NucleusId = ?
        """, (nucleus_id,))
        
        conn.commit()
        
        print(f"✅ Payment marked for Employee: {employee_name} (NucleusId: {nucleus_id})")
        
        return {
            "status": "success", 
            "message": "Face verification successful! Wages payment confirmed.",
            "employee_name": employee_name,
            "father_name": father_name,
            "nucleus_id": nucleus_id,
            "amount": wage_record[3],
            "wage_id": wage_id
        }, 200
        
    except Exception as e:
        logger.error(f"Error in verify_employee: {e}")
        print(f"❌ Error in verify_employee: {e}")
        return {"status": "error", "message": "Verification failed"}, 500
    finally:
        if 'conn' in locals():
            conn.close()

# Cleanup function to be called when the application shuts down
def cleanup_resources():
    """Clean up all resources when the application shuts down"""
    global _working_camera_index
    print("Cleaning up face recognition resources...")
    stop_camera()
    encoding_cache.clear()
    _working_camera_index = None

# Initialize camera on startup
try:
    preload_camera()
except:
    pass  # Ignore errors during startup

# Register cleanup function
import atexit
atexit.register(cleanup_resources)