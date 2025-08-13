"""Custom exceptions for face recognition module"""

class FaceRecognitionError(Exception):
    """Base exception for face recognition module"""
    pass

class CameraError(FaceRecognitionError):
    """Camera related errors"""
    pass

class CameraNotFoundError(CameraError):
    """No working camera found"""
    pass

class CameraInitializationError(CameraError):
    """Camera initialization failed"""
    pass

class FaceEncodingError(FaceRecognitionError):
    """Face encoding related errors"""
    pass

class NoFaceFoundError(FaceEncodingError):
    """No face found in image"""
    pass

class InvalidImageError(FaceEncodingError):
    """Invalid image data"""
    pass

class DatabaseError(FaceRecognitionError):
    """Database related errors"""
    pass