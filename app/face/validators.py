# =============================================================================
# app/face/validators.py
# =============================================================================
"""Input validation for face recognition module"""

import re
from typing import Any, Dict, List, Optional, Tuple
from flask import request
from .exceptions import FaceRecognitionError

class ValidationError(FaceRecognitionError):
    """Validation error"""
    pass

class RequestValidator:
    """Request validation utilities"""
    
    @staticmethod
    def validate_employee_id(employee_id: Any) -> int:
        """Validate employee ID"""
        if employee_id is None:
            raise ValidationError("Employee ID is required")
        
        try:
            emp_id = int(employee_id)
            if emp_id <= 0:
                raise ValidationError("Employee ID must be positive")
            return emp_id
        except (ValueError, TypeError):
            raise ValidationError("Invalid employee ID format")
    
    @staticmethod
    def validate_image_data(image_data: bytes) -> None:
        """Validate image data"""
        if not image_data:
            raise ValidationError("Image data is required")
        
        # Check minimum size (1KB)
        if len(image_data) < 1024:
            raise ValidationError("Image data too small")
        
        # Check maximum size (5MB)
        if len(image_data) > 5 * 1024 * 1024:
            raise ValidationError("Image data too large (max 5MB)")
        
        # Check for basic image headers
        image_headers = [
            b'\xff\xd8\xff',  # JPEG
            b'\x89PNG\r\n\x1a\n',  # PNG
            b'BM',  # BMP
        ]
        
        if not any(image_data.startswith(header) for header in image_headers):
            raise ValidationError("Invalid image format")
    
    @staticmethod
    def validate_nucleus_id(nucleus_id: str) -> str:
        """Validate nucleus ID format"""
        if not nucleus_id:
            raise ValidationError("Nucleus ID is required")
        
        # Assuming nucleus ID format (adjust as needed)
        if not re.match(r'^[A-Z0-9]{3,20}$', nucleus_id):
            raise ValidationError("Invalid nucleus ID format")
        
        return nucleus_id.strip().upper()
    
    @staticmethod
    def validate_request_data(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        """Validate request data for required fields"""
        validated_data = {}
        
        for field in required_fields:
            if field not in data or data[field] is None:
                raise ValidationError(f"Field '{field}' is required")
            validated_data[field] = data[field]
        
        return validated_data
    
    @staticmethod
    def validate_file_upload(file_data: bytes, allowed_extensions: List[str] = None) -> None:
        """Validate uploaded file"""
        if allowed_extensions is None:
            allowed_extensions = ['jpg', 'jpeg', 'png', 'bmp']
        
        # Validate image data
        RequestValidator.validate_image_data(file_data)
        
        # Additional file validation can be added here
        pass
    
    @staticmethod
    def sanitize_string(input_str: str, max_length: int = 255) -> str:
        """Sanitize and validate string input"""
        if not isinstance(input_str, str):
            raise ValidationError("Input must be a string")
        
        # Remove leading/trailing whitespace
        sanitized = input_str.strip()
        
        # Check length
        if len(sanitized) > max_length:
            raise ValidationError(f"Input too long (max {max_length} characters)")
        
        # Remove potentially dangerous characters (adjust as needed)
        sanitized = re.sub(r'[<>"\']', '', sanitized)
        
        return sanitized
    
    @staticmethod
    def validate_pagination_params(page: Any, per_page: Any) -> Tuple[int, int]:
        """Validate pagination parameters"""
        try:
            page_num = int(page) if page else 1
            per_page_num = int(per_page) if per_page else 10
            
            if page_num < 1:
                raise ValidationError("Page number must be positive")
            
            if per_page_num < 1 or per_page_num > 100:
                raise ValidationError("Items per page must be between 1 and 100")
            
            return page_num, per_page_num
            
        except (ValueError, TypeError):
            raise ValidationError("Invalid pagination parameters")

class FormValidator:
    """HTML form validation utilities"""
    
    @staticmethod
    def validate_employee_form(form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate employee form data"""
        required_fields = ['employee_id']
        validated = RequestValidator.validate_request_data(form_data, required_fields)
        
        # Validate employee ID
        validated['employee_id'] = RequestValidator.validate_employee_id(validated['employee_id'])
        
        return validated
    
    @staticmethod
    def validate_search_form(form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate search form data"""
        validated = {}
        
        if 'query' in form_data and form_data['query']:
            validated['query'] = RequestValidator.sanitize_string(form_data['query'], 100)
        
        if 'page' in form_data or 'per_page' in form_data:
            validated['page'], validated['per_page'] = RequestValidator.validate_pagination_params(
                form_data.get('page'), form_data.get('per_page')
            )
        
        return validated

class APIValidator:
    """API request validation utilities"""
    
    @staticmethod
    def validate_json_request(required_fields: List[str] = None, optional_fields: List[str] = None) -> Dict[str, Any]:
        """Validate JSON request data"""
        if not request.is_json:
            raise ValidationError("Request must be JSON")
        
        data = request.get_json()
        if not data:
            raise ValidationError("No JSON data provided")
        
        validated = {}
        
        # Validate required fields
        if required_fields:
            for field in required_fields:
                if field not in data or data[field] is None:
                    raise ValidationError(f"Required field '{field}' missing")
                validated[field] = data[field]
        
        # Validate optional fields
        if optional_fields:
            for field in optional_fields:
                if field in data and data[field] is not None:
                    validated[field] = data[field]
        
        return validated
    
    @staticmethod
    def validate_employee_api_request() -> Dict[str, Any]:
        """Validate employee API request"""
        data = APIValidator.validate_json_request(['employee_id'])
        data['employee_id'] = RequestValidator.validate_employee_id(data['employee_id'])
        return data
    
    @staticmethod
    def validate_verification_request() -> Dict[str, Any]:
        """Validate verification API request"""
        data = APIValidator.validate_json_request(['employee_id'], ['force_verify'])
        data['employee_id'] = RequestValidator.validate_employee_id(data['employee_id'])
        
        if 'force_verify' in data:
            if not isinstance(data['force_verify'], bool):
                raise ValidationError("force_verify must be a boolean")
        
        return data