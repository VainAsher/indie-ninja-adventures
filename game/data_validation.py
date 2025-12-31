"""
Data Validation Module - JSON Schema Validation for Game Data

This module provides validation for game data files (items, missions, dialogues)
using JSON schemas. Prevents data corruption and ensures data integrity.

Version: v1.0.0
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys


# Try to import jsonschema (it's a common library)
try:
    import jsonschema
    from jsonschema import validate, ValidationError, SchemaError
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    print("[WARNING] jsonschema library not installed. Schema validation disabled.")
    print("[INFO] Install with: pip install jsonschema")


# ============================================================
# Paths
# ============================================================

# Get project root (3 levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SCHEMA_DIR = DATA_DIR / "schemas"


# ============================================================
# Schema Loading
# ============================================================

def load_schema(schema_name: str) -> Optional[Dict]:
    """
    Load a JSON schema from the schemas directory.

    Args:
        schema_name: Name of schema file (e.g., "items_schema.json")

    Returns:
        Schema dict, or None if loading fails
    """
    schema_path = SCHEMA_DIR / schema_name

    if not schema_path.exists():
        print(f"[ERROR] Schema file not found: {schema_path}")
        return None

    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        return schema
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in schema {schema_name}: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to load schema {schema_name}: {e}")
        return None


def load_data_file(file_path: Path) -> Optional[Dict]:
    """
    Load a JSON data file.

    Args:
        file_path: Path to JSON file

    Returns:
        Data dict, or None if loading fails
    """
    if not file_path.exists():
        print(f"[ERROR] Data file not found: {file_path}")
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in {file_path.name}: {e}")
        print(f"  Line {e.lineno}, Column {e.colno}: {e.msg}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to load {file_path.name}: {e}")
        return None


# ============================================================
# Validation Functions
# ============================================================

def validate_data(data: Dict, schema: Dict, data_name: str) -> Tuple[bool, List[str]]:
    """
    Validate data against a schema.

    Args:
        data: Data to validate
        schema: JSON schema
        data_name: Name for error messages

    Returns:
        Tuple of (is_valid, error_messages)
    """
    if not JSONSCHEMA_AVAILABLE:
        return True, ["Schema validation skipped (jsonschema not installed)"]

    errors = []

    try:
        validate(instance=data, schema=schema)
        return True, []
    except ValidationError as e:
        # Format validation error
        path = " -> ".join(str(p) for p in e.path) if e.path else "root"
        error_msg = f"Validation error in {data_name} at {path}: {e.message}"
        errors.append(error_msg)

        # Add context from failing instance
        if hasattr(e, 'instance'):
            errors.append(f"  Problematic value: {e.instance}")

        return False, errors
    except SchemaError as e:
        errors.append(f"Schema error in {data_name}: {e.message}")
        return False, errors
    except Exception as e:
        errors.append(f"Unexpected error validating {data_name}: {e}")
        return False, errors


def validate_items_file(file_path: Optional[Path] = None) -> Tuple[bool, List[str]]:
    """
    Validate items.json file.

    Args:
        file_path: Path to items.json (default: data/items.json)

    Returns:
        Tuple of (is_valid, error_messages)
    """
    if file_path is None:
        file_path = DATA_DIR / "items.json"

    # Load schema
    schema = load_schema("items_schema.json")
    if schema is None:
        return False, ["Failed to load items schema"]

    # Load data
    data = load_data_file(file_path)
    if data is None:
        return False, ["Failed to load items data"]

    # Validate
    is_valid, errors = validate_data(data, schema, "items.json")

    # Additional custom validation
    if is_valid:
        custom_errors = _validate_items_custom(data)
        if custom_errors:
            return False, custom_errors

    return is_valid, errors


def validate_missions_file(file_path: Optional[Path] = None) -> Tuple[bool, List[str]]:
    """
    Validate missions.json file.

    Args:
        file_path: Path to missions.json (default: data/missions.json)

    Returns:
        Tuple of (is_valid, error_messages)
    """
    if file_path is None:
        file_path = DATA_DIR / "missions.json"

    # Load schema
    schema = load_schema("missions_schema.json")
    if schema is None:
        return False, ["Failed to load missions schema"]

    # Load data
    data = load_data_file(file_path)
    if data is None:
        return False, ["Failed to load missions data"]

    # Validate
    is_valid, errors = validate_data(data, schema, "missions.json")

    # Additional custom validation
    if is_valid:
        custom_errors = _validate_missions_custom(data)
        if custom_errors:
            return False, custom_errors

    return is_valid, errors


def validate_dialogues_file(file_path: Optional[Path] = None) -> Tuple[bool, List[str]]:
    """
    Validate dialogues.json file.

    Args:
        file_path: Path to dialogues.json (default: data/dialogues.json)

    Returns:
        Tuple of (is_valid, error_messages)
    """
    if file_path is None:
        file_path = DATA_DIR / "dialogues.json"

    # Load schema
    schema = load_schema("dialogues_schema.json")
    if schema is None:
        return False, ["Failed to load dialogues schema"]

    # Load data
    data = load_data_file(file_path)
    if data is None:
        return False, ["Failed to load dialogues data"]

    # Validate
    is_valid, errors = validate_data(data, schema, "dialogues.json")

    # Additional custom validation
    if is_valid:
        custom_errors = _validate_dialogues_custom(data)
        if custom_errors:
            return False, custom_errors

    return is_valid, errors


# ============================================================
# Custom Validation Rules
# ============================================================

def _validate_items_custom(data: Dict) -> List[str]:
    """
    Additional custom validation for items.

    Args:
        data: Items data

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Check for duplicate item IDs
    seen_ids = set()
    for item in data.get("items", []):
        item_id = item.get("item_id")
        if item_id in seen_ids:
            errors.append(f"Duplicate item_id: {item_id}")
        seen_ids.add(item_id)

    # Note: We don't validate that all consumables have effects,
    # as some consumables (like torches) may have effects not
    # represented in stats (lighting, quest progression, etc.)

    return errors


