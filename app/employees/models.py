from sqlite3 import DatabaseError
from app.database import DatabaseManager
from datetime import datetime
import logging
import base64  # ✅ Import for base64 encoding

logger = logging.getLogger(__name__)

class EmployeeModel:
    @staticmethod
    def get_all():
        """Get all employees with contractor information, including base64 image"""
        raw_employees = DatabaseManager.execute_query("""
              SELECT e.Id, e.NucleusId, e.Name, e.FatherName, e.PhoneNo, e.Address, 
                (c.Name + ' ' + c.FatherName) as ContractorName, u.Name as UnitName, e.IsActive,
                u1.Email as CreatedByEmail, e.CreatedAt,
                u2.Email as UpdatedByEmail, e.UpdatedAt
            FROM Employee e
            LEFT JOIN Contractor c ON e.ContractorId = c.ContractorId
            LEFT JOIN Unit u ON e.UnitId = u.Id
            LEFT JOIN [User] u1 ON e.CreatedBy = u1.Id
            LEFT JOIN [User] u2 ON e.UpdatedBy = u2.Id
            ORDER BY e.Id DESC
        """, fetch_all=True)
            
        return raw_employees

    @staticmethod
    def exists_nucleus_id(nucleus_id):
        """Check if a given NucleusId already exists in the Employee table."""
        result = DatabaseManager.execute_query(
            "SELECT 1 FROM Employee WHERE NucleusId = ?",
            (nucleus_id,),
            fetch_one=True
        )
        return result is not None


    @staticmethod
    def get_by_id(employee_id):
        """Get employee by ID with Base64 image conversion"""
        employee = DatabaseManager.execute_query(
            "SELECT * FROM Employee WHERE Id = ?",
            (employee_id,),
            fetch_one=True
        )

        if employee:
            employee = list(employee)  # convert tuple to list so we can modify it

            # If Image column exists and is not None, convert to Base64
            if employee[8]:
                employee[8] = base64.b64encode(employee[8]).decode('utf-8')

        return employee


    @staticmethod
    def create(data, created_by):
        """Create new employee"""
        return DatabaseManager.execute_query("""
            INSERT INTO Employee (NucleusId, Name, FatherName, PhoneNo, Address, ContractorId, UnitId, Image, IsActive, CreatedBy, CreatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['NucleusId'], data['Name'], data['FatherName'], data['PhoneNumber'],
            data['Address'], data.get('ContractorId'), data['Unit'], data['image'], data['IsActive'],
            created_by, datetime.now()
        ))

    @staticmethod
    def update(employee_id, data, updated_by):
        """Update employee with optional image"""        
        if data['image']:
            return DatabaseManager.execute_query("""
                UPDATE Employee 
                SET Name = ?, FatherName = ?, 
                    PhoneNo = ?, Address = ?, 
                    ContractorId = ?, UnitId = ?, Image = ?, IsActive = ?, 
                    UpdatedBy = ?, UpdatedAt = ?
                WHERE Id = ?
            """, (
                data['Name'], data['FatherName'], data['PhoneNumber'],
                data['Address'], data['ContractorId'], data['Unit'], data['image'],
                data['IsActive'], updated_by, datetime.now(), employee_id
            ))
        else:
            return DatabaseManager.execute_query("""
                UPDATE Employee 
                SET Name = ?, FatherName = ?, 
                    PhoneNo = ?, Address = ?, 
                    ContractorId = ?, UnitId = ?, IsActive = ?, 
                    UpdatedBy = ?, UpdatedAt = ?
                WHERE Id = ?
            """, (
                data['Name'], data['FatherName'], data['PhoneNumber'],
                data['Address'], data['ContractorId'], data['Unit'],
                data['IsActive'], updated_by, datetime.now(), employee_id
            ))

    @staticmethod
    def delete(employee_id):
        """Delete employee"""
        return DatabaseManager.execute_query(
            "DELETE FROM Employee WHERE Id = ?",
            (employee_id,)
        )



