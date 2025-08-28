#!/usr/bin/env python3
"""
Test file for the AI Code Review Agent
Tests the review functionality including git diff generation, bug detection, linting, and auto-fixing
"""

import os
import sys
import tempfile
import shutil
import subprocess
import unittest
from unittest.mock import patch, MagicMock, mock_open
import json

# Add the app directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from review import (
    run_command, 
    get_repo_path, 
    get_git_diff, 
    run_flake8_on_files, 
    run_bug_checks, 
    auto_fix_files, 
    stream_review
)


class TestReviewAgent(unittest.TestCase):
    """Test cases for the AI Code Review Agent"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.repo_dir = os.path.join(self.test_dir, "test-repo")
        os.makedirs(self.repo_dir)
        
        # Create a mock git repository
        self._setup_mock_git_repo()
        
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _setup_mock_git_repo(self):
        """Set up a mock git repository for testing"""
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=self.repo_dir, check=True)
        
        # Create a test Python file with some issues
        test_file_path = os.path.join(self.repo_dir, "test_file.py")
        with open(test_file_path, "w") as f:
            f.write("""def test_function():
    x=1+2
    if x==3:
        print('hello world')
    return x

class TestClass:
    def __init__(self):
        self.value=None
""")
        
        # Add and commit the file
        subprocess.run(["git", "add", "test_file.py"], cwd=self.repo_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.repo_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.repo_dir, check=True)
        
        # Make some changes to create a diff
        with open(test_file_path, "w") as f:
            f.write("""def test_function():
    x=1+2  # This line has spacing issues
    if x==3:
        print('hello world')  # Missing space after comma
    return x

class TestClass:
    def __init__(self):
        self.value=None  # Missing space around operator
        self.another_value = "test"
