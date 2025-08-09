from flask import render_template, request, redirect, url_for, flash, session
import logging
from . import contractors_bp
from .models import ContractorModel
from .forms import ContractorForm
from app.auth.decorators import require_auth, require_role

logger = logging.getLogger(__name__)

@contractors_bp.route('/')
@require_auth
@require_role(['admin','hr'])
def list_contractors():
    """List all contractors"""
    try:
        contractors = ContractorModel.get_all()
        units = ContractorModel.get_unit()
        logger.info(contractors)
        return render_template('contractors/contractors.html', contractors=contractors ,units=units)
    
    except Exception as e:
        logger.error(f"Error in list_contractors: {e}")
        flash('Error loading contractor data.', 'error')
        return render_template('contractors/contractors.html', contractors=[])

@contractors_bp.route('/add', methods=['POST'])
@require_auth
@require_role(['admin','hr'])
def add_contractor():
    """Add new contractor"""
    try:
        # Prepare data
        data = ContractorForm.prepare_data(request.form, request.files)
            
        if ContractorModel.exists_Contractor_Id(data['ContractorId']):
            flash('Error: Contractor ID already exists.', 'error')
            return redirect(url_for('contractors.list_contractors'))
            
            # Create employee
        success = ContractorModel.create(data, session['user_id'])
    
        
        if success:
            flash('Contractor added successfully.', 'success')
            logger.info(f"Contractor {data['Name']} added by user {session['email']}")
        else:
            flash('Error adding contractor. Please try again.', 'error')
            
    except Exception as e:
        logger.error(f"Error adding contractor: {e}")
        flash('An unexpected error occurred.', 'error')
    
    return redirect(url_for('contractors.list_contractors'))
