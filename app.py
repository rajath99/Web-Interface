# --- Imports ---
import os
import pandas as pd
from flask import (
    Flask, request, redirect, url_for, render_template,
    flash, session, send_file
)
from werkzeug.utils import secure_filename
import smtplib
from email.message import EmailMessage
from io import BytesIO
from dotenv import load_dotenv
import logging # Good practice for logging

# --- Configuration Loading ---
load_dotenv() # Load .env file

# --- Configuration Variables ---
# (These should ideally be loaded from .env as shown)
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads') # More robust path
ALLOWED_EXTENSIONS = {'csv'}
# IMPORTANT: Load from .env! Use os.urandom(24) to generate a value.
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'default-super-secret-key-change-me-immediately')

# Email Config (loaded from .env)
MAIL_SERVER = os.environ.get('MAIL_SERVER')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') # Use App Password for Gmail
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ['true', '1', 't']
MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() in ['true', '1', 't']

# --- Flask App Setup ---
app = Flask(__name__)
# Apply configurations
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

# Configure logging
logging.basicConfig(level=logging.INFO) # Log informational messages and above

# Ensure the upload folder exists
try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    logging.info(f"Upload folder ensured at: {app.config['UPLOAD_FOLDER']}")
except OSError as e:
    logging.error(f"Could not create upload folder {app.config['UPLOAD_FOLDER']}: {e}")
    # Depending on severity, you might want to exit or handle this differently

# --- Helper Functions ---
def allowed_file(filename):
    """Checks if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_dataframe(filepath):
    """Reads the CSV file into a pandas DataFrame."""
    if not filepath or not os.path.exists(filepath):
        logging.warning(f"get_dataframe called with invalid path: {filepath}")
        return None
    try:
        # Try reading with standard UTF-8 first
        df = pd.read_csv(filepath)
        logging.info(f"Successfully read CSV '{os.path.basename(filepath)}' with utf-8 encoding.")
        return df
    except UnicodeDecodeError:
        try:
            # Fallback to latin1 if UTF-8 fails
            df = pd.read_csv(filepath, encoding='latin1')
            logging.info(f"Successfully read CSV '{os.path.basename(filepath)}' with latin1 encoding.")
            return df
        except Exception as e_inner:
            logging.error(f"Error reading CSV '{os.path.basename(filepath)}' with latin1 encoding: {e_inner}", exc_info=True)
            flash(f"Error reading file '{os.path.basename(filepath)}' with multiple encodings: {e_inner}", "danger")
            return None
    except Exception as e_outer:
        logging.error(f"General error reading CSV '{os.path.basename(filepath)}': {e_outer}", exc_info=True)
        flash(f"Error reading file '{os.path.basename(filepath)}': {e_outer}", "danger")
        return None


def send_email_notification(recipient, subject, body):
    """Sends an email using configured settings."""
    if not all([MAIL_SERVER, MAIL_USERNAME, MAIL_PASSWORD]):
        flash("Email server is not configured in .env file.", "warning")
        logging.warning("Email not sent: Email server details missing in configuration.")
        return False

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = MAIL_USERNAME
    msg['To'] = recipient
    msg.set_content(body)

    try:
        logging.info(f"Attempting to send email via {MAIL_SERVER}:{MAIL_PORT} to {recipient}")
        if MAIL_USE_SSL:
            server = smtplib.SMTP_SSL(MAIL_SERVER, MAIL_PORT)
            logging.info("Using SMTP_SSL.")
        else:
            server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT)
            logging.info("Using SMTP.")
            if MAIL_USE_TLS:
                server.starttls() # Secure the connection
                logging.info("TLS started.")

        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        logging.info("SMTP login successful.")
        server.send_message(msg)
        server.quit()
        logging.info(f"Email sent successfully to {recipient}")
        return True
    except smtplib.SMTPAuthenticationError:
        flash("Email login failed. Check MAIL_USERNAME/MAIL_PASSWORD (or App Password for Gmail).", "danger")
        logging.error("Email login failed: SMTPAuthenticationError.")
        return False
    except smtplib.SMTPServerDisconnected:
         flash("Email server disconnected unexpectedly.", "danger")
         logging.error("Email sending failed: SMTPServerDisconnected.")
         return False
    except Exception as e:
        flash(f"Failed to send email: {e}", "danger")
        logging.error(f"Failed to send email: {e}", exc_info=True)
        return False

# --- Routes (Endpoints) ---

@app.route('/', methods=['GET'])
def index():
    """Renders the main page."""
    # Clear previous results when loading the home page cleanly
    return render_template('index.html', data_html=None, filtered_data_html=None, message=None, filter_message=None)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles file uploads."""
    if 'file' not in request.files:
        flash('No file part in the request.', 'warning')
        return redirect(url_for('index')) # Redirect back to index

    file = request.files['file']
    if file.filename == '':
        flash('No file selected for upload.', 'warning')
        return redirect(url_for('index')) # Redirect back to index

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename) # Sanitize filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(filepath)
            # Store info in session for other routes to use
            session['filename'] = filename
            session['filepath'] = filepath
            session.modified = True # Ensure session is saved
            flash(f'File "{filename}" uploaded successfully!', 'success')
            logging.info(f"File '{filename}' uploaded to '{filepath}'.")
             # Redirect to index to show the success message and enable other buttons
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error saving file: {e}', 'danger')
            logging.error(f"Error saving uploaded file '{filename}': {e}", exc_info=True)
            # Clear session data if upload failed badly
            session.pop('filename', None)
            session.pop('filepath', None)
            return redirect(url_for('index')) # Redirect back to index
    else:
        flash('Invalid file type. Only CSV files (.csv) are allowed.', 'warning')
        return redirect(url_for('index')) # Redirect back to index

