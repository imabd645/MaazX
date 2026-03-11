
import sys
import os
sys.path.append(os.getcwd())

from core import whatsapp_handler
import tools # This is critical to populate the registry!

# Simulate an incoming message from the admin
msg_data = {
    "from": "923350806140@c.us",
    "body": "Send 'The fix is working perfectly!' to Mama",
    "id": "test_msg_id_123",
    "timestamp": 123456789
}

print("Simulating incoming message...")
whatsapp_handler.handle_incoming_message(msg_data)
print("Simulation done.")
