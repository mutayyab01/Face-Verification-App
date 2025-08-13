"""Tests for face recognition service"""

import unittest
import numpy as np
from unittest.mock import patch, MagicMock
from ..face_service import FaceRecognitionService
from ..exceptions import FaceEncodingError, NoFaceFoundError

class TestFaceRecognitionService(unittest.TestCase):
    """Test cases for FaceRecognitionService"""
    
    def setUp(self):
        self.face_service = FaceRecognitionService()
    
    @patch('face_recognition.face_locations')
    @patch('face_recognition.face_encodings')
    @patch('cv2.imdecode')
    @patch('cv2.cvtColor')
    def test_create_face_encoding_success(self, mock_cvt_color, mock_imdecode, 
                                         mock_face_encodings, mock_face_locations):
        """Test successful face encoding creation"""
        # Mock image processing
        mock_imdecode.return_value = MagicMock()
        mock_cvt_color.return_value = MagicMock()
        mock_face_locations.return_value = [(0, 100, 100, 0)]
        mock_face_encodings.return_value = [np.array([1, 2, 3])]
        
        image_data = b'fake_image_data'
        encoding = self.face_service.create_face_encoding(image_data)
        
        self.assertIsInstance(encoding, np.ndarray)
        np.testing.assert_array_equal(encoding, np.array([1, 2, 3]))
    
    @patch('face_recognition.face_locations')
    @patch('cv2.imdecode')
    @patch('cv2.cvtColor')
    def test_create_face_encoding_no_face(self, mock_cvt_color, mock_imdecode, mock_face_locations):
        """Test face encoding when no face found"""
        mock_imdecode.return_value = MagicMock()
        mock_cvt_color.return_value = MagicMock()
        mock_face_locations.return_value = []  # No faces found
        
        image_data = b'fake_image_data'
        
        with self.assertRaises(NoFaceFoundError):
            self.face_service.create_face_encoding(image_data)
    
    def test_load_employee_encoding(self):
        """Test loading employee encoding"""
        with patch.object(self.face_service, 'create_face_encoding') as mock_create:
            mock_create.return_value = np.array([1, 2, 3])
            
            employee_id = 123
            image_data = b'fake_image_data'
            
            self.face_service.load_employee_encoding(employee_id, image_data)
            
            self.assertIn(employee_id, self.face_service.encoding_cache)
            encoding = self.face_service.encoding_cache.get(employee_id)
            np.testing.assert_array_equal(encoding, np.array([1, 2, 3]))

if __name__ == '__main__':
    unittest.main()