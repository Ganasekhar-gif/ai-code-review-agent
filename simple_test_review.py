#!/usr/bin/env python3
"""
Simple test script for the AI Code Review Agent
Quick test to verify basic functionality
"""

import os
import sys
import tempfile
import subprocess

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_basic_functionality():
    """Test basic functionality of the review agent"""
    print("🧪 Testing AI Code Review Agent...")
    
    try:
        # Test imports
        print("📦 Testing imports...")
        from review import run_command, get_git_diff, stream_review
        print("✅ Imports successful")
        
        # Test command execution
        print("🔧 Testing command execution...")
        code, out, err = run_command("echo 'test'")
        if code == 0 and "test" in out:
            print("✅ Command execution successful")
        else:
            print("❌ Command execution failed")
            return False
        
        # Test git functionality
        print("📁 Testing git functionality...")
        test_dir = tempfile.mkdtemp()
        try:
            # Create a test git repo
            subprocess.run(["git", "init"], cwd=test_dir, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=test_dir, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=test_dir, check=True)
            
            # Create a test file
            test_file = os.path.join(test_dir, "test.py")
            with open(test_file, "w") as f:
                f.write("def test():\n    x=1+2\n    return x\n")
            
            # Add and commit
            subprocess.run(["git", "add", "test.py"], cwd=test_dir, check=True)
            subprocess.run(["git", "commit", "-m", "Initial"], cwd=test_dir, check=True)
            
            # Make changes
            with open(test_file, "w") as f:
                f.write("def test():\n    x = 1 + 2  # Fixed\n    return x\n")
            
            # Test git diff
            diff = get_git_diff(test_dir)
            if diff and "test.py" in diff:
                print("✅ Git diff functionality working")
            else:
                print("❌ Git diff functionality failed")
                return False
                
        finally:
            shutil.rmtree(test_dir, ignore_errors=True)
        
        print("🎉 All basic tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_tools_availability():
    """Check if required tools are available"""
    print("\n🔍 Checking required tools...")
    
    tools = {
        "git": "Git version control",
        "flake8": "Python linting",
        "pylint": "Python bug detection", 
        "autopep8": "Python code formatting"
    }
    
    missing = []
    for tool, description in tools.items():
        try:
            result = subprocess.run([tool, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0]
                print(f"✅ {tool}: {version}")
            else:
                print(f"❌ {tool}: Not working properly")
                missing.append(tool)
        except FileNotFoundError:
            print(f"❌ {tool}: Not installed")
            missing.append(tool)
    
    if missing:
        print(f"\n⚠️  Missing tools: {', '.join(missing)}")
        print("Install with: pip install flake8 pylint autopep8")
        print("Note: git should be installed separately")
    else:
        print("\n🎉 All required tools are available!")

def main():
    """Main test function"""
    print("=" * 50)
    print("AI Code Review Agent - Test Suite")
    print("=" * 50)
    
    # Check tools first
    test_tools_availability()
    
    print("\n" + "=" * 50)
    
    # Test basic functionality
    if test_basic_functionality():
        print("\n🎯 Ready to run full test suite!")
        print("Run: python test_review.py")
    else:
        print("\n❌ Basic tests failed. Check your setup.")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        import shutil
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)