""")
    
    def test_run_command_success(self):
        """Test successful command execution"""
        code, out, err = run_command("echo 'hello world'")
        self.assertEqual(code, 0)
        self.assertIn("hello world", out)
        self.assertEqual(err, "")
    
    def test_run_command_failure(self):
        """Test failed command execution"""
        code, out, err = run_command("exit 1")
        self.assertEqual(code, 1)
    
    def test_get_git_diff(self):
        """Test git diff generation"""
        diff = get_git_diff(self.repo_dir)
        self.assertIsInstance(diff, str)
        self.assertIn("test_file.py", diff)
        self.assertIn("+", diff)  # Should contain additions
        self.assertIn("-", diff)  # Should contain deletions
    
    def test_get_git_diff_staged(self):
        """Test staged git diff"""
        # Stage the changes
        subprocess.run(["git", "add", "test_file.py"], cwd=self.repo_dir, check=True)
        
        diff = get_git_diff(self.repo_dir, staged=True)
        self.assertIsInstance(diff, str)
        self.assertIn("test_file.py", diff)
    
    def test_get_git_diff_no_changes(self):
        """Test git diff when no changes exist"""
        # Reset all changes
        subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=self.repo_dir, check=True)
        
        diff = get_git_diff(self.repo_dir)
        self.assertEqual(diff, "")
    
    def test_run_flake8_on_files(self):
        """Test flake8 linting on Python files"""
        files = ["test_file.py"]
        results = list(run_flake8_on_files(self.repo_dir, files))
        
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result["type"], "lint")
        self.assertEqual(result["file"], "test_file.py")
        self.assertIsInstance(result["returncode"], int)
    
    def test_run_bug_checks(self):
        """Test bug checking with pylint"""
        files = ["test_file.py"]
        results = list(run_bug_checks(self.repo_dir, files))
        
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result["type"], "bugcheck")
        self.assertEqual(result["file"], "test_file.py")
        self.assertIsInstance(result["returncode"], int)
    
    def test_auto_fix_files(self):
        """Test automatic file fixing"""
        files = ["test_file.py"]
        results = list(auto_fix_files(self.repo_dir, files))
        
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result["type"], "autofix")
        self.assertEqual(result["file"], "test_file.py")
        self.assertIsInstance(result["fixed"], bool)
    
    def test_stream_review_basic(self):
        """Test basic streaming review functionality"""
        # Mock the get_repo_path function to return our test repo
        with patch('review.get_repo_path', return_value=self.repo_dir):
            results = list(stream_review("https://github.com/test/repo"))
            
            # Should have at least diff chunks and changed files
            self.assertGreater(len(results), 0)
            
            # Check for expected result types
            result_types = [r["type"] for r in results]
            self.assertIn("changed_files", result_types)
            self.assertIn("diff", result_types)
    
    def test_stream_review_with_autofix(self):
        """Test streaming review with auto-fix enabled"""
        with patch('review.get_repo_path', return_value=self.repo_dir):
            results = list(stream_review("https://github.com/test/repo", auto_fix=True))
            
            # Should have autofix results
            result_types = [r["type"] for r in results]
            self.assertIn("autofix", result_types)
    
    def test_stream_review_no_changes(self):
        """Test streaming review when no changes exist"""
        # Reset all changes
        subprocess.run(["git", "reset", "--hard", "HEAD"], cwd=self.repo_dir, check=True)
        
        with patch('review.get_repo_path', return_value=self.repo_dir):
            results = list(stream_review("https://github.com/test/repo"))
            
            # Should have info message about no changes
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["type"], "info")
            self.assertIn("No changes found", results[0]["message"])
    
    def test_stream_review_staged_changes(self):
        """Test streaming review with staged changes"""
        # Stage the changes
        subprocess.run(["git", "add", "test_file.py"], cwd=self.repo_dir, check=True)
        
        with patch('review.get_repo_path', return_value=self.repo_dir):
            results = list(stream_review("https://github.com/test/repo", staged=True))
            
            # Should have results
            self.assertGreater(len(results), 0)
    
    def test_error_handling_invalid_repo(self):
        """Test error handling for invalid repository"""
        with self.assertRaises(Exception):
            get_git_diff("/invalid/path")
    
    def test_file_filtering(self):
        """Test that only Python files are processed for linting and bug checking"""
        # Create a non-Python file
        non_py_file = os.path.join(self.repo_dir, "test.txt")
        with open(non_py_file, "w") as f:
            f.write("This is not a Python file")
        
        files = ["test_file.py", "test.txt"]
        
        # Test flake8 filtering
        flake8_results = list(run_flake8_on_files(self.repo_dir, files))
        self.assertEqual(len(flake8_results), 1)  # Only Python file should be processed
        self.assertEqual(flake8_results[0]["file"], "test_file.py")
        
        # Test bug check filtering
        bug_results = list(run_bug_checks(self.repo_dir, files))
        self.assertEqual(len(bug_results), 1)  # Only Python file should be processed
        self.assertEqual(bug_results[0]["file"], "test_file.py")
        
        # Test autofix filtering
        autofix_results = list(auto_fix_files(self.repo_dir, files))
        self.assertEqual(len(autofix_results), 1)  # Only Python file should be processed
        self.assertEqual(autofix_results[0]["file"], "test_file.py")


class TestReviewAgentIntegration(unittest.TestCase):
    """Integration tests for the review agent"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.repo_dir = os.path.join(self.test_dir, "integration-repo")
        os.makedirs(self.repo_dir)
        
        # Create a more complex test repository
        self._setup_integration_repo()
    
    def tearDown(self):
        """Clean up integration test environment"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def _setup_integration_repo(self):
        """Set up a complex test repository for integration testing"""
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=self.repo_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.repo_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo_dir, check=True)
        
        # Create multiple Python files with various issues
        files_content = {
            "main.py": """import os
import sys

def main():
    x=1+2
    if x==3:
        print('hello world')
    return x

if __name__=='__main__':
    main()
""",
            "utils.py": """def helper_function():
    value=None
    return value

class HelperClass:
    def __init__(self):
        self.data=[]
""",
            "config.py": """# Configuration file