@app.route('/display', methods=['GET'])
def display_data():
    """Displays the content of the uploaded CSV."""
    filepath = session.get('filepath')
    filename = session.get('filename', 'Unknown file') # Get filename for messages

    if not filepath or not os.path.exists(filepath):
        flash('No file has been uploaded yet, or the file was moved/deleted.', 'warning')
        logging.warning("Display attempt failed: filepath not in session or file does not exist.")
        session.pop('filename', None) # Clear potentially stale session data
        session.pop('filepath', None)
        return redirect(url_for('index'))

    logging.info(f"Attempting to display data for: {filename}")
    df = get_dataframe(filepath)

    if df is not None:
        if df.empty:
             data_html = None
             message = f"File '{filename}' is empty or could not be read properly."
             flash(message, "info")
        else:
            # Display only the first N rows for performance in browser
            display_rows = 50
            data_html = df.head(display_rows).to_html(classes='table table-striped table-sm', index=False, border=0)
            message = f"Displaying first {min(display_rows, len(df))} rows of {filename}."
        # Render the template, passing the generated HTML and message
        return render_template('index.html', data_html=data_html, message=message)
    else:
        # get_dataframe already flashed an error and logged it
        
        session.pop('filename', None)
        session.pop('filepath', None)
        return redirect(url_for('index'))

