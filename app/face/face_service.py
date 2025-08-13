"""Face recognition service"""

import cv2
import numpy as np
import face_recognition
import logging
from typing import List, Tuple, Optional, Generator
from dataclasses import dataclass

from .config import FaceRecognitionConfig
from .exceptions import FaceEncodingError, NoFaceFoundError, InvalidImageError
from .cache import FaceEncodingCache

logger = logging.getLogger(__name__)

@dataclass
class FaceMatch:
    """Face match result"""
    is_match: bool
    confidence: float
    distance: float
    location: Tuple[int, int, int, int]  # top, right, bottom, left

@dataclass
class FrameProcessor:
    """Frame processing result"""
    frame: np.ndarray
    matches: List[FaceMatch]
    face_verified: bool

class FaceRecognitionService:
    """Professional face recognition service"""
    
    def __init__(self, config: FaceRecognitionConfig = None):
        self.config = config or FaceRecognitionConfig()
        self.encoding_cache = FaceEncodingCache()
        self._recent_matches: List[bool] = []
        self._frame_count = 0
    
    def create_face_encoding(self, image_data: bytes) -> np.ndarray:
        """Create face encoding from image data"""
        try:
            # Decode image
            np_img = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
            
            if image is None:
                raise InvalidImageError("Could not decode image data")
            
            # Convert to RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Find face encodings
            face_locations = face_recognition.face_locations(rgb_image, model=self.config.MODEL)
            if not face_locations:
                raise NoFaceFoundError("No face found in the image")
            
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
            if not face_encodings:
                raise NoFaceFoundError("Could not generate face encoding")
            
            # Return first encoding (assuming single face per employee image)
            return face_encodings[0]
            
        except Exception as e:
            if isinstance(e, FaceEncodingError):
                raise
            raise FaceEncodingError(f"Failed to create face encoding: {e}")
    
    def load_employee_encoding(self, employee_id: int, image_data: bytes) -> None:
        """Load and cache employee face encoding"""
        if employee_id in self.encoding_cache:
            logger.info(f"Face encoding already cached for employee {employee_id}")
            return
        
        encoding = self.create_face_encoding(image_data)
        self.encoding_cache.set(employee_id, encoding)
        logger.info(f"Face encoding cached for employee {employee_id}")
    
    def process_frame(self, frame: np.ndarray, employee_id: int) -> FrameProcessor:
        """Process frame for face recognition"""
        self._frame_count += 1
        
        # Get known encoding
        known_encoding = self.encoding_cache.get(employee_id)
        if known_encoding is None:
            raise FaceEncodingError(f"No encoding found for employee {employee_id}")
        
        matches = []
        should_process = (self._frame_count % self.config.PROCESS_EVERY_N_FRAMES == 0)
        
        if should_process:
            matches = self._detect_faces(frame, known_encoding)
            
            # Update recent matches for stability
            current_frame_matches = [match.is_match for match in matches]
            self._recent_matches.extend(current_frame_matches)
            
            if len(self._recent_matches) > self.config.MAX_RECENT_FRAMES:
                self._recent_matches = self._recent_matches[-self.config.MAX_RECENT_FRAMES:]
        
        # Draw face rectangles and labels
        processed_frame = self._draw_face_annotations(frame, matches, employee_id)
        
        # Check verification status
        face_verified = self._is_face_verified()
        
        return FrameProcessor(
            frame=processed_frame,
            matches=matches,
            face_verified=face_verified
        )
    
    def _detect_faces(self, frame: np.ndarray, known_encoding: np.ndarray) -> List[FaceMatch]:
        """Detect and match faces in frame"""
        matches = []
        
        try:
            # Resize for faster processing
            small_frame = cv2.resize(frame, (0, 0), fx=self.config.SCALE_FACTOR, fy=self.config.SCALE_FACTOR)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Find faces
            face_locations = face_recognition.face_locations(rgb_small_frame, model=self.config.MODEL)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            
            for face_encoding, face_location in zip(face_encodings, face_locations):
                # Compare faces
                face_matches = face_recognition.compare_faces([known_encoding], face_encoding, tolerance=self.config.TOLERANCE)
                face_distances = face_recognition.face_distance([known_encoding], face_encoding)
                
                # Scale back face location
                top, right, bottom, left = [int(coord / self.config.SCALE_FACTOR) for coord in face_location]
                
                is_match = face_matches[0] and face_distances[0] < self.config.TOLERANCE
                confidence = (1 - face_distances[0]) * 100 if is_match else 0
                
                matches.append(FaceMatch(
                    is_match=is_match,
                    confidence=confidence,
                    distance=face_distances[0],
                    location=(top, right, bottom, left)
                ))
                
        except Exception as e:
            logger.error(f"Face detection error: {e}")
        
        return matches
    
    def _draw_face_annotations(self, frame: np.ndarray, matches: List[FaceMatch], employee_id: int) -> np.ndarray:
        """Draw face rectangles and labels on frame"""
        annotated_frame = frame.copy()
        
        for match in matches:
            top, right, bottom, left = match.location
            
            if match.is_match:
                color = (0, 255, 0)  # Green
                label = "MATCH"
                thickness = 3
            else:
                color = (0, 0, 255)  # Red
                label = "UNKNOWN"
                thickness = 2
            
            # Draw rectangle
            cv2.rectangle(annotated_frame, (left, top), (right, bottom), color, thickness)
            
            # Draw label with background
            text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            cv2.rectangle(annotated_frame, (left, top - text_size[1] - 10), 
                         (left + text_size[0], top), color, -1)
            cv2.putText(annotated_frame, label, (left, top - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Add employee info overlay
        self._add_employee_overlay(annotated_frame, employee_id, self._is_face_verified())
        
        return annotated_frame
    
    def _add_employee_overlay(self, frame: np.ndarray, employee_id: int, verified: bool) -> None:
        """Add employee information overlay"""
        overlay_height = 80 if verified else 50
        cv2.rectangle(frame, (10, 10), (400, 10 + overlay_height), (0, 0, 0), -1)
        
        cv2.putText(frame, f"Employee ID: {employee_id}", (15, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        if verified:
            cv2.putText(frame, "✅ FACE VERIFIED", (15, 65),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    def _is_face_verified(self) -> bool:
        """Check if face is verified based on recent matches"""
        if len(self._recent_matches) < self.config.MAX_RECENT_FRAMES:
            return False
        
        match_ratio = sum(self._recent_matches) / len(self._recent_matches)
        return match_ratio >= self.config.VERIFICATION_THRESHOLD
    
    def reset_verification_state(self) -> None:
        """Reset verification state for new session"""
        self._recent_matches.clear()
        self._frame_count = 0
    
    def clear_cache(self) -> None:
        """Clear encoding cache"""
        self.encoding_cache.clear()
        