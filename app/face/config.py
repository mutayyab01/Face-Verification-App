"""Configuration settings for face recognition module"""

from dataclasses import dataclass
from typing import List
FACE_RECOGNITION_CONFIG = {
    "MODEL": "hog",  # or 'cnn' for GPU
    "VERIFICATION_THRESHOLD": 0.6,
    "MAX_RECENT_MATCHES": 5
}
@dataclass
class CameraConfig:
    """Camera configuration constants"""
    FRAME_WIDTH: int = 640
    FRAME_HEIGHT: int = 480
    FPS: int = 15
    BUFFER_SIZE: int = 1
    JPEG_QUALITY: int = 85
    BACKENDS: List[int] = None
    TIMEOUT: float = 5.0
    MAX_CAMERA_SEARCH: int = 3
    
    def __post_init__(self):
        if self.BACKENDS is None:
            import cv2
            self.BACKENDS = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]

@dataclass
class FaceRecognitionConfig:
    """Face recognition configuration"""
    SCALE_FACTOR: float = 0.4
    TOLERANCE: float = 0.5
    VERIFICATION_THRESHOLD: float = 0.8
    MAX_RECENT_FRAMES: int = 10
    PROCESS_EVERY_N_FRAMES: int = 2
    MODEL: str = "hog"  # or "cnn" for better accuracy but slower

@dataclass
class AppConfig:
    """Application configuration"""
    MAX_NO_FRAME_COUNT: int = 100
    THREAD_JOIN_TIMEOUT: float = 5.0
    CACHE_SIZE_LIMIT: int = 100
