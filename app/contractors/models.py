from app.database import DatabaseManager
from datetime import datetime
import logging
import base64  # ✅ Import for base64 encoding

logger = logging.getLogger(__name__)


class ContractorModel:
    @staticmethod
    def get_unit():
        """Get all Unit"""
        return DatabaseManager.execute_query("""
            SELECT Id, Name FROM Unit
        """, fetch_all=True)
    
    @staticmethod
    def get_all():
        """Get all contractors with base64-encoded profile image"""
        try:
            raw_contractors = DatabaseManager.execute_query("""
                SELECT c.Id, c.Name, c.FatherName, c.PhoneNo, c.UnitId,
                    c.Image, c.Address, c.IsActive,
                    u1.Email as CreatedByEmail, c.CreatedAt,
                    u2.Email as UpdatedByEmail, c.UpdatedAt
                FROM Contractor c
                LEFT JOIN [User] u1 ON c.CreatedBy = u1.Id
                LEFT JOIN [User] u2 ON c.UpdatedBy = u2.Id
                ORDER BY c.Name
            """, fetch_all=True)
            
            contractors = []
            for con in raw_contractors:
                image_data = None
                # Check if image exists and handle potential None/NULL values
                if con[5] is not None and len(con[5]) > 0:
                    try:
                        # Ensure the image data is in bytes format
                        if isinstance(con[5], str):
                            # If it's already a string, assume it's base64
                            image_data = "data:image/jpeg;base64," + con[5]
                        else:
                            # If it's bytes, encode it
                            image_data = "data:image/jpeg;base64," + base64.b64encode(con[5]).decode('utf-8')
                    except Exception as img_error:
                        print(f"Error processing image for contractor {con[0]}: {img_error}")
                        image_data = None
                
                contractors.append((
                    con[0],  # Id
                    con[1],  # Name
                    con[2],  # FatherName
                    con[3],  # PhoneNo
                    con[4],  # Unit
                    image_data,  # Base64 Profile Image
                    con[6],  # Address
                    con[7],  # IsActive
                    con[8],  # CreatedByEmail
                    con[9],  # CreatedAt
                    con[10], # UpdatedByEmail
                    con[11], # UpdatedAt
                ))
            
            return contractors
            
        except Exception as e:
            print(f"Error in get_all(): {e}")
            return []
        
     
    @staticmethod
    def get_active_contractors():
        """Get active contractors for dropdown"""
        return DatabaseManager.execute_query(
            "SELECT ContractorId, Name FROM Contractor WHERE IsActive = 1 ORDER BY Name",
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
    def exists_Contractor_Id(contractor_id):
        """Check if a given ContractorId already exists in the Contractor table."""
        result = DatabaseManager.execute_query(
            "SELECT 1 FROM Contractor WHERE ContractorId = ?",
            (contractor_id,),
            fetch_one=True
        )
        return result is not None
    

    @staticmethod
    def create(data, created_by):
        """Create new contractor"""
        return DatabaseManager.execute_query("""
            INSERT INTO Contractor (ContractorId, Name, FatherName, PhoneNo, UnitId, Image, Address, IsActive, CreatedBy, CreatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['ContractorId'], data['Name'], data['FatherName'], data['PhoneNumber'],
            data['Unit'], data['ProfileImage'], data['Address'], data['IsActive'], created_by, datetime.now()
        ))
    
    @staticmethod
    def update(contractor_id, data, updated_by):
        """Update contractor with optional image"""
         
        logger.info(f"Update data: {data}")
        logger.info(f"Contractor ID: {contractor_id}")

        if data['ProfileImage']:  # If a new image is provided
            return DatabaseManager.execute_query("""
                UPDATE Contractor
                SET ContractorId = ?, Name = ?, FatherName = ?, 
                    PhoneNo = ?, UnitId = ?, Image = ?, Address = ?, 
                    IsActive = ?, UpdatedBy = ?, UpdatedAt = ?
                WHERE Id = ?
            """, (
                data['ContractorId'], data['Name'], data['FatherName'], data['PhoneNumber'],
                data['Unit'], data['ProfileImage'], data['Address'],
                data['IsActive'], updated_by, datetime.now(), contractor_id
            ))
        else:  # Keep the existing image
            return DatabaseManager.execute_query("""
                UPDATE Contractor
                SET ContractorId = ?, Name = ?, FatherName = ?, 
                    PhoneNo = ?, UnitId = ?, Address = ?, 
                    IsActive = ?, UpdatedBy = ?, UpdatedAt = ?
                WHERE Id = ?
            """, (
                data['ContractorId'], data['Name'], data['FatherName'], data['PhoneNumber'],
                data['Unit'], data['Address'],
                data['IsActive'], updated_by, datetime.now(), contractor_id
            ))

        
    @staticmethod
    def delete(contractor_id):
        """Delete contractor"""
        return DatabaseManager.execute_query(
            "DELETE FROM Contractor WHERE Id = ?",
            (contractor_id,)
        )