from flask import render_template, request, redirect, url_for, flash, session
import logging
from . import employees_bp
from .models import EmployeeModel
from .forms import EmployeeForm
from app.auth.decorators import require_auth, require_role
from app.contractors.models import ContractorModel

logger = logging.getLogger(__name__)

@employees_bp.route('/')
@require_auth
@require_role(['admin', 'hr'])
def list_employees():
    """List all employees"""
    try:
        employees = EmployeeModel.get_all()
        contractors = ContractorModel.get_active_contractors()
        units = ContractorModel.get_unit()
      
        return render_template('employees/employees.html', 
                             employees=employees, 
                             contractors=contractors,
                             units=units)
    
    except Exception as e:
        logger.error(f"Error in list_employees: {e}")
        flash('Error loading employee data.', 'error')
        return render_template('employees/employees.html', employees=[], contractors=[])

@employees_bp.route('/add', methods=['GET', 'POST'])
@require_auth
@require_role(['admin', 'hr'])
def add_employee():
    """Add new employee"""
    if request.method == 'POST':
        try:
            # Prepare data
            data = EmployeeForm.prepare_data(request.form, request.files)
            
            if EmployeeModel.exists_nucleus_id(data['NucleusId']):
                flash('Error: Employee ID already exists.', 'error')
                return redirect(url_for('employees.list_employees'))
            
            # Create employee
            success = EmployeeModel.create(data, session['user_id'])

            if success:
                flash('Employee added successfully.', 'success')
                logger.info(f"Employee {data['Name']} added by user {session['email']}")
            else:
                flash('Error adding employee. Please try again.', 'error')

        except Exception as e:
            logger.error(f"Unexpected error while adding employee: {e}")
            flash('An unexpected error occurred.', 'error')

        return redirect(url_for('employees.list_employees'))

    # GET request - show add form
    contractors = ContractorModel.get_active_contractors()
    return render_template('employees/add.html', contractors=contractors or [])




@employees_bp.route('/edit/<int:employee_id>', methods=['GET', 'POST'])
@require_auth
@require_role(['admin', 'hr'])
def edit_employee(employee_id):
    """Edit employee"""
    if request.method == 'POST':
        try:
            
            # Prepare data
            data = EmployeeForm.prepare_data(request.form, request.files)
            success = EmployeeModel.update(employee_id, data, session['user_id'])
            
            if success:
                flash('Employee updated successfully.', 'success')
                logger.info(f"Employee ID {employee_id} updated by user {session['email']}")
                return redirect(url_for('employees.list_employees'))
            else:
                flash('Error updating employee. Please try again.', 'error')
                
        except Exception as e:
            logger.error(f"Error updating employee: {e}")
            flash('An unexpected error occurred.', 'error')
    
    # GET request - show edit form
    try:
        employee = EmployeeModel.get_by_id(employee_id)
        contractors = ContractorModel.get_active_contractors()
        units = ContractorModel.get_unit()

        if not employee:
            flash('Employee not found.', 'error')
            return redirect(url_for('employees.list_employees'))
        
        return render_template('employees/edit_employee.html', 
                             employee=employee, 
                             contractors=contractors,
                             units=units)
    
    except Exception as e:
        logger.error(f"Error in edit_employee:")
        flash('Error loading employee data.', 'error')
        return redirect(url_for('employees.list_employees'))

@employees_bp.route('/delete/<int:employee_id>')
@require_auth
@require_role(['admin', 'hr'])
def delete_employee(employee_id):
    """Delete employee"""
    try:
        success = EmployeeModel.delete(employee_id)
        
        if success:
            flash('Employee deleted successfully.', 'success')
            logger.info(f"Employee ID {employee_id} deleted by user {session['email']}")
        else:
            flash('Error deleting employee. Please try again.', 'error')
            
    except Exception as e:
        logger.error(f"Error deleting employee: {e}")
        flash('An unexpected error occurred.', 'error')
    
    return redirect(url_for('employees.list_employees'))