from flask import render_template, request, redirect, url_for, session, flash
from datetime import datetime
import logging
from . import auth_bp
from app.database import DatabaseManager

logger = logging.getLogger(__name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page with enhanced security"""
    if request.method == 'POST':
        email = request.form.get('loginEmail', '').strip().lower()
        password = request.form.get('loginPassword', '')
        
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('auth/login.html')
        
        user = DatabaseManager.execute_query(
            "SELECT Id, FirstName, LastName, Email, Password, Type FROM [User] WHERE LOWER(TRIM(Email)) = ? and IsActive=1",
            (email,),
            fetch_one=True
        )
        
        logger.info(user)

        if user and user[4] == password:
            session.clear()
            session.permanent = True
            session['user_id'] = user[0]
            session['FirstName'] = user[1]
            session['LastName'] = user[2]
            session['email'] = user[3].strip()
            session['user_type'] = user[5].lower().strip()
            session['last_activity'] = datetime.now()
            
            logger.info(f"User {email} logged in successfully")
            
            user_type = session['user_type']
            if user_type == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user_type == 'hr':
                return redirect(url_for('hr.dashboard'))
            elif user_type == 'finance':
                return redirect(url_for('finance.dashboard'))
            elif user_type == 'cashier':
                return redirect(url_for('face.dashboard'))
            else:
                session.clear()
                flash(f'Invalid user role: {user_type}', 'error')
                return render_template('errors/access_denied.html'), 403
        else:
            logger.warning(f"Failed login attempt for email: {email}")
            flash('Invalid email or password.', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    """Logout and clear session"""
    if 'email' in session:
        logger.info(f"User {session['email']} logged out")
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))