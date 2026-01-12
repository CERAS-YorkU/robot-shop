#!/usr/bin/env python3
"""
Analyze k6 script for validity against robot-shop application
"""

print("="*80)
print("K6 SCRIPT ANALYSIS FOR ROBOT-SHOP")
print("="*80)

# Extract endpoints from k6 script
k6_endpoints = {
    'baselineTraffic': '/products',
    'latencySpike': '/products?delay=true',
    'dbExhaustion': '/search?q=laptop&deep=true',
    'cpuSaturation': '/products?filters=brand,price,color,size,rating',
    'cacheMissStorm': '/products?id=<random>',
    'checkoutFlow': '/checkout (POST)',
    'timeoutScenario': '/inventory?slow=true',
    'errorSpike': '/unstable-endpoint',
}

print("\n1. ENDPOINTS CALLED BY K6 SCRIPT")
print("-" * 80)
for scenario, endpoint in k6_endpoints.items():
    print(f"   {scenario:25s} -> {endpoint}")

print("\n2. ACTUAL ROBOT-SHOP ENDPOINTS (from web nginx config)")
print("-" * 80)
actual_endpoints = [
    '/api/catalogue/*',
    '/api/user/*',
    '/api/cart/*',
    '/api/shipping/*',
    '/api/payment/*',
    '/api/ratings/*',
]
for ep in actual_endpoints:
    print(f"   {ep}")

print("\n3. ISSUES IDENTIFIED")
print("-" * 80)

issues = [
    {
        'severity': 'CRITICAL',
        'issue': 'Wrong base path',
        'detail': 'k6 calls /products but nginx expects /api/catalogue/...',
        'impact': 'ALL requests will hit nginx static files, not services!',
    },
    {
        'severity': 'CRITICAL',
        'issue': 'Non-existent endpoints',
        'detail': '/search, /checkout, /inventory, /unstable-endpoint do not exist',
        'impact': 'These scenarios will all return 404 or static HTML',
    },
    {
        'severity': 'CRITICAL',
        'issue': 'Missing /api/ prefix',
        'detail': 'All service endpoints require /api/<service>/ prefix',
        'impact': 'No service-to-service traces will be generated',
    },
    {
        'severity': 'HIGH',
        'issue': 'Query parameters not implemented',
        'detail': '?delay=true, ?deep=true, ?slow=true are not handled by services',
        'impact': 'Anomaly scenarios will behave same as normal traffic',
    },
    {
        'severity': 'MEDIUM',
        'issue': 'Headers sent correctly',
        'detail': 'x-anomaly-* headers ARE being sent properly',
        'impact': 'Header propagation is correct in k6 script',
    },
]

for idx, issue in enumerate(issues, 1):
    print(f"\n   [{issue['severity']}] Issue #{idx}: {issue['issue']}")
    print(f"   Detail: {issue['detail']}")
    print(f"   Impact: {issue['impact']}")

print("\n4. EXPECTED VS ACTUAL BEHAVIOR")
print("-" * 80)
print("\n   What k6 thinks will happen:")
print("   - Calls /products → catalogue service gets request")
print("   - Calls /search → search service processes query")
print("   - Calls /checkout → payment flow executes")
print()
print("   What ACTUALLY happens:")
print("   - Calls /products → nginx serves static HTML from /usr/share/nginx/html/")
print("   - Calls /search → nginx 404 (no such static file)")
print("   - Calls /checkout → nginx 404 (no such static file)")
print()
print("   Result: NO microservice traces, only nginx access logs!")

print("\n5. CORRECT ENDPOINTS FOR ROBOT-SHOP")
print("-" * 80)
print("""
   Based on actual robot-shop application structure:

   Catalogue service:
   - GET /api/catalogue/products
   - GET /api/catalogue/product/<id>
   - GET /api/catalogue/categories

   User service:
   - GET /api/user/<id>
   - POST /api/user/login
   - POST /api/user/register

   Cart service:
   - GET /api/cart/<user_id>
   - POST /api/cart/<user_id>
   - DELETE /api/cart/<user_id>

   Shipping service:
   - POST /api/shipping/calc (calculates shipping cost)

   Payment service:
   - POST /api/payment/pay

   Full checkout flow (creates MSA trace):
   1. GET /api/catalogue/products
   2. POST /api/user/login
   3. POST /api/cart/<user_id>
   4. POST /api/shipping/calc
   5. POST /api/payment/pay
""")

print("\n6. WHY NO ANOMALOUS LABELS IN DATASET")
print("-" * 80)
print("""
   Headers ARE sent by k6: ✅
   Headers ARE configured in nginx: ✅
   Headers ARE captured in Node.js services: ✅

   BUT:

   ❌ k6 is calling wrong endpoints (no /api/ prefix)
   ❌ Requests hit nginx static file handler, not services
   ❌ Services never receive the requests
   ❌ No service spans created → no anomaly headers in traces

   The few traces that DO exist are likely:
   - Health check probes from Kubernetes
   - Direct service-to-service calls (shipping→cart, etc.)
   - These internal calls don't have anomaly headers
""")

print("\n7. RECOMMENDATION")
print("-" * 80)
print("""
   The k6 script needs a COMPLETE rewrite to:

   1. Use correct /api/<service>/ prefix for all endpoints
   2. Call actual endpoints that exist in robot-shop services
   3. Remove query parameters that services don't implement
   4. Simulate real user flows that create MSA traces:
      - Browse products → Add to cart → Login → Checkout

   For anomaly injection, need to either:
   - Modify services to support ?delay=true style parameters, OR
   - Inject anomalies at infrastructure level (CPU limits, delays), OR
   - Just send headers and let normal load patterns create variation
""")

print("\n" + "="*80)
print("CONCLUSION: k6 script is NOT valid for robot-shop experiment")
print("="*80)
