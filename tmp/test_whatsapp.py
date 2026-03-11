
import sys
import os
# Add current directory to path so we can import tools and database
sys.path.append(os.getcwd())

import database as db
import tools.send_whatsapp as sw

print("Current contacts:", db.get_all_wa_contacts())

# Test 1: Known contact (Mama)
print("\nTesting 'Mama'...")
res1 = sw.send_whatsapp("Mama", "Hi from Debug Script")
print(f"Result for Mama: {res1}")

# Test 2: Unknown contact (Hamna)
print("\nTesting 'Hamna Masood'...")
res2 = sw.send_whatsapp("Hamna Masood", "Hi from Debug Script")
print(f"Result for Hamna: {res2}")
