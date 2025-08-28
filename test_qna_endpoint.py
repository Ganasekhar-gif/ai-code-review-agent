#!/usr/bin/env python3
"""
Test script for the Q&A endpoint
Tests the search functionality with a real query
"""

import requests
import json

def test_qna_endpoint():
    """Test the Q&A endpoint"""
    base_url = "http://localhost:8002"
    
    print("🧪 Testing Q&A Endpoint...")
    print("=" * 50)
    
    # Test data
    test_data = {
        "query": "How does the fraud detection system work?",
        "repo_url": "https://github.com/username/real-time-credit-card-fraud-detection-system"
    }
    
    try:
        print(f"1. Testing Q&A endpoint with query: {test_data['query']}")
        print(f"   Repository: {test_data['repo_url']}")
        
        response = requests.post(f"{base_url}/search", json=test_data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Q&A endpoint working successfully!")
            print(f"   Query: {result['query']}")
            print(f"   Answer: {result['answer'][:200]}...")
            print(f"   Sources: {result['sources']}")
        else:
            print(f"❌ Q&A endpoint failed: {response.status_code}")
            print(f"   Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running on port 8002")
        return False
    except Exception as e:
        print(f"❌ Error testing Q&A endpoint: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Q&A endpoint testing completed!")
    return True

if __name__ == "__main__":
    success = test_qna_endpoint()
    if success:
        print("\n🚀 Your Q&A pipeline is working correctly!")
        print("🌐 Open your browser and go to: http://localhost:8002")
        print("📝 Try asking questions about your code!")
    else:
        print("\n❌ Q&A testing failed. Check server logs.")

