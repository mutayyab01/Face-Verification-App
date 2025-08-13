"""Camera management service"""

import cv2
import threading
import numpy as np
import time
import logging
from typing import Optional, Tuple, Callable, Generator
from contextlib import contextmanager

from .config import CameraConfig, AppConfig
from .exceptions import CameraError, CameraNotFoundError, CameraInitializationError

logger = logging.getLogger(__name__)

class CameraService:
    """Professional camera service with proper resource management"""
    
    def __init__(self, config: CameraConfig = None):
        self.config = config or CameraConfig()
        self._lock = threading.RLock()
        self._video_capture: Optional[cv2.VideoCapture] = None
        self._camera_thread: Optional[threading.Thread] = None
        self._frame_lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._is_running = False
        self._current_employee_id: Optional[int] = None
        self._working_camera_index: Optional[int] = None
        self._stop_event = threading.Event()
    
    @property
    def is_running(self) -> bool:
        """Check if camera is running"""
        with self._lock:
            return self._is_running
    
    @property
    def current_employee_id(self) -> Optional[int]:
        """Get current employee ID"""
        with self._lock:
            return self._current_employee_id
    
    def _find_working_camera(self) -> Tuple[int, int]:
        """Find working camera with backend selection"""
        # Try cached camera first
        if self._working_camera_index is not None:
            for backend in self.config.BACKENDS:
                if self._test_camera(self._working_camera_index, backend):
                    logger.info(f"Using cached camera {self._working_camera_index}")
                    return self._working_camera_index, backend
            # Cache invalid, reset
            self._working_camera_index = None
        
        # Search for working camera
        logger.info("Searching for working camera...")
        for camera_index in range(self.config.MAX_CAMERA_SEARCH):
            for backend in self.config.BACKENDS:
                if self._test_camera(camera_index, backend):
                    logger.info(f"Found camera at index {camera_index}")
                    self._working_camera_index = camera_index
                    return camera_index, backend
        
        raise CameraNotFoundError("No working camera found")
    
    def _test_camera(self, camera_index: int, backend: int) -> bool:
        """Test if camera works with given backend"""
        try:
            cap = cv2.VideoCapture(camera_index, backend)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                return ret and frame is not None
        except Exception as e:
            logger.debug(f"Camera test failed for index {camera_index}: {e}")
        return False
    
    def _configure_camera(self, capture: cv2.VideoCapture) -> bool:
        """Configure camera properties"""
        try:
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.FRAME_WIDTH)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.FRAME_HEIGHT)
            capture.set(cv2.CAP_PROP_FPS, self.config.FPS)
            capture.set(cv2.CAP_PROP_BUFFERSIZE, self.config.BUFFER_SIZE)
            capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            return True
        except Exception as e:
            logger.error(f"Camera configuration failed: {e}")
            return False
    
    def _camera_loop(self) -> None:
        """Camera capture loop running in separate thread"""
        logger.info(f"Camera loop started for employee {self._current_employee_id}")
        
        while not self._stop_event.is_set() and self._is_running:
            try:
                if not self._video_capture or not self._video_capture.isOpened():
                    logger.warning("Video capture unavailable")
                    break
                
                ret, frame = self._video_capture.read()
                if ret and frame is not None:
                    with self._frame_lock:
                        self._latest_frame = frame.copy()
                else:
                    time.sleep(0.01)  # Prevent CPU spinning
                    
            except Exception as e:
                logger.error(f"Camera loop error: {e}")
                break
        
        logger.info("Camera loop ended")
    
    def start(self, employee_id: int) -> None:
        """Start camera for specific employee"""
        with self._lock:
            if self._is_running and self._current_employee_id == employee_id:
                logger.info(f"Camera already running for employee {employee_id}")
                return
            
            # Stop existing session
            if self._is_running:
                self._stop_internal()
                time.sleep(0.5)  # Brief pause for cleanup
            
            try:
                camera_index, backend = self._find_working_camera()
                
                self._video_capture = cv2.VideoCapture(camera_index, backend)
                if not self._video_capture.isOpened():
                    raise CameraInitializationError("Failed to open camera")
                
                if not self._configure_camera(self._video_capture):
                    raise CameraInitializationError("Failed to configure camera")
                
                # Test capture
                success_count = 0
                for _ in range(10):
                    ret, frame = self._video_capture.read()
                    if ret and frame is not None:
                        success_count += 1
                        if success_count >= 3:
                            break
                    time.sleep(0.1)
                
                if success_count < 3:
                    raise CameraInitializationError("Camera capture test failed")
                
                self._is_running = True
                self._current_employee_id = employee_id
                self._stop_event.clear()
                
                self._camera_thread = threading.Thread(
                    target=self._camera_loop, 
                    daemon=True,
                    name=f"CameraThread-{employee_id}"
                )
                self._camera_thread.start()
                
                logger.info(f"Camera started for employee {employee_id}")
                
            except Exception as e:
                self._cleanup_resources()
                raise CameraError(f"Failed to start camera: {e}")
    
    def _stop_internal(self) -> None:
        """Internal stop method without lock"""
        if not self._is_running:
            return
        
        logger.info("Stopping camera...")
        self._is_running = False
        self._stop_event.set()
        
        # Wait for thread to finish
        if self._camera_thread and self._camera_thread.is_alive():
            self._camera_thread.join(timeout=AppConfig.THREAD_JOIN_TIMEOUT)
            if self._camera_thread.is_alive():
                logger.warning("Camera thread did not stop gracefully")
        
        self._cleanup_resources()
    
    def stop(self) -> None:
        """Stop camera and cleanup resources"""
        with self._lock:
            self._stop_internal()
    
    def _cleanup_resources(self) -> None:
        """Cleanup camera resources"""
        if self._video_capture:
            try:
                self._video_capture.release()
            except Exception as e:
                logger.error(f"Error releasing video capture: {e}")
            self._video_capture = None
        
        self._camera_thread = None
        self._latest_frame = None
        self._current_employee_id = None
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get latest captured frame"""
        with self._frame_lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None
    
    @contextmanager
    def camera_session(self, employee_id: int):
        """Context manager for camera session"""
        try:
            self.start(employee_id)
            yield self
        finally:
            self.stop()
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.stop()
        except:
            pass