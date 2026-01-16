import os
import logging
from dotenv import load_dotenv
from netboxlabs.diode.sdk import DiodeClient
from netboxlabs.diode.sdk.ingester import Entity
from google.protobuf.json_format import ParseDict

# Load environment variables
load_dotenv("/opt/diode-ingestion/.env")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# Bind env vars to Python variables
DIODE_GRPC_URL = os.getenv("DIODE_GRPC_URL")
DIODE_CLIENT_ID = os.getenv("DIODE_CLIENT_ID")
DIODE_CLIENT_SECRET = os.getenv("DIODE_CLIENT_SECRET")
APP_NAME = os.getenv("APP_NAME", "enable_interface_demo")
APP_VERSION = os.getenv("APP_VERSION", "0.0.1")# Bind env vars to Python variables
DIODE_GRPC_URL = os.getenv("DIODE_GRPC_URL")
DIODE_CLIENT_ID = os.getenv("DIODE_CLIENT_ID")
DIODE_CLIENT_SECRET = os.getenv("DIODE_CLIENT_SECRET")
APP_NAME = os.getenv("APP_NAME", "enable_interface_demo")
APP_VERSION = os.getenv("APP_VERSION", "0.0.1")

# Embedded entity data
RAW_ENTITIES = [
    {
    "interface": {
        "device": {
        "name": "sw4",
        "deviceType": {
            "model": "C9KV-UADP-8P",
            "manufacturer": {
            "name": "Cisco"
            }
        },
        "platform": {
            "name": "IOS-XE 17.12.1prd9",
            "manufacturer": {
            "name": "Cisco"
            }
        },
        "serial": "CML54321",
        "site": {
            "name": "Default Site"
        },
        "status": "active"
        },
        "name": "GigabitEthernet1/0/2",
        "enabled": True,
        "mtu": 1500,
        "macAddress": "52:54:00:0F:1C:09",
        "speed": 1000000,
        "description": ""
    }
    }
]

def convert_to_entities(raw_entities):
    """Converts raw dictionaries to protobuf Entity messages."""
    entities = []
    for i, raw in enumerate(raw_entities):
        try:
            entity = Entity()
            ParseDict(raw, entity, ignore_unknown_fields=True)
            entities.append(entity)
        except Exception as e:
            logging.warning(f"Failed to parse entity at index {i}: {e}")
    return entities

def send_to_diode(entities):
    """Send protobuf entities to Diode and log a summary."""
    with DiodeClient(
        target=DIODE_GRPC_URL,
        app_name=APP_NAME,
        app_version=APP_VERSION,
    ) as client:
        try:
            response = client.ingest(entities=entities)
            total = len(entities)
            errors = response.errors if response.errors else []
            error_count = len(errors)

            if error_count > 0:
                logging.error(f"❌ Ingest completed with {error_count} error(s) out of {total} entities.")
                for i, error in enumerate(errors, start=1):
                    logging.error(f"  Error {i}: {error}")
            else:
                logging.info(f"✅ Ingest successful. {total} entities sent with no errors.")

        except Exception as e:
            logging.error(f"💥 Critical error during ingestion: {e}")

def main():
    entities = convert_to_entities(RAW_ENTITIES)
    if entities:
        send_to_diode(entities)
    else:
        logging.error("🚫 No valid entities to send.")

if __name__ == "__main__":
    main()
