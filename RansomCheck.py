import requests
import datetime
import os
import csv
import sys
from typing import List, Dict

# ==================== CONFIGURATION ====================
API_BASE_URL = "https://www.ransomlook.io/api"

# RansomLook search endpoint is public (no API key required for /search)
# If you have an API key and want to use it (or for /export), add it here:
API_KEY = None  # Leave as None for public access, or set "your_key_here"

# Path to your suppliers CSV file
CSV_FILE = "suppliers.csv"          # Change if your file has a different name/path

# Output file for alerts (appends every run)
ALERT_FILE = "ransomware_alerts.txt"

# ======================================================

def load_suppliers_from_csv(file_path: str) -> List[str]:
    """Load supplier names from CSV. Looks for common column headers."""
    if not os.path.exists(file_path):
        print(f"❌ Error: CSV file '{file_path}' not found!")
        sys.exit(1)

    suppliers = []
    possible_columns = ["supplier", "name", "company", "vendor", "Supplier", "Name", "Company"]

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            if not reader.fieldnames:
                print("❌ Error: CSV file appears empty or has no header row.")
                sys.exit(1)

            # Find the best matching column
            column_name = None
            for col in possible_columns:
                if col in reader.fieldnames:
                    column_name = col
                    break

            if not column_name:
                # Fallback: use the first column
                column_name = reader.fieldnames[0]
                print(f"Warning: No standard column name found. Using first column: '{column_name}'")

            for row in reader:
                supplier = row.get(column_name, "").strip()
                if supplier:
                    suppliers.append(supplier)

        print(f"Loaded {len(suppliers)} suppliers from {file_path}")
        return suppliers

    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        sys.exit(1)


def check_supplier(supplier: str) -> List[Dict]:
    """Query RansomLook /search endpoint for mentions of a supplier."""
    headers = {}
    if API_KEY:
        headers["Authorization"] = API_KEY

    params = {"query": supplier.strip()}

    try:
        response = requests.get(
            f"{API_BASE_URL}/search",
            headers=headers,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        return response.json()  # List of matching posts
    except requests.exceptions.RequestException as e:
        print(f"Error querying API for '{supplier}': {e}")
        return []


def generate_alert(supplier: str, matches: List[Dict]) -> None:
    """Create on-screen alert and append to log file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    alert_msg = f"""
{'='*80}
🚨 RANSOMWARE ALERT - {timestamp} 🚨
Supplier: {supplier}
Affected by: {len(matches)} ransomware post(s)

Details:
"""
    for match in matches[:10]:  # Limit to 10 matches to avoid huge alerts
        alert_msg += f"- Group: {match.get('group_name', 'Unknown')}\n"
        alert_msg += f"  Post: {match.get('post_title', 'No title')}\n"
        alert_msg += f"  Discovered: {match.get('discovered', 'Unknown')}\n\n"
    
    if len(matches) > 10:
        alert_msg += f"... and {len(matches) - 10} more matches.\n"

    alert_msg += f"{'='*80}\n"
    
    # On-screen alert
    print(alert_msg)
    
    # Append to file
    with open(ALERT_FILE, "a", encoding="utf-8") as f:
        f.write(alert_msg)


def main() -> None:
    print(f"Starting daily ransomware check - {datetime.date.today()}")
    
    suppliers = load_suppliers_from_csv(CSV_FILE)
    
    if not suppliers:
        print("No suppliers found in CSV. Exiting.")
        return

    alerts_issued = False
    
    for supplier in suppliers:
        print(f"Checking supplier: {supplier}...")
        matches = check_supplier(supplier)
        
        if matches:
            alerts_issued = True
            generate_alert(supplier, matches)
        else:
            print(f"  ✓ No mentions found for '{supplier}'")
    
    if not alerts_issued:
        print("\n✅ No ransomware activity detected for any monitored suppliers today.")
    
    print(f"\nCheck completed. Alerts logged to: {os.path.abspath(ALERT_FILE)}")


if __name__ == "__main__":
    main()
