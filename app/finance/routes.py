from flask import render_template, flash, request
import logging
from datetime import datetime
import pandas as pd
from . import finance_bp
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
        print(f"❌ Error loading dashboard: {e}")
        flash("Error loading dashboard.", "error")
        return render_template('finance/finance_dashboard.html', stats={'total_employees': 0, 'active_employees': 0})


@finance_bp.route('/WagesUpload', methods=['GET', 'POST'])
@require_auth
@require_role(['finance'])
def wages_upload():
    print("📁 Accessed Wages Upload Route")
    message = None
    status = None

    if request.method == 'POST':
        print("📝 POST request received.")
        file = request.files.get('file')
        print("File data", file)

        try:
            print("📥 Reading Excel file...")
            df = pd.read_excel(file)
            df.columns = df.columns.str.strip()
            print("✅ Excel file read successfully.")
            print("📑 Columns found:", df.columns.tolist())

            required_columns = {'NucleusId', 'Name', 'FatherName', 'Amount', 'IsPaid'}
            if not required_columns.issubset(df.columns):
                missing = required_columns - set(df.columns)
                print(f"❌ Missing columns: {missing}")
                return render_template('finance/wagesUpload.html', message=f"Missing columns: {missing}", status="error")

            print("🔗 Connecting to database...")
            conn = DatabaseManager.get_connection()
            if not conn:
                print("❌ Failed to connect to database.")
                return render_template('finance/wagesUpload.html', message="Database connection failed.", status="error")

            print("✅ Connected to database.")
            cursor = conn.cursor()
            inserted_rows = 0
            now = datetime.now()
            # Drop Table , Then Execute new Record
            cursor.execute("TRUNCATE TABLE uploadata")
            print("📦 Starting row insertion loop...")
            for index, row in df.iterrows():
                try:
                    print(f"🔄 Inserting row {index}: {row.to_dict()}")
                    cursor.execute("""
                        INSERT INTO uploadata (
                            NucleusId, Name, FatherName, Amount, IsPaid
                        )
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        int(row['NucleusId']),
                        str(row['Name']).strip(),
                        str(row['FatherName']).strip(),
                        float(row['Amount']),
                        1 if str(row['IsPaid']).strip().upper() == 'TRUE' else 0
                    ))
                    inserted_rows += 1
                    print(f"✅ Row {index} inserted.")

                except Exception as insert_err:
                    logger.error(f"❌ Row {index} error: {insert_err}")
                    print(f"❌ Row {index} error: {insert_err}")
                    continue

            print("💾 Committing to database...")
            conn.commit()
            message = f"✅ Successfully inserted {inserted_rows} rows."
            status = "success"
            print("✅ Database commit done.")

        except Exception as e:
            logger.error(f"📄 File processing error: {e}")
            print(f"📄 File processing error: {e}")
            message = f"Error processing file: {e}"
            status = "error"

    upload_data = []
    try:
        conn = DatabaseManager.get_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT Id, NucleusId, Name, FatherName, Amount, IsPaid FROM uploadata")
            upload_data = cursor.fetchall()
    except Exception as e:
        logger.error(f"❌ Failed to fetch uploadata: {e}")
        print(f"❌ Failed to fetch uploadata: {e}")

    return render_template('finance/wagesUpload.html', message=message, status=status, upload_data=upload_data)