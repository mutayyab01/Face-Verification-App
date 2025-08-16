"""Utility functions for face recognition module"""

import cv2
import logging
from typing import List, Dict, Any, Generator
from app.database import DatabaseManager
from .camera_service import CameraService
from .face_service import FaceRecognitionService
from .config import CameraConfig

logger = logging.getLogger(__name__)

def 

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
    Name,              
    FatherName,        
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
    """Generate video frames for streaming"""
    config = CameraConfig()
    no_frame_count = 0
    
    while camera_service.is_running and camera_service.current_employee_id == employee_id:
        try:
            frame = camera_service.get_latest_frame()
            
            if frame is None:
                no_frame_count += 1
                if no_frame_count > config.MAX_NO_FRAME_COUNT:
                    logger.warning("No frames for too long, stopping generation")
                    break
                continue
            
            no_frame_count = 0
            
            # Process frame with face recognition
            processed = face_service.process_frame(frame, employee_id)
            
            # Encode frame
            ret, buffer = cv2.imencode('.jpg', processed.frame, 
                                     [cv2.IMWRITE_JPEG_QUALITY, config.JPEG_QUALITY])
            if not ret:
                continue
            
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                   
        except Exception as e:
            logger.error(f"Frame generation error: {e}")
            continue
    
    logger.info("Frame generation ended")