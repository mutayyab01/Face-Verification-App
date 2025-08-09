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
        units = ContractorModel.get_unit()
        return render_template('contractors/contractors.html', contractors=contractors ,units=units)
    
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
        
          # Get form data
           # Read image file as binary
        image_file = request.files.get('ProfileImage')   
        image_binary = image_file.read()  # read binary data

        UserData = {
            "Name": request.form.get('Name', '').strip().lower(),
            "FatherName": request.form.get('FatherName', '').strip().lower(),
            "PhoneNumber": request.form.get('PhoneNumber', '').strip().lower(),
            "Unit": request.form.get('Unit', '').strip(),
            "ProfileImage": image_binary,
            "Address": request.form.get('Address', '').strip().lower(),
            "IsActive": 'IsActive' in request.form,
            
        }
        logger.info(UserData)

        success = ContractorModel.create(UserData, session['user_id'])
        
        if success:
            flash('Contractor added successfully.', 'success')
            logger.info(f"Contractor {UserData['Name']} added by user {session['email']}")
        else:
            flash('Error adding contractor. Please try again.', 'error')
            
    except Exception as e:
        logger.error(f"Error adding contractor: {e}")
        flash('An unexpected error occurred.', 'error')
    
    return redirect(url_for('contractors.list_contractors'))
