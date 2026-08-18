import json
import os

def count():
    """
    Count the number of guest accounts in guests_converted.json
    """
    guests_file = "guests_manager/guests_converted.json"
    
    if not os.path.exists(guests_file):
        return 0
    
    try:
        with open(guests_file, "r") as f:
            guests = json.load(f)
            if isinstance(guests, list):
                return len(guests)
            return 0
    except Exception as e:
        print(f"Error reading guests file: {e}")
        return 0

if __name__ == "__main__":
    guest_count = count()
    print(f"Total guest accounts: {guest_count}")
