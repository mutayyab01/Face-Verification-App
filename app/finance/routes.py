from flask import render_template, flash, request, session, redirect, url_for
import logging
from datetime import datetime
import pandas as pd
from . import finance_bp
from app.contractors.models import ContractorModel
from .models import WagesUploadModel
from app.auth.decorators import require_auth, require_role
from app.database import DatabaseManager

logger = logging.getLogger(__name__)

@finance_bp.route('/')
@require_auth
@require_role(['finance'])
def dashboard():
    try:
        print("📊 Fetching finance dashboard stats...")
        stats = {
            'total_employees': DatabaseManager.execute_query("SELECT COUNT(*) FROM Employee", fetch_one=True),
            'active_employees': DatabaseManager.execute_query("SELECT COUNT(*) FROM Employee WHERE IsActive = 1", fetch_one=True)
        }
        stats = {k: v[0] if v else 0 for k, v in stats.items()}
        print("✅ Dashboard stats fetched:", stats)
        return render_template('finance/finance_dashboard.html', stats=stats)

    except Exception as e:
        logger.error(f"Error in finance dashboard: {e}")
        print(f"Error loading dashboard: {e}")
        flash("Error loading dashboard.", "error")
        return render_template('finance/finance_dashboard.html', stats={'total_employees': 0, 'active_employees': 0})


@finance_bp.route('/WagesUpload', methods=['GET', 'POST'])
@require_auth
@require_role(['finance'])
def wages_upload():
    print("📁 Accessed Wages Upload Route")
    
    # Check for messages in session
    message = session.pop('upload_message', None) if 'upload_message' in session else None
    status = session.pop('upload_status', None) if 'upload_status' in session else None
    
    units = []

    def parse_contractor_id(value):
        if pd.isna(value):
            return None
        try:
            if isinstance(value, str):
                val = value.strip()
                if val.lower() in ['', 'nan', 'none', 'null']:
                    return None
                return int(float(val))
            return int(float(value))
        except Exception as e:
            print(f"❌ ContractorId parse error: {e} for value {value}")
            return None

    def parse_amount(value):
        """Parse amount removing commas, spaces and converting to float"""
        if pd.isna(value):
            return 0.0
        try:
            if isinstance(value, str):
                # Remove commas, spaces, and any other non-numeric characters except decimal point
                val = value.replace(',', '').replace(' ', '').strip()
                # Handle cases where amount might have currency symbols
                import re
                # Extract only numbers and decimal points
                val = re.sub(r'[^\d.]', '', val)
                if val == '':
                    return 0.0
                return float(val)
            elif isinstance(value, (int, float)):
                return float(value)
            else:
                # Try to convert directly
                return float(str(value).replace(',', '').replace(' ', '').strip())
        except Exception as e:
            print(f"❌ Amount parse error: {e} for value '{value}' (type: {type(value)})")
            return 0.0

    if request.method == 'POST':
        file = request.files.get('file')
        unit_id = request.form.get('Unit')

        if not file:
            session['upload_message'] = "No file uploaded."
            session['upload_status'] = "error"
            return redirect(url_for('finance.wages_upload'))
        if not unit_id:
            session['upload_message'] = "Please select a Unit."
            session['upload_status'] = "error"
            return redirect(url_for('finance.wages_upload'))

        try:
            result = WagesUploadModel.delete_existing_record_with_unitId(unit_id)         
            df = pd.read_excel(file)
            df.columns = df.columns.str.strip()
            
            # Updated required columns to match your Excel format
            required_columns = {'Labour Code', 'Contractor Code', 'Labour Name', 'Net Payable'}
            if not required_columns.issubset(df.columns):
                missing = required_columns - set(df.columns)
                session['upload_message'] = f"Missing columns: {missing}"
                session['upload_status'] = "error"
                return redirect(url_for('finance.wages_upload'))

            conn = DatabaseManager.get_connection()
            if not conn:
                session['upload_message'] = "Database connection failed."
                session['upload_status'] = "error"
                return redirect(url_for('finance.wages_upload'))
            cursor = conn.cursor()

            inserted_rows = 0
            skipped_rows = 0

            for index, row in df.iterrows():
                try:
                    # Map Excel columns to database columns
                    nucleus_id = row['Labour Code']  # Labour Code -> NucleusId
                    contractor_id = parse_contractor_id(row['Contractor Code'])  # Contractor Code -> ContractorId
                    labour_name = str(row['Labour Name']).strip()  # Labour Name -> Name
                    contractor_name = str(row.get('Contractor Name', '')).strip()  # For ContractorName field
                    amount = parse_amount(row['Net Payable'])  # Net Payable -> Amount (properly formatted as number)
                    
                    print(f"Row {index} - NucleusId: {nucleus_id}, ContractorId: {contractor_id}, Amount: {amount:.2f}")

                    # Validate ContractorId
                    if contractor_id is not None:
                        cursor.execute("SELECT ContractorId FROM Contractor WHERE ContractorId = ? AND IsActive = 1", (contractor_id,))
                        if not cursor.fetchone():
                            print(f"⚠ ContractorId {contractor_id} invalid at row {index}, skipping.")
                            skipped_rows += 1
                            continue

                    # Validate NucleusId (Labour Code)
                    try:
                        nucleus_id_int = int(nucleus_id)
                    except Exception:
                        print(f"⚠ Invalid NucleusId at row {index}, skipping.")
                        skipped_rows += 1
                        continue
                    
                    cursor.execute("SELECT Id FROM Employee WHERE NucleusId = ?", (nucleus_id_int,))
                    if not cursor.fetchone():
                        print(f"⚠ NucleusId {nucleus_id_int} not found at row {index}, skipping.")
                        skipped_rows += 1
                        continue

                    # Default IsPaid to 0 (False) since it's not in your Excel
                    is_paid = 0

                    cursor.execute("""
                        INSERT INTO WagesUpload (
                            NucleusId, ContractorId, LabourName, ContractorName, Amount, UnitId, IsPaid, CreatedBy, CreatedAt
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        nucleus_id_int,
                        contractor_id,
                        labour_name,
                        contractor_name,  # Using contractor name as substitute for father name
                        amount,
                        int(unit_id),
                        is_paid,
                        session['user_id'],
                        datetime.now()
                    ))
                    inserted_rows += 1

                except Exception as e:
                    print(f"❌ Error inserting row {index}: {e}")
                    skipped_rows += 1
                    continue

            conn.commit()
            session['upload_message'] = f"✅ Inserted {inserted_rows} rows, skipped {skipped_rows} rows."
            session['upload_status'] = "success"
            return redirect(url_for('finance.wages_upload'))

        except Exception as e:
            logger.error(f"File processing error: {e}")
            session['upload_message'] = f"Error processing file: {e}"
            session['upload_status'] = "error"
            return redirect(url_for('finance.wages_upload'))

    # Rest of your code for displaying upload data...
    try:
        unit_id = request.args.get("unit_id", type=int, default=1)
        upload_data = WagesUploadModel.get_latest_record_by_unit(unit_id)
        units = ContractorModel.get_unit()
        unit_map = {
                        1: "C4",
                        2: "E-38",
                        3: "B44"
                   }
    except Exception as e:
        logger.error(f"Failed to fetch WagesUpload data: {e}")

    return render_template('finance/wagesUpload.html', message=message, status=status, upload_data=upload_data, units=units, unit_map=unit_map)