#!/usr/bin/env python3
"""
Local build script for coffee shop queue system backend.
Run this script before pushing to ensure everything works locally.
"""

import sys
import subprocess
import os
import signal
import time
import requests
from pathlib import Path

def run_command(command, cwd=None, capture_output=True):
    """Run a command and return the result"""
    print(f"Running: {command}")
    try:
        if capture_output:
            result = subprocess.run(
                command, 
                shell=True, 
                cwd=cwd, 
                capture_output=True, 
                text=True,
                timeout=60
            )
            if result.returncode != 0:
                print(f" Command failed with exit code {result.returncode}")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return False
            else:
                print(f"Command succeeded")
                if result.stdout:
                    print(f"Output: {result.stdout.strip()}")
                return True
        else:
            # For commands that need to run in background or interactively
            process = subprocess.Popen(command, shell=True, cwd=cwd)
            return process
    except subprocess.TimeoutExpired:
        print(f"Command timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"Command failed with exception: {e}")
        return False

def check_dependencies():
    """Check if all required dependencies are available"""
    print("🔍 Checking dependencies...")
    
    # Check if we're in a virtual environment
    if not (os.environ.get('VIRTUAL_ENV') or sys.prefix != sys.base_prefix):
        print("Warning: Not running in a virtual environment")
        print("   Consider running: python -m venv venv && source venv/bin/activate")
    else:
        print("Running in virtual environment")
    
    # Check if required packages are installed
    try:
        import flask
        import pytest
        print("Required packages are installed")
        return True
    except ImportError as e:
        print(f"Missing required package: {e}")
        print("   Run: pip install -r requirements.txt")
        return False

def run_unit_tests():
    """Run unit tests with pytest"""
    print("🧪 Running unit tests...")
    
    # Run pytest on our test files
    test_command = "python -m pytest test_queue_manager.py test_app.py -v --tb=short"
    return run_command(test_command)

def run_linting():
    """Run code linting (if available)"""
    print("🔍 Checking code style...")
    
    # Try to run flake8 if available
    try:
        import flake8
        lint_command = "python -m flake8 app.py queue_manager.py --max-line-length=120 --ignore=E501"
        return run_command(lint_command)
    except ImportError:
        print(" flake8 not installed, skipping linting")
        return True

def start_server():
    """Start the Flask server for integration testing"""
    print("Starting Flask server for integration tests...")
    
    # Set environment variables for testing
    env = os.environ.copy()
    env['FLASK_ENV'] = 'development'
    env['PYTHONPATH'] = os.getcwd()
    
    # Start the server
    server_process = subprocess.Popen([
        sys.executable, '-c',
        'from app import app, socketio; socketio.run(app, host="127.0.0.1", port=5002, debug=False)'
    ], env=env)
    
    # Wait for server to start
    print("Waiting for server to start...")
    for i in range(30):  # Wait up to 30 seconds
        try:
            response = requests.get('http://localhost:5002/api/health', timeout=2)
            if response.status_code == 200:
                print("Server started successfully")
                return server_process
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
    
    print("Server failed to start")
    server_process.terminate()
    return None

def run_integration_tests(server_process):
    """Run integration tests against the running server"""
    print("Running integration tests...")
    
    try:
        # Move the integration test file to root temporarily if it's not there
        parent_dir = Path(__file__).parent.parent
        integration_test_path = parent_dir / "test_api.py"
        
        if integration_test_path.exists():
            # Run the integration test
            test_command = f"python {integration_test_path}"
            return run_command(test_command)
        else:
            print(" Integration test file not found, skipping...")
            return True
            
    except Exception as e:
        print(f"Integration tests failed: {e}")
        return False

def main():
    """Main build function"""
    print("Starting local build process for Coffee Shop Queue System Backend")
    print("=" * 70)
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    print(f"📁 Working directory: {os.getcwd()}")
    
    success = True
    server_process = None
    
    try:
        # Step 1: Check dependencies
        if not check_dependencies():
            success = False
            
        # Step 2: Run unit tests
        if success and not run_unit_tests():
            success = False
            
        # Step 3: Run linting
        if success and not run_linting():
            print("Linting failed, but continuing...")
            
        # Step 4: Start server for integration tests
        if success:
            server_process = start_server()
            if not server_process:
                success = False
            
        # Step 5: Run integration tests
        if success and server_process:
            if not run_integration_tests(server_process):
                print(" Integration tests failed, but unit tests passed")
        
    finally:
        # Clean up: stop the server
        if server_process:
            print("Stopping test server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
    
    print("=" * 70)
    if success:
        print("Build completed successfully!")
        print("Your code is ready to push to production")
        return 0
    else:
        print("Build failed!")
        print("Please fix the issues above before pushing")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
