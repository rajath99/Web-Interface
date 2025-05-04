# Flask CSV Processor Interface

A simple web application built with Flask to process CSV files. It allows users to upload a CSV, display its contents, email a datewise summary, filter data by date and restaurant name, download the filtered data, and simulate deleting filtered rows.

## Features

*   **Upload:** Upload CSV files via a web interface.
*   **Display:** View the first 50 rows of the uploaded CSV in the browser.
*   **Email Summary:** Generate and email a summary of records grouped by 'Order Date'.
*   **Filter:** Filter data based on 'Order Date' and/or 'Restaurant Name'.
*   **Download:** Download the filtered data as a new CSV file.
*   **Delete (Simulated):** View the data that would remain *after* deleting rows matching the filter criteria (does not modify the original uploaded file).

## Requirements

*   Python 3.7+
*   Dependencies listed in `requirements.txt` (Flask, Pandas, python-dotenv, openpyxl)

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    # Replace YourUsername and YourRepositoryName with your actual details
    git clone https://github.com/YourUsername/YourRepositoryName.git
    cd YourRepositoryName
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # Create venv
    python -m venv venv
    # Activate venv (Windows cmd)
    venv\Scripts\activate
    # Or (Windows PowerShell)
    # .\venv\Scripts\Activate.ps1
    # Or (macOS/Linux)
    # source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **Create a `.env` file** in the project root directory.
2.  **Add the following variables**, replacing placeholders with your actual values:

    ```ini
    # Generate using: python -c 'import os; print(os.urandom(24))'
    FLASK_SECRET_KEY='YOUR_VERY_SECRET_FLASK_KEY'

    # Email Configuration (Example for Gmail)
    # Use an App Password if using Gmail with 2FA
    MAIL_SERVER=smtp.gmail.com
    MAIL_PORT=587
    MAIL_USERNAME=your_email@gmail.com
    MAIL_PASSWORD=your_gmail_app_password_or_regular_password
    MAIL_USE_TLS=True
    MAIL_USE_SSL=False
    ```

## Usage

1.  **Ensure the virtual environment is active.**
2.  **Run the Flask development server:**
    ```bash
    flask run
    ```
3.  **Open your web browser** and navigate to `http://127.0.0.1:5000` 
4.  **Use the web interface** to upload and process your CSV file.

## Important Notes

*   The application assumes your CSV file has columns named exactly `Order Date` and `Restaurant Name` for filtering and email summaries. Modify `app.py` if your column names differ.
*   The "Delete" functionality is a simulation only; it does not modify the originally uploaded file.
*   The `uploads/` directory (where uploaded files are temporarily stored) is intentionally excluded from Git tracking via `.gitignore`.# Web-Interface
