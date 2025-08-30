"""Utility functions for face recognition module"""

import logging
from typing import List, Dict, Any, Generator
from app.database import DatabaseManager
from .face_service import FaceRecognitionService
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
