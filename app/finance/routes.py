from flask import render_template, flash, request, session
import logging
from datetime import datetime
import pandas as pd
from . import finance_bp
from app.contractors.models import ContractorModel
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
            'total_employees': DatabaseManager.execute_query("SELECT COUNT(*) FROM Employees", fetch_one=True),
            'active_employees': DatabaseManager.execute_query("SELECT COUNT(*) FROM Employees WHERE IsActive = 1", fetch_one=True)
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
    message = None
    status = None
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

    if request.method == 'POST':
        file = request.files.get('file')
        unit_id = request.form.get('Unit')

        if not file:
            return render_template('finance/wagesUpload.html', message="No file uploaded.", status="error")
        if not unit_id:
            return render_template('finance/wagesUpload.html', message="Please select a Unit.", status="error")

        try:
            df = pd.read_excel(file)
            df.columns = df.columns.str.strip()
            required_columns = {'NucleusId', 'ContractorId', 'Name', 'FatherName', 'Amount', 'IsPaid'}
            if not required_columns.issubset(df.columns):
                missing = required_columns - set(df.columns)
                return render_template('finance/wagesUpload.html', message=f"Missing columns: {missing}", status="error")

            conn = DatabaseManager.get_connection()
            if not conn:
                return render_template('finance/wagesUpload.html', message="Database connection failed.", status="error")
            cursor = conn.cursor()

            inserted_rows = 0
            skipped_rows = 0

            for index, row in df.iterrows():
                try:
                    contractor_id = parse_contractor_id(row['ContractorId'])
                    print(f"Row {index} - Parsed ContractorId: {contractor_id}")

                    if contractor_id is not None:
                        cursor.execute("SELECT Id FROM Contractor WHERE Id = ? AND IsActive = 1", (contractor_id,))
                        if not cursor.fetchone():
                            print(f"⚠ ContractorId {contractor_id} invalid at row {index}, skipping.")
                            skipped_rows += 1
                            continue

                    try:
                        nucleus_id = int(row['NucleusId'])
                    except Exception:
                        print(f"⚠ Invalid NucleusId at row {index}, skipping.")
                        skipped_rows += 1
                        continue
                    cursor.execute("SELECT Id FROM Employee WHERE NucleusId = ?", (nucleus_id,))
                    if not cursor.fetchone():
                        print(f"⚠ NucleusId {nucleus_id} not found at row {index}, skipping.")
                        skipped_rows += 1
                        continue

                    is_paid = 1 if str(row['IsPaid']).strip().upper() == 'TRUE' else 0
                    is_paid = int(is_paid)

                    cursor.execute("""
                        INSERT INTO WagesUpload (
                            NucleusId, ContractorId, Name, FatherName, Amount, UnitId, IsPaid, CreatedBy, CreatedAt
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        nucleus_id,
                        contractor_id,
                        str(row['Name']).strip(),
                        str(row['FatherName']).strip(),
                        float(row['Amount']),
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
            message = f"✅ Inserted {inserted_rows} rows, skipped {skipped_rows} rows."
            status = "success"

        except Exception as e:
            logger.error(f"File processing error: {e}")
            message = f"Error processing file: {e}"
            status = "error"

    upload_data = []
    try:
        conn = DatabaseManager.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    NucleusId,
                    ContractorId,
                    Name,
                    FatherName,
                    Amount,
                    CASE WHEN IsPaid = 1 THEN 'Yes' ELSE 'No' END AS IsPaid,
                    UnitId,
                    CreatedBy,
                    CreatedAt
                FROM WagesUpload
                WHERE CONVERT(VARCHAR(19), CreatedAt, 120) = (
                    SELECT CONVERT(VARCHAR(19), MAX(CreatedAt), 120)
                    FROM WagesUpload
                )
            """)
            upload_data = cursor.fetchall()
            units = ContractorModel.get_unit()
    except Exception as e:
        logger.error(f"Failed to fetch WagesUpload data: {e}")

    return render_template('finance/wagesUpload.html', message=message, status=status, upload_data=upload_data, units=units)
