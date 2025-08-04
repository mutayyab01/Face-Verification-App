from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pyodbc
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import os
from datetime import datetime, timedelta
import logging
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
config = Config()
app.secret_key = config.SECRET_KEY
app.permanent_session_lifetime = timedelta(hours=2)  # Session timeout

class DatabaseManager:
    @staticmethod
    def get_connection():
        """Create database connection with error handling"""
        try:
            conn = pyodbc.connect(config.DATABASE_URI)
            return conn
        except pyodbc.Error as e:
            logger.error(f"Database connection error: {e}")
            return None
    
    @staticmethod
    def execute_query(query, params=None, fetch_one=False, fetch_all=False):
        """Execute query with proper error handling"""
        conn = None
        try:
            conn = DatabaseManager.get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                conn.commit()
                return True
                
        except pyodbc.Error as e:
            logger.error(f"Database query error: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()

# Authentication and Authorization Decorators
def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if 'user_id' not in session or 'user_type' not in session:
            logger.warning(f"Unauthorized access attempt to {request.endpoint}")
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        
        # Check session timeout
        if 'last_activity' in session:
            try:
                # Convert session timestamp to datetime if it's a string
                if isinstance(session['last_activity'], str):
                    last_activity = datetime.fromisoformat(session['last_activity'])
                else:
                    last_activity = session['last_activity']
                
                # Ensure both datetimes are naive (no timezone info)
                current_time = datetime.now()
                if hasattr(last_activity, 'tzinfo') and last_activity.tzinfo is not None:
                    last_activity = last_activity.replace(tzinfo=None)
                
                if current_time - last_activity > app.permanent_session_lifetime:
                    logger.info(f"Session expired for user {session.get('email')}")
                    session.clear()
                    flash('Session expired. Please log in again.', 'warning')
                    return redirect(url_for('login'))
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing session timestamp: {e}")
                # Reset session if timestamp is corrupted
                session['last_activity'] = datetime.now()
        
        # Update last activity
        session['last_activity'] = datetime.now()
        
        # Verify user still exists and is active
        user = DatabaseManager.execute_query(
            "SELECT Id, Email, Type FROM [User] WHERE Id = ?",
            (session['user_id'],),
            fetch_one=True
        )
        
        if not user:
            logger.warning(f"User {session.get('email')} no longer exists in database")
            session.clear()
            flash('User account not found. Please log in again.', 'error')
            return redirect(url_for('login'))
        
        # Update session with current user data
        session['user_type'] = user[2].lower().strip()
        session['email'] = user[1]
        
        return f(*args, **kwargs)
    return decorated_function

def require_role(allowed_roles):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Ensure user is authenticated first
            if 'user_id' not in session or 'user_type' not in session:
                logger.warning(f"Unauthenticated access attempt to {request.endpoint}")
                return redirect(url_for('login'))
            
            # Normalize user type and allowed roles for comparison
            user_type = session['user_type'].lower().strip()
            normalized_roles = [role.lower().strip() for role in allowed_roles]
            
            logger.info(f"User {session.get('email')} (type: '{user_type}') accessing {request.endpoint}")
            logger.info(f"Required roles: {normalized_roles}")
            
            if user_type not in normalized_roles:
                logger.warning(f"Access denied for user {session.get('email')} (type: '{user_type}') to {request.endpoint}. Required: {normalized_roles}")
                return render_template('access_denied.html', 
                                     user_type=user_type, 
                                     required_roles=allowed_roles), 403
            
            logger.info(f"Access granted for user {session.get('email')} to {request.endpoint}")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Utility function to check if user has specific role
def has_role(required_roles):
    """Check if current user has required role"""
    if 'user_type' not in session:
        return False
    
    user_type = session['user_type'].lower().strip()
    normalized_roles = [role.lower().strip() for role in required_roles]
    return user_type in normalized_roles

# Routes
@app.route('/')
def index():
    """Home page - redirect to appropriate dashboard based on role"""
    if 'user_id' in session and 'user_type' in session:
        user_type = session.get('user_type', '').lower().strip()
        logger.info(f"Redirecting user {session.get('email')} with type '{user_type}'")
        
        if user_type == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user_type == 'hr':
            return redirect(url_for('hr_dashboard'))
        else:
            logger.warning(f"Unknown user type '{user_type}' for user {session.get('email')}")
            flash(f'Unknown user role: {user_type}', 'error')
            return render_template('access_denied.html'), 403
    
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page with enhanced security"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('login.html')
        
        # Query user from database
        user = DatabaseManager.execute_query(
            "SELECT Id, Email, Password, Type FROM [User] WHERE LOWER(TRIM(Email)) = ?",
            (email,),
            fetch_one=True
        )
        
        if user and user[2] == password:  # In production, use password hashing
            # Clear any existing session data
            session.clear()
            
            # Set session data
            session.permanent = True
            session['user_id'] = user[0]
            session['email'] = user[1].strip()
            session['user_type'] = user[3].lower().strip()
            session['last_activity'] = datetime.now()
            
            logger.info(f"User {email} logged in successfully with type '{session['user_type']}'")
            
            # Redirect based on role
            user_type = session['user_type']
            if user_type == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user_type == 'hr':
                return redirect(url_for('hr_dashboard'))
            else:
                logger.error(f"Invalid user role '{user_type}' for user {email}")
                session.clear()
                flash(f'Invalid user role: {user_type}', 'error')
                return render_template('access_denied.html'), 403
        else:
            logger.warning(f"Failed login attempt for email: {email}")
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    if 'email' in session:
        logger.info(f"User {session['email']} logged out")
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/admin')
@require_auth
@require_role(['admin'])
def admin_dashboard():
    """Admin dashboard with access to all tables"""
    try:
        # Get statistics
        stats = {
            'employees': DatabaseManager.execute_query("SELECT COUNT(*) FROM Employee", fetch_one=True),
            'contractors': DatabaseManager.execute_query("SELECT COUNT(*) FROM Contractor", fetch_one=True),
            'users': DatabaseManager.execute_query("SELECT COUNT(*) FROM [User]", fetch_one=True)
        }
        
        # Convert tuple results to integers
        stats = {k: v[0] if v else 0 for k, v in stats.items()}
        
        logger.info(f"Admin dashboard accessed by {session.get('email')}")
        return render_template('admin_dashboard.html', stats=stats)
    
    except Exception as e:
        logger.error(f"Error in admin dashboard: {e}")
        flash('Error loading dashboard data.', 'error')
        return render_template('admin_dashboard.html', stats={'employees': 0, 'contractors': 0, 'users': 0})

@app.route('/hr')
@require_auth
@require_role(['hr'])
def hr_dashboard():
    """HR dashboard with employee management"""
    try:
        # Get employee statistics
        stats = {
            'total_employees': DatabaseManager.execute_query("SELECT COUNT(*) FROM Employee", fetch_one=True),
            'active_employees': DatabaseManager.execute_query("SELECT COUNT(*) FROM Employee WHERE IsActive = 1", fetch_one=True)
        }
        
        stats = {k: v[0] if v else 0 for k, v in stats.items()}
        
        logger.info(f"HR dashboard accessed by {session.get('email')}")
        return render_template('hr_dashboard.html', stats=stats)
    
    except Exception as e:
        logger.error(f"Error in HR dashboard: {e}")
        flash('Error loading dashboard data.', 'error')
        return render_template('hr_dashboard.html', stats={'total_employees': 0, 'active_employees': 0})

# Employee CRUD Operations
@app.route('/employees')
@require_auth
@require_role(['admin', 'hr'])
def list_employees():
    """List all employees"""
    try:
        # Get employees with contractor information
        employees = DatabaseManager.execute_query("""
                    SELECT e.Id, e.Name, e.FatherName, e.PhoneNo, e.Address, 
                        c.Name as ContractorName, e.IsActive,
                        u1.Email as CreatedByEmail, e.CreatedAt,
                        u2.Email as UpdatedByEmail, e.UpdatedAt
                    FROM Employee e
                    LEFT JOIN Contractor c ON e.ContractorId = c.Id
                    LEFT JOIN [User] u1 ON e.CreatedBy = u1.Id
                    LEFT JOIN [User] u2 ON e.UpdatedBy = u2.Id
                    ORDER BY e.Id DESC
                    """, fetch_all=True)
        
        # # Get contractors for dropdown
        # contractors = DatabaseManager.execute_query(
        #     "SELECT Id, Name FROM Contractor WHERE IsActive = 1 ORDER BY Name",
        #     fetch_all=True
        # )
        
                # Update the list_contractors query
        contractors = DatabaseManager.execute_query(
                    """SELECT c.Id, c.Name, c.FatherName, c.Address, c.IsActive,
                        u1.Email as CreatedByEmail, c.CreatedAt,
                        u2.Email as UpdatedByEmail, c.UpdatedAt
                    FROM Contractor c
                    LEFT JOIN [User] u1 ON c.CreatedBy = u1.Id
                    LEFT JOIN [User] u2 ON c.UpdatedBy = u2.Id
                    WHERE IsActive = 1 ORDER BY c.Name""",fetch_all=True)



        logger.info(f"Employee list accessed by {session.get('email')}")
        return render_template('employees.html', 
                             employees=employees or [], 
                             contractors=contractors or [])
    
    except Exception as e:
        logger.error(f"Error in list_employees: {e}")
        flash('Error loading employee data.', 'error')
        return render_template('employees.html', employees=[], contractors=[])

# Update the add_employee function
@app.route('/employee/add', methods=['POST'])
@require_auth
@require_role(['admin', 'hr'])
def add_employee():
    """Add new employee with validation"""
    try:
        name = request.form.get('name', '').strip()
        father_name = request.form.get('father_name', '').strip()
        phone_no = request.form.get('phone_no', '').strip()
        address = request.form.get('address', '').strip()
        contractor_id = request.form.get('contractor_id') or None
        is_active = 'is_active' in request.form
        
        # Validation
        if not name or not father_name:
            flash('Name and Father Name are required.', 'error')
            return redirect(url_for('list_employees'))
        
        # Convert contractor_id to int if provided
        if contractor_id:
            try:
                contractor_id = int(contractor_id)
            except ValueError:
                contractor_id = None
        
        # Get current user ID and timestamp
        created_by = session['user_id']
        created_at = datetime.now()
        
        success = DatabaseManager.execute_query("""
            INSERT INTO Employee (Name, FatherName, PhoneNo, Address, ContractorId, IsActive, CreatedBy, CreatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, father_name, phone_no or None, address or None, contractor_id, is_active, created_by, created_at))
        
        if success:
            flash('Employee added successfully.', 'success')
            logger.info(f"Employee {name} added by user {session['email']}")
        else:
            flash('Error adding employee. Please try again.', 'error')
            
    except Exception as e:
        logger.error(f"Error adding employee: {e}")
        flash('An unexpected error occurred.', 'error')
    
    return redirect(url_for('list_employees'))



    
@app.route('/employee/edit/<int:employee_id>')
@require_auth
@require_role(['admin', 'hr'])
def edit_employee(employee_id):
    """Edit employee form"""
    try:
        employee = DatabaseManager.execute_query(
            "SELECT * FROM Employee WHERE Id = ?",
            (employee_id,),
            fetch_one=True
        )
        
        contractors = DatabaseManager.execute_query(
            "SELECT Id, Name FROM Contractor WHERE IsActive = 1 ORDER BY Name",
            fetch_all=True
        )
        
        if not employee:
            flash('Employee not found.', 'error')
            return redirect(url_for('list_employees'))
        
        return render_template('edit_employee.html', 
                             employee=employee, 
                             contractors=contractors or [])
    
    except Exception as e:
        logger.error(f"Error in edit_employee: {e}")
        flash('Error loading employee data.', 'error')
        return redirect(url_for('list_employees'))

# Update the update_employee function
@app.route('/employee/edit/<int:employee_id>', methods=['POST'])
@require_auth
@require_role(['admin', 'hr'])
def update_employee(employee_id):
    """Update employee with validation"""
    try:
        name = request.form.get('name', '').strip()
        father_name = request.form.get('father_name', '').strip()
        phone_no = request.form.get('phone_no', '').strip()
        address = request.form.get('address', '').strip()
        contractor_id = request.form.get('contractor_id') or None
        is_active = 'is_active' in request.form
        
        # Validation
        if not name or not father_name:
            flash('Name and Father Name are required.', 'error')
            return redirect(url_for('edit_employee', employee_id=employee_id))
        
        # Convert contractor_id to int if provided
        if contractor_id:
            try:
                contractor_id = int(contractor_id)
            except ValueError:
                contractor_id = None
        
        # Get current user ID and timestamp for update
        updated_by = session['user_id']
        updated_at = datetime.now()
        
        success = DatabaseManager.execute_query("""
            UPDATE Employee 
            SET Name = ?, FatherName = ?, PhoneNo = ?, Address = ?, 
                ContractorId = ?, IsActive = ?, UpdatedBy = ?, UpdatedAt = ?
            WHERE Id = ?
        """, (name, father_name, phone_no or None, address or None, 
              contractor_id, is_active, updated_by, updated_at, employee_id))
        
        if success:
            flash('Employee updated successfully.', 'success')
            logger.info(f"Employee ID {employee_id} updated by user {session['email']}")
        else:
            flash('Error updating employee. Please try again.', 'error')
            
    except Exception as e:
        logger.error(f"Error updating employee: {e}")
        flash('An unexpected error occurred.', 'error')
    
    return redirect(url_for('list_employees'))




@app.route('/employee/delete/<int:employee_id>')
@require_auth
@require_role(['admin', 'hr'])
def delete_employee(employee_id):
    """Delete employee"""
    try:
        success = DatabaseManager.execute_query(
            "DELETE FROM Employee WHERE Id = ?",
            (employee_id,)
        )
        
        if success:
            flash('Employee deleted successfully.', 'success')
            logger.info(f"Employee ID {employee_id} deleted by user {session['email']}")
        else:
            flash('Error deleting employee. Please try again.', 'error')
            
    except Exception as e:
        logger.error(f"Error deleting employee: {e}")
        flash('An unexpected error occurred.', 'error')
    
    return redirect(url_for('list_employees'))

# Contractor CRUD Operations (Admin only)
@app.route('/contractors')
@require_auth
@require_role(['admin'])
def list_contractors():
    """List all contractors"""
    try:
        contractors = DatabaseManager.execute_query(
            "SELECT Id, Name, FatherName, Address, IsActive FROM Contractor ORDER BY Name",
            fetch_all=True
        )
        
        logger.info(f"Contractor list accessed by {session.get('email')}")
        return render_template('contractors.html', contractors=contractors or [])
    
    except Exception as e:
        logger.error(f"Error in list_contractors: {e}")
        flash('Error loading contractor data.', 'error')
        return render_template('contractors.html', contractors=[])

# Update the add_contractor function
@app.route('/contractor/add', methods=['POST'])
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
            return redirect(url_for('list_contractors'))
        
        # Get current user ID and timestamp
        created_by = session['user_id']
        created_at = datetime.now()
        
        success = DatabaseManager.execute_query("""
            INSERT INTO Contractor (Name, FatherName, Address, PhoneNo, IsActive, CreatedBy, CreatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, father_name, address or None, phone_no, is_active, created_by, created_at))
        
        if success:
            flash('Contractor added successfully.', 'success')
            logger.info(f"Contractor {name} added by user {session['email']}")
        else:
            flash('Error adding contractor. Please try again.', 'error')
            
    except Exception as e:
        logger.error(f"Error adding contractor: {e}")
        flash('An unexpected error occurred.', 'error')
    
    return redirect(url_for('list_contractors'))



    # Update the update_contractor function (you'll need to add this if it doesn't exist)


@app.route('/contractor/edit/<int:contractor_id>', methods=['POST'])
@require_auth
@require_role(['admin'])
def update_contractor(contractor_id):
    """Update contractor"""
    try:
        name = request.form.get('name', '').strip()
        father_name = request.form.get('father_name', '').strip()
        address = request.form.get('address', '').strip()
        is_active = 'is_active' in request.form
        
        if not name or not father_name:
            flash('Name and Father Name are required.', 'error')
            return redirect(url_for('edit_contractor', contractor_id=contractor_id))
        
        # Get current user ID and timestamp for update
        updated_by = session['user_id']
        updated_at = datetime.now()
        
        success = DatabaseManager.execute_query("""
            UPDATE Contractor 
            SET Name = ?, FatherName = ?, Address = ?, IsActive = ?, 
                UpdatedBy = ?, UpdatedAt = ?
            WHERE Id = ?
        """, (name, father_name, address or None, is_active, 
              updated_by, updated_at, contractor_id))
        
        if success:
            flash('Contractor updated successfully.', 'success')
            logger.info(f"Contractor ID {contractor_id} updated by user {session['email']}")
        else:
            flash('Error updating contractor. Please try again.', 'error')
            
    except Exception as e:
        logger.error(f"Error updating contractor: {e}")
        flash('An unexpected error occurred.', 'error')
    
    return redirect(url_for('list_contractors'))





# User Management (Admin only)
@app.route('/users')
@require_auth
@require_role(['admin'])
def list_users():
    """List all users"""
    try:
        users = DatabaseManager.execute_query(
            "SELECT Id, Email, Type FROM [User] ORDER BY Email",
            fetch_all=True
        )
        
        logger.info(f"User list accessed by {session.get('email')}")
        return render_template('users.html', users=users or [])
    
    except Exception as e:
        logger.error(f"Error in list_users: {e}")
        flash('Error loading user data.', 'error')
        return render_template('users.html', users=[])

@app.route('/user/add', methods=['POST'])
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
            return redirect(url_for('list_users'))
        
        if user_type not in ['admin', 'hr']:
            flash(f'Invalid user type: {user_type}. Must be admin or hr.', 'error')
            return redirect(url_for('list_users'))
        
        # Check if email already exists
        existing_user = DatabaseManager.execute_query(
            "SELECT Id FROM [User] WHERE LOWER(TRIM(Email)) = ?",
            (email,),
            fetch_one=True
        )
        
        if existing_user:
            flash('Email already exists.', 'error')
            return redirect(url_for('list_users'))
        
        # In production, hash the password
        success = DatabaseManager.execute_query("""
            INSERT INTO [User] (Email, Password, Type)
            VALUES (?, ?, ?)
        """, (email, password, user_type))
        
        if success:
            flash('User added successfully.', 'success')
            logger.info(f"User {email} added by user {session['email']}")
        else:
            flash('Error adding user. Please try again.', 'error')
            
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        flash('An unexpected error occurred.', 'error')
    
    return redirect(url_for('list_users'))

# Debug route to check session data
@app.route('/debug/session')
@require_auth
def debug_session():
    """Debug route to check session data"""
    last_activity = session.get('last_activity')
    return jsonify({
        'user_id': session.get('user_id'),
        'email': session.get('email'),
        'user_type': session.get('user_type'),
        'last_activity': str(last_activity) if last_activity else None,
        'last_activity_type': str(type(last_activity)),
        'current_time': str(datetime.now()),
        'session_keys': list(session.keys()),
        'session_timeout_hours': app.permanent_session_lifetime.total_seconds() / 3600
    })

# Error Handlers
@app.errorhandler(403)
def forbidden(error):
    return render_template('access_denied.html'), 403

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return render_template('500.html'), 500

# Context Processors
@app.context_processor
def inject_user():
    """Inject user information into all templates"""
    return {
        'current_user': {
            'id': session.get('user_id'),
            'email': session.get('email'),
            'type': session.get('user_type')
        },
        'has_role': has_role  # Make has_role function available in templates
    }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)