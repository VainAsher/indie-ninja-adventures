"""
Build script for creating PyInstaller executables.

Usage:
    python build.py --all          # Build all three versions
    python build.py --production   # Build production only
    python build.py --testing      # Build testing only
    python build.py --dev          # Build dev only
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path
import argparse


def run_command(cmd, env=None):
    """Run a command and return success status"""
    print(f"\n> {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env)
    return result.returncode == 0


def build(build_type, spec_file):
    """Build a specific configuration"""
    print(f"\n{'='*60}")
    print(f"Building {build_type.upper()}")
    print('='*60)

    # Set environment variable
    env = os.environ.copy()
    env['BUILD_MODE'] = build_type.upper()

    # Run PyInstaller
    cmd = ['pyinstaller', '--clean', spec_file]
    success = run_command(cmd, env=env)

    if success:
        print(f"\n{build_type.upper()} build completed successfully!")
    else:
        print(f"\nERROR: {build_type.upper()} build failed!")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description='Build Ninja Dash executables')
    parser.add_argument('--all', action='store_true', help='Build all configurations')
    parser.add_argument('--production', action='store_true', help='Build production')
    parser.add_argument('--testing', action='store_true', help='Build testing')
    parser.add_argument('--dev', action='store_true', help='Build development')

    args = parser.parse_args()

    # Change to build directory
    build_dir = Path(__file__).parent
    os.chdir(build_dir)

    # Check if PyInstaller is installed
    try:
        subprocess.run(['pyinstaller', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("PyInstaller not found. Installing...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])

    # Clean previous builds
    if (build_dir / 'dist').exists():
        print("Cleaning previous builds...")
        shutil.rmtree(build_dir / 'dist')
    if (build_dir / 'build').exists():
        shutil.rmtree(build_dir / 'build')

    # Determine what to build
    builds = []
    if args.all:
        builds = [
            ('production', 'ninja_dash_production.spec'),
            ('testing', 'ninja_dash_testing.spec'),
            ('dev', 'ninja_dash_dev.spec'),
        ]
    else:
        if args.production:
            builds.append(('production', 'ninja_dash_production.spec'))
        if args.testing:
            builds.append(('testing', 'ninja_dash_testing.spec'))
        if args.dev:
            builds.append(('dev', 'ninja_dash_dev.spec'))

    # Default to all if nothing specified
    if not builds:
        builds = [
            ('production', 'ninja_dash_production.spec'),
            ('testing', 'ninja_dash_testing.spec'),
            ('dev', 'ninja_dash_dev.spec'),
        ]

    # Build each configuration
    all_success = True
    for build_type, spec_file in builds:
        if not build(build_type, spec_file):
            all_success = False

    # Summary
    print(f"\n{'='*60}")
    if all_success:
        print("ALL BUILDS COMPLETED SUCCESSFULLY!")
    else:
        print("SOME BUILDS FAILED - Check output above")
    print('='*60)

    print("\nOutput directories:")
    for build_type, _ in builds:
        if build_type == "production":
            print("  - dist/ninja_dash.exe")
        else:
            dist_name = f"ninja_dash_{build_type}"
            print(f"  - dist/{dist_name}/")
    print()


if __name__ == '__main__':
    main()
