from flask import render_template, request, redirect, url_for, flash, session
import logging
from . import contractors_bp
from .models import ContractorModel
from app.auth.decorators import require_auth, require_role

logger = logging.getLogger(__name__)

@contractors_bp.route('/')
@require_auth
@require_role(['admin'])
def list_contractors():
    """List all contractors"""
    try:
        contractors = ContractorModel.get_all()
        return render_template('contractors/contractors.html', contractors=contractors or [])
    
    except Exception as e:
        logger.error(f"Error in list_contractors: {e}")
        flash('Error loading contractor data.', 'error')
        return render_template('contractors/contractors.html', contractors=[])

@contractors_bp.route('/add', methods=['POST'])
@require_auth
@require_role(['admin'])
def add_contractor():
    """Add new contractor"""
    try:
        name = request.form.get('name', '').strip()
        father_name = request.form.get('father_name', '').strip()
        phone_no = request.form.get('phone_no', '').strip()
        address = request.form.get('address', '').strip()
        is_active = 'is_active' in request.form

        if not name or not father_name:
            flash('Name and Father Name are required.', 'error')
            return redirect(url_for('contractors.list_contractors'))
        
        data = {
            'name': name,
            'father_name': father_name,
            'phone_no': phone_no or None,
            'address': address or None,
            'is_active': is_active
        }
        
        success = ContractorModel.create(data, session['user_id'])
        
        if success:
            flash('Contractor added successfully.', 'success')
            logger.info(f"Contractor {name} added by user {session['email']}")
        else:
            flash('Error adding contractor. Please try again.', 'error')
            
    except Exception as e:
        logger.error(f"Error adding contractor: {e}")
        flash('An unexpected error occurred.', 'error')
    
    return redirect(url_for('contractors.list_contractors'))
