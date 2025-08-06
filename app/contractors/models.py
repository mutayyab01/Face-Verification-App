from app.database import DatabaseManager
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ContractorModel:
    @staticmethod
    def get_all():
        """Get all contractors"""
        return DatabaseManager.execute_query("""
            SELECT c.Id, c.Name, c.FatherName, c.Address, c.IsActive,
                u1.Email as CreatedByEmail, c.CreatedAt,
                u2.Email as UpdatedByEmail, c.UpdatedAt
            FROM Contractor c
            LEFT JOIN [User] u1 ON c.CreatedBy = u1.Id
            LEFT JOIN [User] u2 ON c.UpdatedBy = u2.Id
            ORDER BY c.Name
        """, fetch_all=True)
    
    @staticmethod
    def get_active():
        """Get active contractors for dropdown"""
        return DatabaseManager.execute_query(
            "SELECT Id, Name FROM Contractor WHERE IsActive = 1 ORDER BY Name",
            fetch_all=True
        )
    
    @staticmethod
    def get_by_id(contractor_id):
        """Get contractor by ID"""
        return DatabaseManager.execute_query(
            "SELECT * FROM Contractor WHERE Id = ?",
            (contractor_id,),
            fetch_one=True
        )
    
    @staticmethod
    def create(data, created_by):
        """Create new contractor"""
        return DatabaseManager.execute_query("""
            INSERT INTO Contractor (Name, FatherName, Address, PhoneNo, IsActive, CreatedBy, CreatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data['name'], data['father_name'], data.get('address'),
            data.get('phone_no'), data['is_active'], created_by, datetime.now()
        ))
    
    @staticmethod
    def update(contractor_id, data, updated_by):
        """Update contractor"""
        return DatabaseManager.execute_query("""
            UPDATE Contractor 
            SET Name = ?, FatherName = ?, Address = ?, IsActive = ?, 
                UpdatedBy = ?, UpdatedAt = ?
            WHERE Id = ?
        """, (
            data['name'], data['father_name'], data.get('address'),
            data['is_active'], updated_by, datetime.now(), contractor_id
        ))
    
    @staticmethod
    def delete(contractor_id):
        """Delete contractor"""
        return DatabaseManager.execute_query(
            "DELETE FROM Contractor WHERE Id = ?",
            (contractor_id,)
        )