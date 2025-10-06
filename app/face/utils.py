"""Utility functions for face recognition module"""

import logging
from flask import session
from typing import List, Dict, Any, Generator
from app.database import DatabaseManager
from datetime import datetime
from .face_service import FaceRecognitionService
logger = logging.getLogger(__name__)

def get_upload_data(unit_id: int) -> List[Dict[str, Any]]:
    """Fetch upload data from database where UnitId and today's date match."""
    try:
        conn = DatabaseManager.get_connection()
        if conn:
            cursor = conn.cursor()

            query = """
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
                AND CAST(CreatedAt AS DATE) = (
                SELECT MAX(CAST(CreatedAt AS DATE)) 
                FROM WagesUpload 
                WHERE UnitId = ?
                );
            """
            params = (unit_id, unit_id)
            cursor.execute(query, params)

            # Fetch all rows
            rows = cursor.fetchall()
            if not rows:
                return []
            return rows

    except Exception as e:
        logger.error(f"Failed to fetch upload data: {e}")

    return []


def mark_labour_as_paid_for_code(unit_id: int, target_date: datetime.date, nucleus_id: int) -> bool:
    """
    Update WagesUpload by setting IsPaid = 1 
    for a given UnitId and CreatedAt date (latest record).
    
    Args:
        unit_id (int): The Unit ID.
        target_date (datetime.date): The date to filter on.

    Returns:
        bool: True if rows were updated, False otherwise.
    """
    try:
        conn = DatabaseManager.get_connection()
        if conn:
            cursor = conn.cursor()

            query = """
                UPDATE WagesUpload
SET VerifyType = 'Code',
    UpdatedBy = ?,
    UpdatedAt = ?
WHERE UnitId = ?
  AND CAST(CreatedAt AS DATE) = ?
  AND NucleusId = ?
                  
            """
            params = (session['user_id'], datetime.now(), unit_id, target_date, nucleus_id)

            cursor.execute(query, params)
            conn.commit()

            return cursor.rowcount > 0   # True if at least one row updated

    except Exception as e:
        logger.error(f"Failed to update wages: {e}")

    return False


def mark_labour_as_paid_for_face(unit_id: int, target_date: datetime.date, nucleus_id: int) -> bool:
    """
    Update WagesUpload by setting IsPaid = 1 
    for a given UnitId and CreatedAt date (latest record).
    
    Args:
        unit_id (int): The Unit ID.
        target_date (datetime.date): The date to filter on.

    Returns:
        bool: True if rows were updated, False otherwise.
    """
    try:
        conn = DatabaseManager.get_connection()
        if conn:
            cursor = conn.cursor()

            query = """
                UPDATE WagesUpload
                SET VerifyType = 'Face',
                UpdatedBy = ?,
                UpdatedAt = ?
                WHERE UnitId = ?
                  AND CAST(CreatedAt AS DATE) = ?
                  and NucleusId = ?
                  
            """
            params = (session['user_id'], datetime.now(), unit_id, target_date, nucleus_id)

            cursor.execute(query, params)
            conn.commit()

            return cursor.rowcount > 0   # True if at least one row updated

    except Exception as e:
        logger.error(f"Failed to update wages: {e}")

    return False


def check_labour_ispaid_or_not(unit_id: int, nucleus_id: int) -> bool:
    """
    Check if a labour is marked as paid in the WagesUpload table.

    Args:
        unit_id (int): The Unit ID.
        target_date (datetime.date): The date to filter on.
        nucleus_id (int): The Nucleus ID of the labour.

    Returns:
        bool: True if the labour is marked as paid, False otherwise.
    """
    try:
        conn = DatabaseManager.get_connection()
        if conn:
            cursor = conn.cursor()

            query = """
                    SELECT 
                    NucleusId, 
                    LabourName, 
                    ContractorName, 
                    Amount, 
                    IsPaid, 
                    CreatedAt
                    FROM WagesUpload
                    WHERE UnitId = ?
                    AND NucleusId = ?
                    AND CAST(CreatedAt AS DATE) = (
                    SELECT MAX(CAST(CreatedAt AS DATE)) 
                    FROM WagesUpload
                    WHERE UnitId = ?
                    AND NucleusId = ?
                    );
            """
            params = (unit_id, nucleus_id, unit_id, nucleus_id)

            cursor.execute(query, params)
            return cursor.fetchone()

    except Exception as e:
        logger.error(f"Failed to check labour payment status: {e}")

    return False


