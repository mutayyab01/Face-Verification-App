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
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        user_type = request.form.get('type', '').strip().lower()
        
        if not email or not password or not user_type:
            flash('All fields are required.', 'error')
            return redirect(url_for('users.list_users'))
        
        if user_type not in ['admin', 'hr']:
            flash(f'Invalid user type: {user_type}. Must be admin or hr.', 'error')
            return redirect(url_for('users.list_users'))
        
        # Check if email already exists
        existing_user = UserModel.get_by_email(email)
        if existing_user:
            flash('Email already exists.', 'error')
            return redirect(url_for('users.list_users'))
        
        success = UserModel.create(email, password, user_type)
        
        if success:
            flash('User added successfully.', 'success')
            logger.info(f"User {email} added by user {session['email']}")
        else:
            flash('Error adding user. Please try again.', 'error')
            
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        flash('An unexpected error occurred.', 'error')
    
    return redirect(url_for('users.list_users'))