@app.route('/email', methods=['POST'])
def email_summary():
    """Generates and emails a datewise summary."""
    filepath = session.get('filepath')
    filename = session.get('filename', 'Unknown file')
    recipient = request.form.get('recipient_email')

    if not filepath or not os.path.exists(filepath):
        flash('No file uploaded or file not found. Please upload again.', 'warning')
        logging.warning("Email attempt failed: filepath not in session or file does not exist.")
        session.pop('filename', None)
        session.pop('filepath', None)
        return redirect(url_for('index'))
    if not recipient:
        flash('Recipient email address is required.', 'warning')
        return redirect(url_for('index')) # Stay on page, user needs to enter email

    logging.info(f"Attempting email summary for {filename} to {recipient}")
    df = get_dataframe(filepath)
    if df is None:
        # Error already flashed by get_dataframe
        session.pop('filename', None)
        session.pop('filepath', None)
        return redirect(url_for('index'))

    # --- Datewise Summary Logic (Using 'Order Date') ---
    summary_text = f"Datewise Summary for {filename}:\n\n"
    date_column_name = 'Order Date' # <--- ADJUSTED COLUMN NAME

    try:
        if date_column_name in df.columns:
             # Attempt to convert to datetime, coercing errors to NaT (Not a Time)
            df[date_column_name] = pd.to_datetime(df[date_column_name], errors='coerce')
             # Drop rows where conversion failed if necessary, or handle them
            df_valid_dates = df.dropna(subset=[date_column_name])

            if not df_valid_dates.empty:
                # Group by date (ignoring time part) and count entries
                summary = df_valid_dates.groupby(df_valid_dates[date_column_name].dt.date).size().reset_index(name='Record Count')
                summary.columns = ['Date', 'Record Count'] 
                summary_text += summary.to_string(index=False)
                logging.info(f"Generated datewise summary for {filename}.")
            else:
                 summary_text += f"No valid dates found in column '{date_column_name}' or column is empty after conversion."
                 logging.warning(f"No valid dates found in '{date_column_name}' for {filename}.")
        else:
            summary_text += f"Column '{date_column_name}' not found in the file."
            flash(f"Column '{date_column_name}' not found for summary.", "warning")
            logging.warning(f"Column '{date_column_name}' not found in {filename} for email summary.")

    except Exception as e:
        summary_text = f"An unexpected error occurred while generating the summary: {e}"
        flash(f"Error during summary generation: {e}", "danger")
        logging.error(f"Error creating email summary for {filename}: {e}", exc_info=True)

    # --- Send Email ---
    subject = f"Datewise Summary: {filename}"
    if send_email_notification(recipient, subject, summary_text):
        flash(f'Summary email sent successfully to {recipient}!', 'success')
    # Error flash messages handled within send_email_notification

    # Render index page again (or redirect, depending on desired UX)
    # Redirecting keeps the URL clean
    return redirect(url_for('index'))

