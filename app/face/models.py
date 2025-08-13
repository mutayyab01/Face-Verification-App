"""Database models for face recognition module"""

import logging
from typing import Optional, List, Dict, Any
from app.database import DatabaseManager
from .exceptions import DatabaseError

logger = logging.getLogger(__name__)

class EmployeeFaceModel:
    """Employee model for face recognition"""
    
    def __init__(self, employee_id: int, nucleus_id: str, name: str, 
                 father_name: str, image: bytes = None, is_active: bool = True):
        self.employee_id = employee_id
        self.nucleus_id = nucleus_id
        self.name = name
        self.father_name = father_name
        self.image = image
        self.is_active = is_active
    
    @classmethod
    def get_by_id(cls, employee_id: int) -> Optional['EmployeeFaceModel']:
        """Get employee by ID with image data"""
        try:
            conn = DatabaseManager.get_connection()
            if not conn:
                raise DatabaseError("Database connection failed")
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT NucleusId, Name, FatherName, Image, IsActive
                FROM Employee 
                WHERE NucleusId = ? AND IsActive = 1
            """, (employee_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            return cls(
                employee_id=employee_id,
                nucleus_id=result[0],
                name=result[1],
                father_name=result[2],
                image=result[3],
                is_active=result[4]
            )
            
        except Exception as e:
            logger.error(f"Error fetching employee {employee_id}: {e}")
            raise DatabaseError(f"Failed to fetch employee: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
    
    @classmethod
    def get_all_with_images(cls) -> List['EmployeeFaceModel']:
        """Get all active employees with images"""
        try:
            conn = DatabaseManager.get_connection()
            if not conn:
                raise DatabaseError("Database connection failed")
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT NucleusId, Name, FatherName, Image 
                FROM Employee 
                WHERE IsActive = 1 AND Image IS NOT NULL
                ORDER BY Name
            """)
            
            results = cursor.fetchall()
            employees = []
            
            for result in results:
                employees.append(cls(
                    employee_id=result[0],
                    nucleus_id=result[0],
                    name=result[1],
                    father_name=result[2],
                    image=result[3]
                ))
            
            return employees
            
        except Exception as e:
            logger.error(f"Error fetching employees: {e}")
            raise DatabaseError(f"Failed to fetch employees: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
    
    @property
    def Image(self) -> Optional[bytes]:
        """Property for backward compatibility"""
        return self.image

class WagesModel:
    """Wages model for payment verification"""
    
    def __init__(self, wages_id: int, nucleus_id: str, name: str, 
                 father_name: str, amount: float, is_paid: bool = False):
        self.wages_id = wages_id
        self.nucleus_id = nucleus_id
        self.name = name
        self.father_name = father_name
        self.amount = amount
        self.is_paid = is_paid
    
    @classmethod
    def get_by_nucleus_id(cls, nucleus_id: str) -> Optional['WagesModel']:
        """Get wages record by nucleus ID"""
        try:
            conn = DatabaseManager.get_connection()
            if not conn:
                raise DatabaseError("Database connection failed")
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT Id, NucleusId, Name, FatherName, Amount, IsPaid
                FROM WagesUpload 
                WHERE NucleusId = ?
            """, (nucleus_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            return cls(
                wages_id=result[0],
                nucleus_id=result[1],
                name=result[2],
                father_name=result[3],
                amount=result[4],
                is_paid=bool(result[5])
            )
            
        except Exception as e:
            logger.error(f"Error fetching wages for {nucleus_id}: {e}")
            raise DatabaseError(f"Failed to fetch wages: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
    
    def mark_as_paid(self) -> bool:
        """Mark wages as paid"""
        try:
            conn = DatabaseManager.get_connection()
            if not conn:
                raise DatabaseError("Database connection failed")
            
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE WagesUpload 
                SET IsPaid = 1 
                WHERE NucleusId = ?
            """, (self.nucleus_id,))
            
            conn.commit()
            self.is_paid = True
            
            logger.info(f"Wages marked as paid for {self.name} (NucleusId: {self.nucleus_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error updating wages payment: {e}")
            raise DatabaseError(f"Failed to update wages: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
    
    @classmethod
    def get_all_unpaid(cls) -> List['WagesModel']:
        """Get all unpaid wages"""
        try:
            conn = DatabaseManager.get_connection()
            if not conn:
                raise DatabaseError("Database connection failed")
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT Id, NucleusId, Name, FatherName, Amount, IsPaid
                FROM WagesUpload 
                WHERE IsPaid = 0
                ORDER BY Name
            """)
            
            results = cursor.fetchall()
            wages = []
            
            for result in results:
                wages.append(cls(
                    wages_id=result[0],
                    nucleus_id=result[1],
                    name=result[2],
                    father_name=result[3],
                    amount=result[4],
                    is_paid=bool(result[5])
                ))
            
            return wages
            
        except Exception as e:
            logger.error(f"Error fetching unpaid wages: {e}")
            raise DatabaseError(f"Failed to fetch unpaid wages: {e}")
        finally:
            if 'conn' in locals():
                conn.close()