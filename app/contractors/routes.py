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


@contractors_bp.route('/delete/<int:contractor_id>')
@require_auth
@require_role(['admin', 'hr'])
def delete_contractor(contractor_id):
    """Delete Contractor"""
    try:
        success = ContractorModel.delete(contractor_id)
        if success:
            flash('Contractor deleted successfully.', 'success')
            logger.info(f"Contractor ID {contractor_id} deleted by user {session['email']}")
        else:
            flash('Error deleting contractor. Please try again.', 'error')
            
            
    except Exception as e:
        if 'FK_Employee_Contractor' in str(e):
            flash('Cannot delete this contractor because they are linked to employee records.', 'error')
            logger.warning(f"Failed to delete contractor {contractor_id} due to foreign key constraint")
        else:
            flash('An unexpected error occurred.', 'error')
            logger.error(f"Error deleting contractor: {e}")
    
    return redirect(url_for('contractors.list_contractors'))


@contractors_bp.route('/edit/<int:contractor_id>', methods=['GET', 'POST'])
@require_auth
@require_role(['admin', 'hr'])
def edit_contractor(contractor_id):
    """Edit contractor"""
    if request.method == 'POST':
        try:
            # Prepare data from form & file inputs
            data = ContractorForm.prepare_data(request.form, request.files)

            # Update contractor
            success = ContractorModel.update(contractor_id, data, session['user_id'])
            
            if success:
                flash('Contractor updated successfully.', 'success')
                logger.info(f"Contractor ID {contractor_id} updated by user {session['email']}")
                return redirect(url_for('contractors.list_contractors'))
            else:
                flash('Error updating contractor. Please try again.', 'error')

        except Exception as e:
            logger.error(f"Error updating contractor: {e}")
            flash('An unexpected error occurred.', 'error')
    
    # GET request - show edit form
    try:
        contractor = ContractorModel.get_by_id(contractor_id)
        units = ContractorModel.get_unit()       

        if not contractor:
            flash('Contractor not found.', 'error')
            return redirect(url_for('contractors.list_contractors'))
        
        return render_template(
            'contractors/edit_contractor.html',
            contractor=contractor,
            units=units
        )
    
    except Exception as e:
        logger.error(f"Error in edit_contractor: {e}")
        flash('Error loading contractor data.', 'error')
        return redirect(url_for('contractors.list_contractors'))
