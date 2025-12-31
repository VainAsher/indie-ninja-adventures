"""
Campaign Validation Tool - Prevents Soft-Locks and Validates Mission Graph

This tool validates the game campaign to prevent soft-lock scenarios:
- Checks for circular dependencies in mission unlock requirements
- Validates all missions are reachable
- Ensures ability progression is valid (no orphaned abilities)
- Checks region accessibility
- Validates mission graph structure
- Detects impossible mission chains

Version: v0.7.0
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque


# ============================================================
# Validation Result Classes
# ============================================================

class ValidationError:
    """Represents a validation error"""
    def __init__(self, severity: str, category: str, message: str, mission_id: Optional[str] = None):
        self.severity = severity  # 'ERROR', 'WARNING', 'INFO'
        self.category = category  # 'CIRCULAR_DEP', 'UNREACHABLE', etc.
        self.message = message
        self.mission_id = mission_id

    def __str__(self):
        prefix = f"[{self.severity}]"
        mission_part = f" [{self.mission_id}]" if self.mission_id else ""
        return f"{prefix}{mission_part} {self.category}: {self.message}"


class ValidationReport:
    """Validation report with errors and warnings"""
    def __init__(self):
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []
        self.info: List[ValidationError] = []

    def add_error(self, category: str, message: str, mission_id: Optional[str] = None):
        self.errors.append(ValidationError('ERROR', category, message, mission_id))

    def add_warning(self, category: str, message: str, mission_id: Optional[str] = None):
        self.warnings.append(ValidationError('WARNING', category, message, mission_id))

    def add_info(self, category: str, message: str, mission_id: Optional[str] = None):
        self.info.append(ValidationError('INFO', category, message, mission_id))

    def is_valid(self) -> bool:
        """Check if campaign is valid (no errors)"""
        return len(self.errors) == 0

    def has_warnings(self) -> bool:
        """Check if campaign has warnings"""
        return len(self.warnings) > 0


# ============================================================
# Campaign Validator
# ============================================================

class CampaignValidator:
    """
    Validates campaign structure and mission graph.

    Checks for soft-locks, circular dependencies, and progression issues.
    """

    def __init__(self, missions_data: dict):
        """
        Initialize validator with missions data.

        Args:
            missions_data: Loaded missions.json data
        """
        self.data = missions_data
        self.missions = {m['mission_id']: m for m in missions_data.get('missions', [])}
        self.regions = missions_data.get('regions', {})
        self.report = ValidationReport()

    def validate_all(self) -> ValidationReport:
        """
        Run all validation checks.

        Returns:
            ValidationReport with all errors and warnings
        """
        print("Running campaign validation...")
        print()

        # Run all validation checks
        self._validate_mission_references()
        self._validate_region_references()
        self._validate_circular_dependencies()
        self._validate_reachability()
        self._validate_ability_progression()
        self._validate_region_accessibility()
        self._validate_difficulty_progression()

        return self.report

    # ============================================================
    # Validation Checks
    # ============================================================

    def _validate_mission_references(self):
        """Validate all mission ID references are valid"""
        mission_ids = set(self.missions.keys())

        for mission_id, mission in self.missions.items():
            # Check unlock requirements
            for req_id in mission.get('unlock_requirements', []):
                if req_id not in mission_ids:
                    self.report.add_error(
                        'INVALID_REFERENCE',
                        f"References non-existent mission: {req_id}",
                        mission_id
                    )

    def _validate_region_references(self):
        """Validate all region references are valid"""
        region_ids = set(self.regions.keys())

        for mission_id, mission in self.missions.items():
            region = mission.get('region')
            if region not in region_ids:
                self.report.add_error(
                    'INVALID_REGION',
                    f"References non-existent region: {region}",
                    mission_id
                )

    def _validate_circular_dependencies(self):
        """Detect circular dependencies in mission unlock requirements"""
        # Build dependency graph
        dependencies = defaultdict(list)
        for mission_id, mission in self.missions.items():
            for req_id in mission.get('unlock_requirements', []):
                dependencies[mission_id].append(req_id)

        # Check for cycles using DFS
        def has_cycle_from(node: str, visited: Set[str], rec_stack: Set[str]) -> Optional[List[str]]:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in dependencies.get(node, []):
                if neighbor not in visited:
                    cycle = has_cycle_from(neighbor, visited, rec_stack)
                    if cycle:
                        return cycle + [node]
                elif neighbor in rec_stack:
                    # Found cycle
                    return [neighbor, node]

            rec_stack.remove(node)
            return None

        visited = set()
        for mission_id in self.missions.keys():
            if mission_id not in visited:
                cycle = has_cycle_from(mission_id, visited, set())
                if cycle:
                    cycle_str = " -> ".join(reversed(cycle))
                    self.report.add_error(
                        'CIRCULAR_DEPENDENCY',
                        f"Circular mission dependency: {cycle_str}",
                        cycle[-1]
                    )

    def _validate_reachability(self):
        """Validate all missions are reachable from starting missions"""
        # Find starting missions (no unlock requirements)
        starting_missions = [
            m_id for m_id, m in self.missions.items()
            if not m.get('unlock_requirements', [])
        ]

        if not starting_missions:
            self.report.add_error(
                'NO_STARTING_MISSIONS',
                "No missions without unlock requirements found"
            )
            return

        # BFS to find all reachable missions
        reachable = set(starting_missions)
        queue = deque(starting_missions)

        # Build reverse dependency graph (what each mission unlocks)
        unlocks = defaultdict(list)
        for mission_id, mission in self.missions.items():
            for req_id in mission.get('unlock_requirements', []):
                unlocks[req_id].append(mission_id)

        while queue:
            current = queue.popleft()
            # Add missions that this mission unlocks
            for unlocked_id in unlocks.get(current, []):
                if unlocked_id not in reachable:
                    # Check if all requirements are met
                    requirements = self.missions[unlocked_id].get('unlock_requirements', [])
                    if all(req in reachable for req in requirements):
                        reachable.add(unlocked_id)
                        queue.append(unlocked_id)

        # Check for unreachable missions
        unreachable = set(self.missions.keys()) - reachable
        for mission_id in unreachable:
            self.report.add_error(
                'UNREACHABLE_MISSION',
                f"Mission cannot be reached from starting missions",
                mission_id
            )

        # Info about reachability
        self.report.add_info(
            'REACHABILITY',
            f"{len(reachable)}/{len(self.missions)} missions reachable"
        )

    def _validate_ability_progression(self):
        """Validate ability progression (no orphaned abilities)"""
        # Collect all abilities
        all_required_abilities = set()
        all_unlocked_abilities = set()

        for mission_id, mission in self.missions.items():
            required = mission.get('required_abilities', [])
            unlocked = mission.get('unlock_abilities', [])

            all_required_abilities.update(required)
            all_unlocked_abilities.update(unlocked)

        # Base abilities (always available)
        base_abilities = {'basic_movement', 'jump'}

        # Check for orphaned abilities (required but never unlocked)
        available_abilities = base_abilities | all_unlocked_abilities
        orphaned = all_required_abilities - available_abilities

        for ability in orphaned:
            self.report.add_error(
                'ORPHANED_ABILITY',
                f"Ability '{ability}' is required but never unlocked"
            )

        # Check for unused unlocked abilities
        unused = all_unlocked_abilities - all_required_abilities
        for ability in unused:
            self.report.add_warning(
                'UNUSED_ABILITY',
                f"Ability '{ability}' is unlocked but never required"
            )

        # Info about abilities
        self.report.add_info(
            'ABILITIES',
            f"{len(all_unlocked_abilities)} abilities unlocked, "
            f"{len(all_required_abilities)} abilities required"
        )

    def _validate_region_accessibility(self):
        """Validate regions are accessible based on mission completion requirements"""
        # Simulate mission completion to check region access
        completed_missions = 0

        for region_id, region in self.regions.items():
            required_count = region.get('required_missions_completed', 0)
            required_abilities = region.get('required_abilities', [])

            # Check if requirements are reasonable
            total_missions = len(self.missions)
            if required_count > total_missions:
                self.report.add_error(
                    'IMPOSSIBLE_REGION',
                    f"Region '{region_id}' requires {required_count} missions "
                    f"but only {total_missions} exist",
                    None
                )

            # Warn if region requires too many missions
            if required_count > total_missions * 0.8:
                self.report.add_warning(
                    'LATE_REGION',
                    f"Region '{region_id}' requires {required_count}/{total_missions} missions "
                    "(may be inaccessible until very late game)",
                    None
                )

    def _validate_difficulty_progression(self):
        """Validate difficulty increases reasonably"""
        # Group missions by unlock depth
        depths = self._calculate_mission_depths()

        # Check if difficulty generally increases with depth
        for mission_id, mission in self.missions.items():
            depth = depths.get(mission_id, 0)
            difficulty = mission.get('difficulty', 1)

            # Very rough heuristic: difficulty should be near depth
            expected_difficulty_min = max(1, depth - 2)
            expected_difficulty_max = depth + 3

            if difficulty < expected_difficulty_min:
                self.report.add_warning(
                    'DIFFICULTY_TOO_LOW',
                    f"Difficulty {difficulty} seems low for mission depth {depth}",
                    mission_id
                )
            elif difficulty > expected_difficulty_max:
                self.report.add_warning(
                    'DIFFICULTY_TOO_HIGH',
                    f"Difficulty {difficulty} seems high for mission depth {depth}",
                    mission_id
                )

    # ============================================================
    # Helper Methods
    # ============================================================

    def _calculate_mission_depths(self) -> Dict[str, int]:
        """Calculate depth of each mission in unlock tree (BFS distance from start)"""
        # Find starting missions
        starting_missions = [
            m_id for m_id, m in self.missions.items()
            if not m.get('unlock_requirements', [])
        ]

        depths = {m_id: 0 for m_id in starting_missions}
        queue = deque(starting_missions)

        # Build forward dependency graph
        unlocks = defaultdict(list)
        for mission_id, mission in self.missions.items():
            for req_id in mission.get('unlock_requirements', []):
                unlocks[req_id].append(mission_id)

        while queue:
            current = queue.popleft()
            current_depth = depths[current]

            for unlocked_id in unlocks.get(current, []):
                if unlocked_id not in depths:
                    requirements = self.missions[unlocked_id].get('unlock_requirements', [])
                    # Depth is max of all requirement depths + 1
                    if all(req in depths for req in requirements):
                        new_depth = max(depths[req] for req in requirements) + 1
                        depths[unlocked_id] = new_depth
                        queue.append(unlocked_id)

        return depths


# ============================================================
# Command Line Interface
# ============================================================

def load_missions_data(file_path: Path) -> dict:
    """Load missions.json file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {file_path}: {e}")
        sys.exit(1)


