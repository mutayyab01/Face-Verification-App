from app.database import DatabaseManager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class EmployeeFaceModel:
    @staticmethod
    def get_by_id(employee_id):
        """Get employee by ID"""
        return DatabaseManager.execute_query(
            "SELECT * FROM Employee WHERE NucleusId = ?",
            (employee_id,),
            fetch_one=True
        )