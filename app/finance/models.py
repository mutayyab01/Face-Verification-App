from app.database import DatabaseManager
from datetime import datetime
import logging
import base64  # ✅ Import for base64 encoding

logger = logging.getLogger(__name__)

class WagesUploadModel:
      @staticmethod
      def delete_existing_record_with_unitId(unitId: int):
          try:
              conn = DatabaseManager.get_connection()
              if conn:
                  logger.info(f"Deleting existing records for UnitId {unitId} created today: {datetime.now().date()}")
                  cursor = conn.cursor()
                  cursor.execute("""
                      DELETE FROM WagesUpload
                      WHERE UnitId = ? and CAST([CreatedAt] AS DATE) = ?;
                  """, (unitId, datetime.now().date()))
                  conn.commit()
          except Exception as e:
              logger.error(f"Failed to delete record with UnitId {unitId}: {e}")
              conn.rollback()
              conn.close()
              return False
          return True
    
      @staticmethod
      def get_latest_record_by_unit(unitId: int):
        """
        Fetch the latest WagesUpload record for the given UnitId on today's date.
        """
        try:
            conn = DatabaseManager.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT 
                NucleusId,
                ContractorId,
                LabourName,
                ContractorName,
                Amount,
                CASE WHEN IsPaid = 1 THEN 1 ELSE 0 END AS IsPaid,   -- force into 0/1
                CASE WHEN IsPaid = 1 THEN 'Yes' ELSE 'No' END AS IsPaidText,
                UnitId,
                CreatedBy,
                CreatedAt
                FROM WagesUpload
                WHERE UnitId = ?
                AND CAST(CreatedAt AS DATE) = ?
                """, (unitId, datetime.now().date()))
                
                record = cursor.fetchall()
                conn.close()
                return record  # returns None if no record found
        except Exception as e:
            logger.error(f"Failed to fetch latest record for UnitId {unitId}: {e}")
            if conn:
                conn.close()
            return None
        return None