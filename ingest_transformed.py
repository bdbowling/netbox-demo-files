#!/usr/bin/env python3
"""
Transform and Ingest Script for Orb Agent Dry Run Output

Skips Interface entities entirely.
"""

import json
import os
import sys
import time
import glob
from datetime import datetime

try:
    from netboxlabs.diode.sdk import DiodeClient
    from netboxlabs.diode.sdk.ingester import (
        Device,
        DeviceType,
        Interface,
        IPAddress,
        Prefix,
        Site,
        DeviceRole,
        Manufacturer,
        Platform,
        Entity,
    )
except ImportError:
    print("ERROR: netboxlabs-diode-sdk not installed")
    print("Install with: pip install netboxlabs-diode-sdk")
    sys.exit(1)

# Configuration
WATCH_DIR = os.environ.get("WATCH_DIR", "/opt/orb/output")
PROCESSED_DIR = os.environ.get("PROCESSED_DIR", "/opt/orb/output/processed")
DIODE_TARGET = os.environ.get("DIODE_TARGET", "grpc://10.168.251.14:80/diode")
DIODE_CLIENT_ID = os.environ.get("DIODE_CLIENT_ID")
DIODE_CLIENT_SECRET = os.environ.get("DIODE_CLIENT_SECRET")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "10"))
APP_NAME = "orb1/device-discovery-transformed"
APP_VERSION = "1.0.0"


def load_json(filepath: str) -> list:
    """Load a dry_run JSON file."""
    print(f"Loading: {filepath}")
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    if isinstance(data, list):
        entities = data
    elif isinstance(data, dict) and "entities" in data:
        entities = data["entities"]
    else:
        entities = [data]
    
    print(f"  Found {len(entities)} entities")
    return entities


def build_device(dev_data: dict) -> Device:
    """Build a Device object from raw data."""
    device_type = None
    if "device_type" in dev_data:
        dt = dev_data["device_type"]
        manufacturer = None
        if "manufacturer" in dt:
            manufacturer = Manufacturer(name=dt["manufacturer"].get("name"))
        device_type = DeviceType(
            model=dt.get("model"),
            manufacturer=manufacturer
        )
    
    role = None
    if "role" in dev_data:
        role = DeviceRole(name=dev_data["role"].get("name"))
    
    platform = None
    if "platform" in dev_data:
        plat = dev_data["platform"]
        plat_manufacturer = None
        if "manufacturer" in plat:
            plat_manufacturer = Manufacturer(name=plat["manufacturer"].get("name"))
        platform = Platform(
            name=plat.get("name"),
            manufacturer=plat_manufacturer
        )
    
    site = None
    if "site" in dev_data:
        site = Site(name=dev_data["site"].get("name"))
    
    return Device(
        name=dev_data.get("name"),
        device_type=device_type,
        role=role,
        platform=platform,
        serial=dev_data.get("serial"),
        site=site,
        status=dev_data.get("status"),
        description=dev_data.get("description"),
        comments=dev_data.get("comments"),
    )


def create_diode_entities(raw_entities: list) -> list:
    """Convert raw entity dicts to Diode SDK Entity objects."""
    diode_entities = []
    
    for raw in raw_entities:
        try:
            # Handle Device entities (standalone)
            if "device" in raw and "interface" not in raw and "ip_address" not in raw:
                device = build_device(raw["device"])
                diode_entities.append(Entity(device=device))
                print(f"  Created Device: {raw['device'].get('name')}")
            
            # SKIP Interface entities
            elif "interface" in raw:
                print(f"  Skipping Interface: {raw['interface'].get('name')}")
            
            # SKIP IPAddress entities (they reference interfaces)
            elif "ip_address" in raw:
                print(f"  Skipping IPAddress: {raw['ip_address'].get('address')}")
            
            # Handle Prefix entities
            elif "prefix" in raw:
                prefix = Prefix(prefix=raw["prefix"].get("prefix"))
                diode_entities.append(Entity(prefix=prefix))
                print(f"  Created Prefix: {raw['prefix'].get('prefix')}")
            
            # Handle Site entities
            elif "site" in raw:
                site = Site(
                    name=raw["site"].get("name"),
                    status=raw["site"].get("status"),
                    description=raw["site"].get("description"),
                )
                diode_entities.append(Entity(site=site))
                print(f"  Created Site: {raw['site'].get('name')}")
            
            # Skip VLAN
            elif "vlan" in raw:
                print(f"  Skipping VLAN")
            
            # Skip timestamp-only entries
            elif list(raw.keys()) == ["timestamp"]:
                continue
            
            else:
                keys = [k for k in raw.keys() if k != "timestamp"]
                if keys:
                    print(f"  WARNING: Unknown entity type: {keys}")
                
        except Exception as e:
            print(f"  ERROR creating entity: {e}")
    
    return diode_entities


def ingest_to_diode(entities: list) -> bool:
    """Ingest entities to Diode server."""
    if not entities:
        print("  No entities to ingest")
        return True
    
    print(f"\n  Ingesting {len(entities)} entities to Diode...")
    
    try:
        with DiodeClient(
            target=DIODE_TARGET,
            app_name=APP_NAME,
            app_version=APP_VERSION,
        ) as client:
            response = client.ingest(entities=entities)
            
            if response.errors:
                print(f"  Ingestion completed with {len(response.errors)} errors:")
                for error in response.errors[:5]:
                    print(f"    - {error}")
                return False
            else:
                print(f"  Successfully ingested {len(entities)} entities")
                return True
                
    except Exception as e:
        print(f"  ERROR during ingestion: {e}")
        return False


def move_to_processed(filepath: str):
    """Move a processed file to the processed directory."""
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    filename = os.path.basename(filepath)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_path = os.path.join(PROCESSED_DIR, f"{timestamp}_{filename}")
    os.rename(filepath, new_path)
    print(f"  Moved to: {new_path}")


def process_file(filepath: str) -> bool:
    """Process a single JSON file."""
    print(f"\n{'='*60}")
    print(f"Processing: {filepath}")
    print(f"{'='*60}")
    
    try:
        raw_entities = load_json(filepath)
        diode_entities = create_diode_entities(raw_entities)
        success = ingest_to_diode(diode_entities)
        
        if success:
            move_to_processed(filepath)
        return success
        
    except Exception as e:
        print(f"  ERROR processing file: {e}")
        return False


def get_pending_files() -> list:
    """Get list of JSON files waiting to be processed."""
    pattern = os.path.join(WATCH_DIR, "*.json")
    files = glob.glob(pattern)
    files.sort(key=os.path.getmtime)
    return files


def main():
    """Main loop."""
    print("="*60)
    print("Orb Agent Transform & Ingest Script")
    print("(Skipping Interfaces)")
    print("="*60)
    print(f"Watch directory: {WATCH_DIR}")
    print(f"Diode target: {DIODE_TARGET}")
    print()
    
    if not DIODE_CLIENT_ID or not DIODE_CLIENT_SECRET:
        print("ERROR: DIODE_CLIENT_ID and DIODE_CLIENT_SECRET must be set")
        sys.exit(1)
    
    os.makedirs(WATCH_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    print("Watching for files... (Ctrl+C to stop)\n")
    
    while True:
        try:
            for filepath in get_pending_files():
                process_file(filepath)
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\nShutting down...")
            break


if __name__ == "__main__":
    main()
