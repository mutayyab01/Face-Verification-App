"""Tests for camera service"""

import unittest
from unittest.mock import patch, MagicMock
from ..camera_service import CameraService
from ..exceptions import CameraError, CameraNotFoundError

class TestCameraService(unittest.TestCase):
    """Test cases for CameraService"""
    
    def setUp(self):
        self.camera_service = CameraService()
    
    def tearDown(self):
        self.camera_service.stop()
    
    @patch('cv2.VideoCapture')
    def test_find_working_camera_success(self, mock_video_capture):
        """Test successful camera detection"""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, MagicMock())
        mock_video_capture.return_value = mock_cap
        
        camera_index, backend = self.camera_service._find_working_camera()
        self.assertEqual(camera_index, 0)
    
    @patch('cv2.VideoCapture')
    def test_find_working_camera_not_found(self, mock_video_capture):
        """Test camera not found scenario"""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_video_capture.return_value = mock_cap
        
        with self.assertRaises(CameraNotFoundError):
            self.camera_service._find_working_camera()
    
    def test_start_stop_camera(self):
        """Test camera start and stop"""
        # Mock successful start
        with patch.object(self.camera_service, '_find_working_camera', return_value=(0, 0)):
            with patch('cv2.VideoCapture') as mock_cap:
                mock_instance = MagicMock()
                mock_instance.isOpened.return_value = True
                mock_instance.read.return_value = (True, MagicMock())
                mock_cap.return_value = mock_instance
                
                self.camera_service.start(123)
                self.assertTrue(self.camera_service.is_running)
                self.assertEqual(self.camera_service.current_employee_id, 123)
                
                self.camera_service.stop()
                self.assertFalse(self.camera_service.is_running)

if __name__ == '__main__':
    unittest.main()