@app.route('/filter_action', methods=['POST'])
def filter_action():
    """Handles filtering and subsequent download or 'delete' (simulation)."""
    filepath = session.get('filepath')
    filename = session.get('filename', 'Unknown file')
    action = request.form.get('action') 
    filter_date_str = request.form.get('filter_date') # Expects YYYY-MM-DD
    filter_restaurant = request.form.get('filter_restaurant')

    # --- Column Names for Filtering ---
    date_col = 'Order Date'
    restaurant_col = 'Restaurant Name'
    # --- --- --- --- --- --- --- --- ---

    if not filepath or not os.path.exists(filepath):
        flash('No file uploaded or file not found. Please upload again.', 'warning')
        logging.warning("Filter/Action attempt failed: filepath not in session or file does not exist.")
        session.pop('filename', None)
        session.pop('filepath', None)
        return redirect(url_for('index'))

    logging.info(f"Action '{action}' requested for {filename}. Filters: Date='{filter_date_str}', Restaurant='{filter_restaurant}'")
    df = get_dataframe(filepath)
    if df is None:
        # Error already flashed by get_dataframe
        session.pop('filename', None)
        session.pop('filepath', None)
        return redirect(url_for('index'))

    if df.empty:
        flash(f"The file '{filename}' is empty. No filtering possible.", "info")
        return redirect(url_for('index'))

    # --- Filtering Logic ---
    filtered_df = df.copy() # Start with the full dataframe
    active_filters = []
    original_row_count = len(filtered_df)

    try:
        # Date Filter
        if filter_date_str:
            if date_col in filtered_df.columns:
                try:
                    # Convert filter date string to datetime object (only date part)
                    filter_date_dt = pd.to_datetime(filter_date_str).date()
                    
                    # Do this on a temporary series to avoid modifying filtered_df unless the filter is applied
                    date_series = pd.to_datetime(filtered_df[date_col], errors='coerce').dt.date
                    
                    filtered_df = filtered_df[date_series == filter_date_dt]
                    active_filters.append(f"{date_col} = {filter_date_str}")
                    logging.info(f"Applied date filter. Rows remaining: {len(filtered_df)}")
                except ValueError:
                    flash(f"Invalid date format entered: '{filter_date_str}'. Please use YYYY-MM-DD.", "warning")
                   
                except Exception as e:
                    flash(f"Error applying date filter: {e}", "danger")
                    logging.error(f"Error applying date filter for {filename}: {e}", exc_info=True)
            else:
                 flash(f"Column '{date_col}' not found for filtering.", "warning")
                 logging.warning(f"Column '{date_col}' not found in {filename} for filtering.")

        # Restaurant Name Filter (Case-sensitive)
        if filter_restaurant:
            if restaurant_col in filtered_df.columns:
                try:
                    
                    # Also handle potential NaN values in the column gracefully.
                    filtered_df = filtered_df[filtered_df[restaurant_col].astype(str).fillna('') == filter_restaurant]
                    active_filters.append(f"{restaurant_col} = '{filter_restaurant}'")
                    logging.info(f"Applied restaurant filter. Rows remaining: {len(filtered_df)}")
                except Exception as e:
                    flash(f"Error applying restaurant filter: {e}", "danger")
                    logging.error(f"Error applying restaurant filter for {filename}: {e}", exc_info=True)
            else:
                 flash(f"Column '{restaurant_col}' not found for filtering.", "warning")
                 logging.warning(f"Column '{restaurant_col}' not found in {filename} for filtering.")


    except Exception as e:
        flash(f"An unexpected error occurred during filtering: {e}", "danger")
        logging.error(f"Unexpected error applying filters for {filename}: {e}", exc_info=True)
        # Render the page without results but keeping the session file info
        return render_template('index.html', filter_message="Error during filtering.")


    filter_message = f"Filters applied: {', '.join(active_filters)}" if active_filters else "No filters applied."
    rows_matched_filter = len(filtered_df) # Rows *kept* by the filter criteria
    logging.info(f"Filtering complete for {filename}. {filter_message}. Found {rows_matched_filter} matching rows.")


    # --- Perform Action ---
    if action == 'download':
        if filtered_df.empty:
            flash(f"No data matched the filters. Nothing to download. {filter_message}", "info")
            # Render template showing the message
            return render_template('index.html', filter_message=f"No data matched the filters. Nothing to download. {filter_message}")

        # Create CSV in memory
        output = BytesIO()
        try:
            filtered_df.to_csv(output, index=False, encoding='utf-8')
            output.seek(0)
            download_filename = f"filtered_{filename}"
            flash(f"Prepared download for {rows_matched_filter} rows. {filter_message}", "success")
            logging.info(f"Sending {rows_matched_filter} rows for download as {download_filename}")
            return send_file(
                output,
                mimetype='text/csv',
                as_attachment=True,
                download_name=download_filename
            )
        except Exception as e:
             flash(f"Error preparing download file: {e}", "danger")
             logging.error(f"Error creating download file for {filename}: {e}", exc_info=True)
             return redirect(url_for('index'))


    elif action == 'delete':
        

        indices_to_delete = filtered_df.index # Get indices of rows that matched the filters

        if not indices_to_delete.empty:
            # Create a DataFrame containing rows *not* in the indices_to_delete
            df_after_delete = df.drop(indices_to_delete)
            num_deleted = len(df) - len(df_after_delete)
            flash(f"'Deleted' {num_deleted} rows matching filters (simulation). Displaying remaining {len(df_after_delete)} rows. {filter_message}", "info")
            logging.info(f"Simulated deletion of {num_deleted} rows for {filename}. Displaying remainder.")
            # Display the simulated result (first N rows)
            display_rows = 50
            filtered_data_html = df_after_delete.head(display_rows).to_html(classes='table table-striped table-sm', index=False, border=0)
            filter_msg_display = f"Showing remaining {len(df_after_delete)} rows (previewing first {min(display_rows, len(df_after_delete))}) after simulating deletion of {num_deleted} rows. {filter_message}"
            return render_template('index.html', filtered_data_html=filtered_data_html, filter_message=filter_msg_display)
        else:
            # No rows matched the filter, so nothing to "delete"
            flash(f"No rows matched the filters. Nothing was 'deleted'. {filter_message}", "info")
            logging.info(f"Simulated deletion for {filename}: No rows matched filters.")
            # Render the template showing the message
            return render_template('index.html', filter_message=f"No rows matched the filters. Nothing was 'deleted'. {filter_message}")

    else:
        flash('Invalid action specified.', 'danger')
        logging.warning(f"Invalid action '{action}' received.")
        return redirect(url_for('index'))


if __name__ == '__main__':
    
    app.run(debug=True, host='0.0.0.0', port=5000) 