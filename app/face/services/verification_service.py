"""Employee verification service"""

import logging
from typing import Dict, Any, Optional
from ..models import EmployeeFaceModel, WagesModel
from ..exceptions import DatabaseError, FaceRecognitionError
from ..validators import RequestValidator

logger = logging.getLogger(__name__)

class VerificationService:
    """Service for employee verification and wage payment"""
    
    @staticmethod
    def verify_and_pay_employee(employee_id: int) -> Dict[str, Any]:
        """Verify employee face match and process wage payment"""
        try:
            # Validate employee ID
            validated_id = RequestValidator.validate_employee_id(employee_id)
            
            # Get employee details
            employee = EmployeeFaceModel.get_by_id(validated_id)
            if not employee:
                raise FaceRecognitionError("Employee not found or inactive")
            
            # Get wages record
            wages = WagesModel.get_by_nucleus_id(employee.nucleus_id)
            if not wages:
                raise FaceRecognitionError(f"No wages record found for employee {employee.nucleus_id}")
            
            # Check if already paid
            if wages.is_paid:
                return {
                    "status": "warning",
                    "message": "Wages already paid for this employee",
                    "employee_name": employee.name,
                    "father_name": employee.father_name,
                    "nucleus_id": employee.nucleus_id,
                    "amount": wages.amount,
                    "already_paid": True
                }
            
            # Mark as paid
            if wages.mark_as_paid():
                logger.info(f"Payment processed for {employee.name} (ID: {employee.nucleus_id})")
                
                return {
                    "status": "success",
                    "message": "Face verification successful! Wages payment confirmed.",
                    "employee_name": employee.name,
                    "father_name": employee.father_name,
                    "nucleus_id": employee.nucleus_id,
                    "amount": wages.amount,
                    "wage_id": wages.wages_id,
                    "already_paid": False
                }
            else:
                raise FaceRecognitionError("Failed to process payment")
                
        except FaceRecognitionError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in verification: {e}")
            raise FaceRecognitionError(f"Verification failed: {e}")
    
    @staticmethod
    def get_employee_verification_status(employee_id: int) -> Dict[str, Any]:
        """Get employee verification status without processing payment"""
        try:
            validated_id = RequestValidator.validate_employee_id(employee_id)
            
            employee = EmployeeFaceModel.get_by_id(validated_id)
            if not employee:
                return {"status": "error", "message": "Employee not found"}
            
            wages = WagesModel.get_by_nucleus_id(employee.nucleus_id)
            if not wages:
                return {"status": "error", "message": "No wages record found"}
            
            return {
                "status": "success",
                "employee_name": employee.name,
                "father_name": employee.father_name,
                "nucleus_id": employee.nucleus_id,
                "amount": wages.amount,
                "is_paid": wages.is_paid,
                "has_image": employee.image is not None
            }
            
        except Exception as e:
            logger.error(f"Error getting verification status: {e}")
            return {"status": "error", "message": "Failed to get status"}