from flask import render_template, flash
import logging
from . import finance_bp
from app.auth.decorators import require_auth, require_role
from app.database import DatabaseManager

logger = logging.getLogger(__name__)

@finance_bp.route('/')
@require_auth
@require_role(['finance'])
def dashboard():
    """Finance dashboard with employee management"""
    try:
        stats = {
            'total_employees': DatabaseManager.execute_query("SELECT COUNT(*) FROM Employee", fetch_one=True),
            'active_employees': DatabaseManager.execute_query("SELECT COUNT(*) FROM Employee WHERE IsActive = 1", fetch_one=True)
        }
        
        stats = {k: v[0] if v else 0 for k, v in stats.items()}
        
        return render_template('finance/finance_dashboard.html', stats=stats)
    
    except Exception as e:
        logger.error(f"Error in HR dashboard: {e}")
        flash('Error loading dashboard data.', 'error')
        return render_template('finance/finance_dashboard.html', stats={'total_employees': 0, 'active_employees': 0})
    

@finance_bp.route('/WagesUpload')
@require_auth
@require_role(['admin','finance'])
def WagesUpload():
    """List all employees"""
    try:

      
        return render_template('finance/wagesUpload.html')
    
    except Exception as e:
        logger.error(f"Error in list_employees: {e}")
        flash('Error loading employee data.', 'error')
        return render_template('employees/employees.html')