def print_report(report: ValidationReport):
    """Print validation report"""
    print("=" * 70)
    print("CAMPAIGN VALIDATION REPORT")
    print("=" * 70)
    print()

    # Print errors
    if report.errors:
        print(f"ERRORS ({len(report.errors)}):")
        print("-" * 70)
        for error in report.errors:
            print(f"  {error}")
        print()

    # Print warnings
    if report.warnings:
        print(f"WARNINGS ({len(report.warnings)}):")
        print("-" * 70)
        for warning in report.warnings:
            print(f"  {warning}")
        print()

    # Print info
    if report.info:
        print(f"INFO ({len(report.info)}):")
        print("-" * 70)
        for info in report.info:
            print(f"  {info}")
        print()

    # Summary
    print("=" * 70)
    if report.is_valid():
        if report.has_warnings():
            print("RESULT: VALID (with warnings)")
            print()
            print("The campaign is playable but has some issues that should be reviewed.")
        else:
            print("RESULT: VALID")
            print()
            print("The campaign is well-structured with no issues detected!")
    else:
        print("RESULT: INVALID")
        print()
        print(f"The campaign has {len(report.errors)} error(s) that must be fixed.")
        print("These errors may cause soft-locks or unplayable scenarios.")

    print("=" * 70)


def main():
    """Run campaign validation from command line"""
    # Get project root
    project_root = Path(__file__).parent.parent
    missions_file = project_root / "data" / "missions.json"

    print("Campaign Validator v0.7.0")
    print(f"Validating: {missions_file}")
    print()

    # Load missions data
    missions_data = load_missions_data(missions_file)

    # Create validator
    validator = CampaignValidator(missions_data)

    # Run validation
    report = validator.validate_all()

    # Print report
    print_report(report)

    # Exit with appropriate code
    if report.is_valid():
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
