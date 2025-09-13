"""Test script to verify RAG API server works correctly."""
import os
import sys
import requests
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_rag_api():
    """Test that the RAG API server works correctly."""
    print("Testing RAG API server...")
    
    # First, let's check if the RAG API server is running
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            print("RAG API server is running")
        else:
            print(f"RAG API server returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("RAG API server is not running. Please start it with: uv run python -m rag.api.server")
        return False
    except Exception as e:
        print(f"Error connecting to RAG API server: {e}")
        return False
    
    # Create a simple test file
    test_file_path = "test_document.txt"
    with open(test_file_path, "w") as f:
        f.write("This is a simple test document for RAG processing.")
    
    try:
        # Test the process document endpoint
        response = requests.post(
            "http://localhost:8001/process/document",
            json={"file_path": os.path.abspath(test_file_path)},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"RAG API process document test result: {result}")
            if result.get("status") == "success":
                print("RAG API server is working correctly!")
                return True
            else:
                print(f"RAG API server returned error: {result.get('detail', 'Unknown error')}")
                return False
        else:
            print(f"RAG API server returned status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error testing RAG API server: {e}")
        return False
    finally:
        # Clean up the test file
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

if __name__ == "__main__":
    test_rag_api()