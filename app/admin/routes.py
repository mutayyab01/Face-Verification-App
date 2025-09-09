from flask import render_template, flash,jsonify,request,session
import logging
from . import admin_bp
from app.auth.decorators import require_auth, require_role
from app.database import DatabaseManager
from datetime import datetime

logger = logging.getLogger(__name__)

@admin_bp.route('/')
@require_auth
@require_role(['admin'])
def dashboard():
    """Admin dashboard with access to all tables"""
    try:
        stats = {
            'employees': DatabaseManager.execute_query("SELECT COUNT(*) FROM Employee", fetch_one=True),
            'contractors': DatabaseManager.execute_query("SELECT COUNT(*) FROM Contractor", fetch_one=True),
            'users': DatabaseManager.execute_query("SELECT COUNT(*) FROM [User]", fetch_one=True)
        }
        
        stats = {k: v[0] if v else 0 for k, v in stats.items()}
        
        return render_template('admin/admin_dashboard.html', stats=stats)
    
    except Exception as e:
        logger.error(f"Error in admin dashboard: {e}")
        flash('Error loading dashboard data.', 'error')
        return render_template('admin/admin_dashboard.html', stats={'employees': 0, 'contractors': 0, 'users': 0})
    
#Author: Abrar ul Hassan, Comment: View Page Employee Payment View, Created At: 09-01-2025
@admin_bp.route('/ViewEmployePayment')
@require_auth
@require_role(['cashier:paid'])
def viewPaymentLabour():
    return render_template('admin/EmployeePaymentView.html')

#Author: Abrar ul Hassan, Comment: Get Employee Paid Record, Created At: 09-01-2025
@admin_bp.route("/api/get_employeesPayment")
@require_auth
@require_role(["cashier:paid"])
def get_employees_payment():
    conn = DatabaseManager.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
     SELECT NucleusId, ContractorId, LabourName, ContractorName, UpdatedAt, Amount,
       UnitId, IsPaid, VerifyType,
       CASE
       WHEN UnitId = 1 THEN 'C4'
       END AS Unit
    FROM WagesUpload
    WHERE CreatedAt = (
        SELECT MAX(CreatedAt) 
        FROM WagesUpload wu 
        WHERE wu.NucleusId = WagesUpload.NucleusId
    )
    AND UnitId = 1
    AND UpdatedAt is not null
    ORDER BY UpdatedAt DESC;  
    """)

    rows = cursor.fetchall()

    employees = []
    for row in rows:
        employees.append({
            "NucleusId": row.NucleusId,
            "LabourName": row.LabourName,
            "ContractorName": row.ContractorName,
            "Amount": row.Amount,
            "Date": row.UpdatedAt.strftime("%Y-%m-%d %H:%M:%S") if row.UpdatedAt else None,
            "Unit": row.Unit,
            "IsPaid": row.IsPaid,
        })

    return jsonify(employees)
#Author: Abrar ul Hassan, Comment: Update Wages Payment Confirm ispaid =1, Created At: 09-09-2025
@admin_bp.route("/api/get_employeesPayment",methods=["POST"])
@require_auth
@require_role(["cashier:paid"])
def PyamentConfirm():
    try:
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        data = request.get_json()
        NucleusId = data.get("NucleusId")
        IsPaid = data.get("isPaid")
        cursor.execute("""
            update WagesUpload set IsPaid = ?,
            UpdatedAt = ?, 
            UpdatedBy = ?
            where NucleusId = ? AND UnitId = 1
        """, (IsPaid,datetime.now(),session['user_id'],NucleusId))
        conn.commit()
        return jsonify({"success": True, "message": "Payment confirmed"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()