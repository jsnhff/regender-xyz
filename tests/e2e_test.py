#!/usr/bin/env python3
"""
End-to-end test for the complete book processing pipeline.

This test simulates a real user workflow:
1. Download books from Project Gutenberg
2. Parse books to JSON format
3. Validate JSON against source
4. Attempt transformation with Grok (expecting graceful failure)
5. Clean up all test files
"""

import os
import sys
import subprocess
import json
import shutil
from pathlib import Path
import time
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Test configuration
TEST_BOOK_COUNT = 2
TEST_DIRS = {
    'texts': 'book_texts',
    'json': 'book_json',
    'transforms': 'book_transforms'
}

# ANSI color codes for output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'


class E2ETestRunner:
    """Run end-to-end tests for the book processing pipeline."""
    
    def __init__(self):
        self.results = {
            'start_time': datetime.now(),
            'tests_passed': 0,
            'tests_failed': 0,
            'errors': [],
            'warnings': [],
            'outputs': {}
        }
        self.root_dir = Path(__file__).parent.parent
        self.cli_path = self.root_dir / 'regender_book_cli.py'
        
    def run_command(self, cmd: list, test_name: str, capture_output=True):
        """Run a command and capture output."""
        print(f"\n{BLUE}Running: {' '.join(cmd)}{RESET}")
        
        start_time = time.time()
        try:
            # Use the same Python interpreter
            if cmd[0] == 'python':
                cmd[0] = sys.executable
                
            result = subprocess.run(
                cmd,
                cwd=self.root_dir,
                capture_output=capture_output,
                text=True,
                check=False
            )
            elapsed = time.time() - start_time
            
            # Store output
            self.results['outputs'][test_name] = {
                'command': ' '.join(cmd),
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'elapsed': elapsed
            }
            
            # Print summary
            if result.returncode == 0:
                print(f"{GREEN}✓ {test_name} completed in {elapsed:.1f}s{RESET}")
                self.results['tests_passed'] += 1
            else:
                print(f"{RED}✗ {test_name} failed with code {result.returncode}{RESET}")
                self.results['tests_failed'] += 1
                self.results['errors'].append(f"{test_name}: Exit code {result.returncode}")
                
            # Show stderr if present
            if result.stderr:
                print(f"{YELLOW}STDERR:{RESET}\n{result.stderr}")
                
            return result
            
        except Exception as e:
            self.results['errors'].append(f"{test_name}: {str(e)}")
            self.results['tests_failed'] += 1
            print(f"{RED}✗ {test_name} failed with exception: {e}{RESET}")
            return None
    
    def check_directories(self):
        """Check if test directories exist and are empty."""
        print(f"\n{BLUE}=== Checking Directories ==={RESET}")
        
        for name, dir_path in TEST_DIRS.items():
            path = self.root_dir / dir_path
            if path.exists():
                file_count = len(list(path.glob('*')))
                if file_count > 0:
                    print(f"{YELLOW}⚠ {dir_path} contains {file_count} files{RESET}")
                    self.results['warnings'].append(f"{dir_path} not empty: {file_count} files")
                else:
                    print(f"{GREEN}✓ {dir_path} is empty{RESET}")
            else:
                print(f"{GREEN}✓ {dir_path} will be created{RESET}")
                
    def test_download(self):
        """Test downloading books from Gutenberg."""
        print(f"\n{BLUE}=== Testing Book Download ==={RESET}")
        
        result = self.run_command(
            ['python', str(self.cli_path), 'download', '--count', str(TEST_BOOK_COUNT)],
            'download_books'
        )
        
        if result and result.returncode == 0:
            # Check if files were downloaded
            texts_dir = self.root_dir / TEST_DIRS['texts']
            if texts_dir.exists():
                downloaded_files = list(texts_dir.glob('*.txt'))
                print(f"Downloaded {len(downloaded_files)} files:")
                for f in downloaded_files[:5]:  # Show first 5
                    print(f"  - {f.name}")
                    
                if len(downloaded_files) == 0:
                    self.results['errors'].append("No files downloaded")
                    return False
                    
                return True
            else:
                self.results['errors'].append(f"{TEST_DIRS['texts']} directory not created")
                return False
        return False
    
    def test_list_books(self):
        """Test listing downloaded books."""
        print(f"\n{BLUE}=== Testing Book Listing ==={RESET}")
        
        result = self.run_command(
            ['python', str(self.cli_path), 'list'],
            'list_books'
        )
        
        if result and result.returncode == 0:
            # Check output contains book listings
            if 'Found' in result.stdout and 'books' in result.stdout:
                print(f"{GREEN}✓ Book listing shows downloaded books{RESET}")
                return True
            else:
                self.results['warnings'].append("List command succeeded but output unexpected")
        return False
    
    def test_process_to_json(self):
        """Test processing books to JSON format."""
        print(f"\n{BLUE}=== Testing JSON Processing ==={RESET}")
        
        result = self.run_command(
            ['python', str(self.cli_path), 'process'],
            'process_to_json'
        )
        
        if result and result.returncode == 0:
            # Check if JSON files were created
            json_dir = self.root_dir / TEST_DIRS['json']
            if json_dir.exists():
                json_files = list(json_dir.glob('*.json'))
                print(f"Created {len(json_files)} JSON files:")
                
                # Validate JSON structure of first file
                if json_files:
                    try:
                        with open(json_files[0], 'r') as f:
                            book_data = json.load(f)
                        
                        # Check required fields
                        required_fields = ['metadata', 'chapters', 'statistics']
                        missing = [f for f in required_fields if f not in book_data]
                        
                        if missing:
                            self.results['errors'].append(f"JSON missing fields: {missing}")
                        else:
                            print(f"{GREEN}✓ JSON structure valid{RESET}")
                            print(f"  Title: {book_data['metadata'].get('title', 'Unknown')}")
                            print(f"  Chapters: {len(book_data['chapters'])}")
                            print(f"  Sentences: {book_data['statistics']['total_sentences']}")
                            return True
                            
                    except Exception as e:
                        self.results['errors'].append(f"JSON validation error: {e}")
                        
                return len(json_files) > 0
            else:
                self.results['errors'].append(f"{TEST_DIRS['json']} directory not created")
        return False
    
    def test_validate_json(self):
        """Test validating JSON against source texts."""
        print(f"\n{BLUE}=== Testing JSON Validation ==={RESET}")
        
        result = self.run_command(
            ['python', str(self.cli_path), 'validate'],
            'validate_json'
        )
        
        if result:
            # Check validation output
            if 'Valid:' in result.stdout:
                # Extract validation stats
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Valid:' in line:
                        print(f"  {line.strip()}")
                    elif 'Invalid:' in line:
                        print(f"  {line.strip()}")
                    elif 'Warnings:' in line:
                        print(f"  {line.strip()}")
                        
                # Check if validation report was created
                report_path = self.root_dir / 'validation_report.txt'
                if report_path.exists():
                    print(f"{GREEN}✓ Validation report created{RESET}")
                    # Clean up report
                    report_path.unlink()
                    
                return result.returncode == 0
        return False
    
    def test_transform_with_grok(self):
        """Test transformation with Grok (expecting graceful failure)."""
        print(f"\n{BLUE}=== Testing Grok Transformation ==={RESET}")
        
        # Get first JSON file
        json_dir = self.root_dir / TEST_DIRS['json']
        json_files = list(json_dir.glob('*.json'))
        
        if not json_files:
            self.results['errors'].append("No JSON files to transform")
            return False
            
        first_json = json_files[0]
        output_json = json_dir / f"{first_json.stem}_grok_test.json"
        
        result = self.run_command(
            [
                'python', str(self.cli_path), 'transform',
                str(first_json),
                '-o', str(output_json),
                '--type', 'comprehensive',
                '--model', 'grok-beta'
            ],
            'transform_grok'
        )
        
        # We expect this to fail gracefully
        if result:
            if result.returncode != 0:
                # Check for graceful failure
                if 'Error' in result.stderr or 'Error' in result.stdout:
                    print(f"{GREEN}✓ Grok transformation failed gracefully as expected{RESET}")
                    
                    # Check error message
                    error_output = result.stderr + result.stdout
                    if 'grok' in error_output.lower() or 'provider' in error_output.lower():
                        print(f"  Error mentions Grok/provider issue")
                        return True
                    else:
                        self.results['warnings'].append("Error doesn't clearly indicate Grok issue")
                        return True
                else:
                    self.results['errors'].append("Failed but no clear error message")
            else:
                # Unexpected success
                self.results['warnings'].append("Grok transformation succeeded unexpectedly")
                # Clean up output file if created
                if output_json.exists():
                    output_json.unlink()
                    
        return False
    
    def cleanup(self):
        """Clean up all test files and directories."""
        print(f"\n{BLUE}=== Cleaning Up ==={RESET}")
        
        cleanup_count = 0
        
        for name, dir_path in TEST_DIRS.items():
            path = self.root_dir / dir_path
            if path.exists():
                file_count = len(list(path.glob('*')))
                if file_count > 0:
                    try:
                        shutil.rmtree(path)
                        path.mkdir(exist_ok=True)
                        cleanup_count += file_count
                        print(f"{GREEN}✓ Cleaned {file_count} files from {dir_path}{RESET}")
                    except Exception as e:
                        self.results['errors'].append(f"Cleanup error for {dir_path}: {e}")
                        print(f"{RED}✗ Failed to clean {dir_path}: {e}{RESET}")
                        
        print(f"Total files cleaned: {cleanup_count}")
        
    def generate_report(self):
        """Generate detailed test report."""
        print(f"\n{BLUE}=== Test Report ==={RESET}")
        
        total_tests = self.results['tests_passed'] + self.results['tests_failed']
        elapsed = (datetime.now() - self.results['start_time']).total_seconds()
        
        print(f"\nSummary:")
        print(f"  Total tests: {total_tests}")
        print(f"  {GREEN}Passed: {self.results['tests_passed']}{RESET}")
        print(f"  {RED}Failed: {self.results['tests_failed']}{RESET}")
        print(f"  Time elapsed: {elapsed:.1f}s")
        
        if self.results['errors']:
            print(f"\n{RED}Errors:{RESET}")
            for error in self.results['errors']:
                print(f"  - {error}")
                
        if self.results['warnings']:
            print(f"\n{YELLOW}Warnings:{RESET}")
            for warning in self.results['warnings']:
                print(f"  - {warning}")
                
        # Detailed output analysis
        print(f"\n{BLUE}Detailed Results:{RESET}")
        
        for test_name, output in self.results['outputs'].items():
            print(f"\n{test_name}:")
            print(f"  Command: {output['command']}")
            print(f"  Return code: {output['returncode']}")
            print(f"  Elapsed: {output['elapsed']:.1f}s")
            
            # Analyze stdout for key information
            stdout = output['stdout']
            if test_name == 'download_books':
                if 'Downloaded:' in stdout:
                    for line in stdout.split('\n'):
                        if 'Downloaded:' in line or 'Failed:' in line:
                            print(f"  {line.strip()}")
                            
            elif test_name == 'process_to_json':
                if 'Successful:' in stdout:
                    for line in stdout.split('\n'):
                        if 'Successful:' in line or 'Failed:' in line:
                            print(f"  {line.strip()}")
                            
            elif test_name == 'validate_json':
                if 'Valid:' in stdout:
                    for line in stdout.split('\n'):
                        if 'Valid:' in line or 'Invalid:' in line or 'Warnings:' in line:
                            print(f"  {line.strip()}")
        
        # Save detailed report
        report_path = self.root_dir / 'tests' / 'e2e_test_report.json'
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\n{GREEN}Detailed report saved to: {report_path}{RESET}")
        
    def run_all_tests(self):
        """Run all tests in sequence."""
        print(f"{BLUE}Starting End-to-End Test Suite{RESET}")
        print(f"Time: {self.results['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Pre-flight checks
        self.check_directories()
        
        # Run test pipeline
        tests = [
            ("Download Books", self.test_download),
            ("List Books", self.test_list_books),
            ("Process to JSON", self.test_process_to_json),
            ("Validate JSON", self.test_validate_json),
            ("Transform with Grok", self.test_transform_with_grok)
        ]
        
        for test_name, test_func in tests:
            if not test_func():
                print(f"{YELLOW}⚠ {test_name} had issues, continuing...{RESET}")
                
        # Cleanup
        self.cleanup()
        
        # Generate report
        self.generate_report()
        
        # Return success if all critical tests passed
        critical_failures = self.results['tests_failed']
        return critical_failures == 0 or (critical_failures == 1 and 'grok' in str(self.results['errors']).lower())


def main():
    """Run the end-to-end test suite."""
    runner = E2ETestRunner()
    success = runner.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()