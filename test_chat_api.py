"""Simple test to verify chat endpoint works correctly."""
import requests
import json

def test_chat():
    # Create session for cookies
    session = requests.Session()
    
    # Login first (expects JSON)
    login_url = "http://localhost:8000/login"
    login_resp = session.post(login_url, json={"username": "admin", "password": "admin123"})
    print(f"Login: {login_resp.status_code} - {login_resp.text}")
    
    url = "http://localhost:8000/api/chat/"
    
    # Test 1: Database-specific alert query
    print("=" * 60)
    print("TEST 1: show me alerts for MIDDEVSTB")
    print("=" * 60)
    try:
        response = session.post(url, json={
            "message": "show me alerts for MIDDEVSTB",
            "new_conversation": True
        }, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print("Status: OK")
            print("Answer:\n", data.get('answer', 'N/A'))
            print("\nIntent:", data.get('question_type', 'N/A'))
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Exception: {e}")
    
    print("\n")
    
    # Test 2: Total alerts count
    print("=" * 60)
    print("TEST 2: how many total alerts")
    print("=" * 60)
    try:
        response = session.post(url, json={
            "message": "how many total alerts",
            "new_conversation": True
        }, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print("Status: OK")
            print("Answer:\n", data.get('answer', 'N/A'))
            print("\nIntent:", data.get('question_type', 'N/A'))
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Exception: {e}")
    
    print("\n")
    
    # Test 3: Standby issues
    print("=" * 60)
    print("TEST 3: show me standby issues")
    print("=" * 60)
    try:
        response = session.post(url, json={
            "message": "show me standby issues",
            "new_conversation": True
        }, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print("Status: OK")
            print("Answer:\n", data.get('answer', 'N/A'))
            print("\nIntent:", data.get('question_type', 'N/A'))
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_chat()
