#!/usr/bin/env python
"""
API Verification Script
Tests all endpoints to ensure 200 OK responses
"""
import sys
import time
try:
    # Python 3
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError, URLError
except ImportError:
    # Python 2
    from urllib2 import urlopen, Request, HTTPError, URLError

def test_endpoint(url, method="GET"):
    """Test a single endpoint"""
    try:
        if method == "POST":
            req = Request(url, data=b'{}', headers={'Content-Type': 'application/json'})
        else:
            req = Request(url)
        
        response = urlopen(req, timeout=10)
        status = response.getcode()
        
        if status == 200:
            print("[OK] {0} {1} -> 200 OK".format(method, url))
            return True
        else:
            print("[WARN] {0} {1} -> {2}".format(method, url, status))
            return False
    except HTTPError as e:
        print("[ERROR] {0} {1} -> {2} {3}".format(method, url, e.code, e.reason))
        return False
    except URLError as e:
        print("[ERROR] {0} {1} -> Connection failed: {2}".format(method, url, e.reason))
        return False
    except Exception as e:
        print("[ERROR] {0} {1} -> {2}".format(method, url, str(e)))
        return False

def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = sys.argv[2] if len(sys.argv) > 2 else "4540"
    base_url = "http://{0}:{1}".format(host, port)
    
    print("=" * 60)
    print("API VERIFICATION TEST")
    print("Base URL: {0}".format(base_url))
    print("=" * 60)
    
    # Wait for server to be ready
    print("\n[*] Waiting for server to be ready...")
    max_retries = 30
    for i in range(max_retries):
        try:
            urlopen("{0}/login".format(base_url), timeout=2)
            print("[OK] Server is ready!\n")
            break
        except:
            if i == max_retries - 1:
                print("[ERROR] Server not responding after 30 seconds")
                sys.exit(1)
            time.sleep(1)
            sys.stdout.write(".")
            sys.stdout.flush()
    
    # Test endpoints
    endpoints = [
        ("GET", "/api/dashboard/summary"),
        ("GET", "/api/dashboard/databases"),
        ("GET", "/api/dashboard/incidents"),
        ("GET", "/api/dashboard/alert-validation"),
        ("GET", "/api/dashboard/risk-trend"),
        ("POST", "/api/chat/warmup"),
    ]
    
    results = []
    for method, path in endpoints:
        url = "{0}{1}".format(base_url, path)
        success = test_endpoint(url, method)
        results.append(success)
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print("RESULTS: {0}/{1} tests passed".format(passed, total))
    
    if passed == total:
        print("STATUS: ALL TESTS PASSED ✓")
        print("=" * 60)
        sys.exit(0)
    else:
        print("STATUS: SOME TESTS FAILED ✗")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()