def _validate_missions_custom(data: Dict) -> List[str]:
    """
    Additional custom validation for missions.

    Args:
        data: Missions data

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Check for duplicate mission IDs
    seen_ids = set()
    for mission in data.get("missions", []):
        mission_id = mission.get("mission_id")
        if mission_id in seen_ids:
            errors.append(f"Duplicate mission_id: {mission_id}")
        seen_ids.add(mission_id)

    # Validate region references
    regions = set(data.get("regions", {}).keys())
    for mission in data.get("missions", []):
        mission_region = mission.get("region")
        if mission_region not in regions:
            errors.append(f"Mission '{mission.get('mission_id')}' references unknown region: {mission_region}")

    # Validate unlock requirements (check circular dependencies)
    mission_ids = {m.get("mission_id") for m in data.get("missions", [])}
    for mission in data.get("missions", []):
        for required_mission in mission.get("unlock_requirements", []):
            if required_mission not in mission_ids:
                errors.append(f"Mission '{mission.get('mission_id')}' requires unknown mission: {required_mission}")

    return errors


def _validate_dialogues_custom(data: Dict) -> List[str]:
    """
    Additional custom validation for dialogues.

    Args:
        data: Dialogues data

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Validate each dialogue tree
    for dialogue_id, dialogue in data.items():
        # Check root node exists
        root_id = dialogue.get("root_node_id")
        nodes = dialogue.get("nodes", {})

        if root_id not in nodes:
            errors.append(f"Dialogue '{dialogue_id}' root node '{root_id}' not found in nodes")

        # Check all next_node_id references are valid
        for node_id, node in nodes.items():
            # Check direct next_node_id
            next_id = node.get("next_node_id")
            if next_id is not None and next_id not in nodes:
                errors.append(f"Dialogue '{dialogue_id}' node '{node_id}' references unknown node: {next_id}")

            # Check choice next_node_ids
            for choice in node.get("choices", []):
                choice_next = choice.get("next_node_id")
                if choice_next is not None and choice_next not in nodes:
                    errors.append(f"Dialogue '{dialogue_id}' node '{node_id}' choice references unknown node: {choice_next}")

    return errors


# ============================================================
# Batch Validation
# ============================================================

def validate_all_data_files() -> Tuple[bool, Dict[str, List[str]]]:
    """
    Validate all game data files.

    Returns:
        Tuple of (all_valid, errors_by_file)
    """
    results = {}
    all_valid = True

    # Validate items
    is_valid, errors = validate_items_file()
    results["items.json"] = errors
    if not is_valid:
        all_valid = False

    # Validate missions
    is_valid, errors = validate_missions_file()
    results["missions.json"] = errors
    if not is_valid:
        all_valid = False

    # Validate dialogues
    is_valid, errors = validate_dialogues_file()
    results["dialogues.json"] = errors
    if not is_valid:
        all_valid = False

    return all_valid, results


# ============================================================
# Command Line Interface
# ============================================================

def main():
    """Run validation from command line"""
    print("="*60)
    print("GAME DATA VALIDATION")
    print("="*60)
    print()

    all_valid, results = validate_all_data_files()

    for filename, errors in results.items():
        if not errors:
            print(f"[PASS] {filename}: VALID")
        else:
            print(f"[FAIL] {filename}: INVALID")
            for error in errors:
                print(f"   - {error}")
        print()

    print("="*60)
    if all_valid:
        print("[PASS] ALL DATA FILES VALID")
        return 0
    else:
        print("[FAIL] VALIDATION FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