DEBUG=True
API_KEY="test_key"
DATABASE_URL="sqlite:///test.db"
"""
        }
        
        # Create and commit files
        for filename, content in files_content.items():
            filepath = os.path.join(self.repo_dir, filename)
            with open(filepath, "w") as f:
                f.write(content)
            subprocess.run(["git", "add", filename], cwd=self.repo_dir, check=True)
        
        subprocess.run(["git", "commit", "-m", "Initial commit with multiple files"], cwd=self.repo_dir, check=True)
        
        # Make changes to create diffs
        updated_content = {
            "main.py": """import os
import sys

def main():
    x = 1 + 2  # Fixed spacing
    if x == 3:  # Fixed spacing
        print('hello world')  # Fixed spacing
    return x

if __name__ == '__main__':  # Fixed spacing
    main()
""",
            "utils.py": """def helper_function():
    value = None  # Fixed spacing
    return value

class HelperClass:
    def __init__(self):
        self.data = []  # Fixed spacing
""",
            "config.py": """# Configuration file
DEBUG = True  # Fixed spacing
API_KEY = "test_key"  # Fixed spacing
DATABASE_URL = "sqlite:///test.db"  # Fixed spacing
"""
        }
        
        # Update files
        for filename, content in updated_content.items():
            filepath = os.path.join(self.repo_dir, filename)
            with open(filepath, "w") as f:
                f.write(content)
    
    def test_full_review_workflow(self):
        """Test the complete review workflow"""
        with patch('review.get_repo_path', return_value=self.repo_dir):
            results = list(stream_review("https://github.com/test/repo", auto_fix=True))
            
            # Verify we have all expected result types
            result_types = [r["type"] for r in results]
            self.assertIn("diff", result_types)
            self.assertIn("changed_files", result_types)
            self.assertIn("lint", result_types)
            self.assertIn("bugcheck", result_types)
            self.assertIn("autofix", result_types)
            
            # Verify changed files
            changed_files_result = next(r for r in results if r["type"] == "changed_files")
            self.assertIn("main.py", changed_files_result["files"])
            self.assertIn("utils.py", changed_files_result["files"])
            self.assertIn("config.py", changed_files_result["files"])
    
    def test_review_with_staged_changes(self):
        """Test review with staged changes"""
        # Stage all changes
        subprocess.run(["git", "add", "."], cwd=self.repo_dir, check=True)
        
        with patch('review.get_repo_path', return_value=self.repo_dir):
            results = list(stream_review("https://github.com/test/repo", staged=True, auto_fix=True))
            
            # Should have results
            self.assertGreater(len(results), 0)
            
            # Verify staged diff is processed
            diff_results = [r for r in results if r["type"] == "diff"]
            self.assertGreater(len(diff_results), 0)


def run_tests():
    """Run all tests"""
    # Create test suite using modern unittest approach
    test_suite = unittest.TestSuite()
    
    # Add test classes using TestLoader
    loader = unittest.TestLoader()
    test_suite.addTest(loader.loadTestsFromTestCase(TestReviewAgent))
    test_suite.addTest(loader.loadTestsFromTestCase(TestReviewAgentIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    # Check if required tools are available
    required_tools = ["git", "flake8", "pylint", "autopep8"]
    missing_tools = []
    
    for tool in required_tools:
        try:
            subprocess.run([tool, "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_tools.append(tool)
    
    if missing_tools:
        print(f"Warning: The following tools are not available: {', '.join(missing_tools)}")
        print("Some tests may fail or be skipped.")
        print("To install missing tools:")
        print("  pip install flake8 pylint autopep8")
        print("  # Note: git should be installed separately")
    
    # Try to run tests using the modern approach
    try:
        exit_code = run_tests()
        sys.exit(exit_code)
    except Exception as e:
        print(f"Error running tests: {e}")
        print("Trying alternative test runner...")
        
        # Alternative: Use unittest.main() which is more compatible
        try:
            unittest.main(verbosity=2, exit=False)
        except Exception as e2:
            print(f"Alternative test runner also failed: {e2}")
            sys.exit(1)
