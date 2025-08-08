from flask import render_template, request, redirect, url_for, flash, session
import logging
from . import users_bp
from .models import UserModel
from app.auth.decorators import require_auth, require_role

logger = logging.getLogger(__name__)

@users_bp.route('/')
@require_auth
@require_role(['admin'])
def list_users():
    """List all users"""
    try:
        users = UserModel.get_all()
        return render_template('users/users.html', users=users or [])
    
    except Exception as e:
        logger.error(f"Error in list_users: {e}")
        flash('Error loading user data.', 'error')
        return render_template('users/users.html', users=[])

@users_bp.route('/add', methods=['POST'])
@require_auth
@require_role(['admin'])
def add_user():
    """Add new user"""
    try:
         # Get form data
        UserData = {
            "FirstName": request.form.get('FirstName', '').strip().lower(),
            "LastName": request.form.get('LastName', '').strip().lower(),
            "Email": request.form.get('email', '').strip().lower(),
            "Password": request.form.get('password', '').strip(),
            "UserType": request.form.get('type', '').strip().lower(),
            "IsActive": 'IsActive' in request.form
        }
        
        # Check if email already exists
        existing_user = UserModel.get_by_email(UserData['Email'])
        if existing_user:
            flash('Email already exists.', 'error')
            return redirect(url_for('users.list_users'))
        
        success = UserModel.create(UserData)
        
        if success:
            flash('User added successfully.', 'success')
            logger.info(f"User {UserData['Email']} added by user {session['email']}")
        else:
            flash('Error adding user. Please try again.', 'error')
            
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        flash('An unexpected error occurred.', 'error')
    
    return redirect(url_for('users.list_users'))