def PreviousWeekUnpaidEmployeesfromDB(unit_id: int) -> List[Dict[str, Any]]:
    try:
        conn = DatabaseManager.get_connection()
        if conn:
            cursor = conn.cursor()
            query = """
                SELECT 
                    wu.NucleusId,
                    wu.ContractorId,
                    wu.LabourName,
                    wu.ContractorName,
                    wu.Amount,
                    wu.UnitId,
                    u.Name AS UnitName,
                    wu.IsPaid,
                    wu.VerifyType,
                    wu.CreatedBy,
                    wu.CreatedAt
                FROM WagesUpload wu
                INNER JOIN Unit u ON wu.UnitId = u.Id
                WHERE wu.IsPaid = 0 
                  AND wu.UnitId = ?
                  AND CAST(CreatedAt AS DATE) = (
                  SELECT MAX(CAST(CreatedAt AS DATE)) 
                  FROM WagesUpload where UnitId = ?
                );
            """
            params = (unit_id, unit_id)
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]  # get column names
            rows = cursor.fetchall()
            results = [dict(zip(columns, row)) for row in rows]  # convert each row into dict
            return results
    except Exception as e:
        logger.error(f"Failed to load previous week unpaid employees: {e}")
    return []

    
def FilterByDatePreviousWeek(unit_id: int, from_date: datetime.date, to_date: datetime.date) -> List[Dict[str, Any]]:
    try:
        conn = DatabaseManager.get_connection()
        if conn:
            cursor = conn.cursor()
            query = """
                    SELECT 
                    wu.NucleusId,
                    wu.ContractorId,
                    wu.LabourName,
                    wu.ContractorName,
                    wu.Amount,
                    wu.UnitId,
                    u.Name AS UnitName,
                    wu.IsPaid,
                    wu.VerifyType,
                    wu.CreatedBy,
                    wu.CreatedAt
                    FROM WagesUpload wu
                    INNER JOIN Unit u ON wu.UnitId = u.Id
                    WHERE wu.IsPaid = 0
                    AND wu.UnitId = ?
                    AND CAST(wu.CreatedAt AS DATE) BETWEEN ? AND ?;
            """
            params = (unit_id, from_date, to_date)
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]  # get column names
            rows = cursor.fetchall()
            results = [dict(zip(columns, row)) for row in rows]  # convert each row into dict
            return results
    except Exception as e:
        logger.error(f"Failed to load previous week unpaid employees: {e}")
    return []


def get_EmployeeByLabourId(nucleus_id: int) -> Any:
    """
    Fetch employee Based on NucleusId.
    """
    try:
        conn = DatabaseManager.get_connection()
        if conn:
            cursor = conn.cursor()

            query = """
                    SELECT e.NucleusId,e.Name ,e.FatherName,e.PhoneNo,e.Address,c.Name,e.UnitId,e.Image,e.IsActive
                    FROM Employee e inner join Contractor c on c.ContractorId=e.ContractorId where e.NucleusId = ?
            """
            params = (nucleus_id, )

            cursor.execute(query, params)
            return cursor.fetchone()

    except Exception as e:
        logger.error(f"Failed to Get employee details: {e}")
    return False

def get_Paid_Employee_Details(nucleus_id: int, unit_id: int, date: datetime.date) -> Any:
    """
    Get Paid Employee Details.
    """
    try:
        conn = DatabaseManager.get_connection()
        if conn:
            cursor = conn.cursor()

            query = """
                    SELECT 
                     NucleusId,
                     ContractorId,
                     LabourName,
                     ContractorName,
                     Amount,
                     UnitId,
                     IsPaid,
                     CreatedAt
                     FROM WagesUpload WHERE NucleusId = ? AND UnitId = ? AND IsPaid=0 AND CAST(CreatedAt AS DATE)=?
            """
            params = (nucleus_id, unit_id, date)

            cursor.execute(query, params)
            return cursor.fetchone()

    except Exception as e:
        logger.error(f"Failed to Get employee details: {e}")
    return False

def mark_labour_as_paid_for_code_for_single_employee(nucleus_id: int, unit_id: int, date: datetime.date) -> bool:
    """
    Update WagesUpload by setting IsPaid = 1 
    for a given UnitId and CreatedAt date (latest record).
    """
    try:
        conn = DatabaseManager.get_connection()
        if conn:
            cursor = conn.cursor()

            query = """
            UPDATE WagesUpload
            SET VerifyType = 'Code -- Single Employee',
            UpdatedBy = ?,
            UpdatedAt = ?,
            IsPaid = 1
            WHERE UnitId = ?
            AND CAST(CreatedAt AS DATE) = ?
            AND NucleusId = ?
            """
            params = (session['user_id'], datetime.now(), unit_id, date, nucleus_id)
            cursor.execute(query, params)
            conn.commit()

            return cursor.rowcount > 0   # True if at least one row updated

    except Exception as e:
        logger.error(f"Failed to update wages: {e}")

    return False