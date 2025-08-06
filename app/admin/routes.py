from flask import render_template, flash
import logging
from . import admin_bp
from app.auth.decorators import require_auth, require_role
from app.database import DatabaseManager

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