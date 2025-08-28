"""Utility functions for face recognition module"""

import cv2
import logging
from typing import List, Dict, Any, Generator
from app.database import DatabaseManager
from .camera_service import CameraService
from .face_service import FaceRecognitionService
from .config import CameraConfig, AppConfig, FaceRecognitionConfig

logger = logging.getLogger(__name__)

def get_upload_data() -> List[Dict[str, Any]]:
    """Fetch upload data from database"""
    try:
        conn = DatabaseManager.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    NucleusId,         
                    ContractorId,      
                    LabourName, 
                    ContractorName,   
                    Amount,            
                    CASE WHEN IsPaid = 1 THEN 1 ELSE 0 END AS IsPaid,   -- force into 0/1
                    CASE WHEN IsPaid = 1 THEN 'Yes' ELSE 'No' END AS IsPaidText, 
                    UnitId,
                    CreatedBy,
                    CreatedAt
                FROM WagesUpload
                WHERE CONVERT(VARCHAR(19), CreatedAt, 120) = (
                    SELECT CONVERT(VARCHAR(19), MAX(CreatedAt), 120)
                    FROM WagesUpload
                );
            """)
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to fetch upload data: {e}")
    return []

def generate_video_frames(camera_service: CameraService, 
                         face_service: FaceRecognitionService, 
                         employee_id: int) -> Generator[bytes, None, None]:
    """Generate video frames for streaming with improved performance handling"""
    import time
    
    # Initialize configuration instances
    camera_config = CameraConfig()
    app_config = AppConfig()
    face_config = FaceRecognitionConfig()
    
    no_frame_count = 0
    frame_counter = 0
    last_successful_frame = None
    
    logger.info(f"Starting video frame generation for employee {employee_id}")
    
    while camera_service.is_running and camera_service.current_employee_id == employee_id:
        try:
            frame = camera_service.get_latest_frame()
            frame_counter += 1
            
            if frame is None:
                no_frame_count += 1
                logger.debug(f"No frame received, count: {no_frame_count}")
                
                # Use last successful frame if available
                if last_successful_frame is not None and no_frame_count < 5:
                    frame = last_successful_frame.copy()
                else:
                    if no_frame_count > app_config.MAX_NO_FRAME_COUNT:
                        logger.warning(f"No frames for {no_frame_count} consecutive attempts, stopping generation")
                        break
                    time.sleep(0.1)  # Small delay before retry
                    continue
            else:
                no_frame_count = 0
                last_successful_frame = frame.copy()
            
            # Skip frames for better performance on slower systems
            if frame_counter % face_config.PROCESS_EVERY_N_FRAMES != 0:
                continue
            
            # Process frame for face recognition
            try:
                processed = face_service.process_frame(frame, employee_id)
                processed_frame = processed.frame
            except Exception as proc_error:
                logger.warning(f"Frame processing error: {proc_error}")
                processed_frame = frame  # Use original frame if processing fails
            
            # Encode frame as JPEG with error handling
            try:
                ret, buffer = cv2.imencode('.jpg', processed_frame, 
                                         [cv2.IMWRITE_JPEG_QUALITY, camera_config.JPEG_QUALITY])
                if not ret:
                    logger.warning("Failed to encode frame as JPEG")
                    continue
                
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                       
            except Exception as encode_error:
                logger.warning(f"Frame encoding error: {encode_error}")
                continue
                   
        except Exception as e:
            logger.error(f"Frame generation error: {e}")
            time.sleep(0.1)  # Small delay before retry
            continue
    
    logger.info("Frame generation ended")