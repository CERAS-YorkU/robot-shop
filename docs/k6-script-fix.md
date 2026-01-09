# K6 Script Fix - Corrected for Robot-Shop

**Date**: 2026-01-09
**Issue**: Original k6 script calls non-existent endpoints, preventing MSA traces

---

## Problem Summary

The original `k6_optel_anomaly_labeled.js` script was calling endpoints that don't exist in robot-shop, resulting in:

- **0 anomalous traces** (100% normal)
- **6,288 single-span traces** (no MSA chains)
- **Nginx serving static files** instead of proxying to services

### Original vs Corrected Endpoints

| Scenario | Original (WRONG) | Corrected |
|----------|------------------|-----------|
| Browse products | `/products` | `/api/catalogue/products` |
| Search | `/search?q=laptop` | `/api/catalogue/search/laptop` |
| Checkout | `/checkout` (POST) | Full flow: catalogue → user → cart → shipping → payment |
| Inventory | `/inventory?slow=true` | `/api/user/check/<id>` + `/api/cart/cart/<id>` |
| Error spike | `/unstable-endpoint` | `/api/catalogue/product/INVALID-SKU` |

---

## Key Fixes

### 1. Correct API Prefix

**Before:**
```javascript
http.get(`${BASE_URL}/products`)  // ❌ Hits nginx static files
```

**After:**
```javascript
http.get(`${BASE_URL}/api/catalogue/products`)  // ✅ Routes to catalogue service
```

### 2. Real Endpoints

All endpoints now match actual robot-shop services:

**Catalogue Service** (`/api/catalogue/*`):
- `GET /api/catalogue/products` - List all products
- `GET /api/catalogue/product/<sku>` - Get specific product
- `GET /api/catalogue/products/<category>` - Filter by category
- `GET /api/catalogue/categories` - List categories
- `GET /api/catalogue/search/<text>` - Search products

**User Service** (`/api/user/*`):
- `POST /api/user/register` - Register new user
- `POST /api/user/login` - User login
- `GET /api/user/check/<id>` - Check user existence
- `GET /api/user/history/<id>` - Order history

**Cart Service** (`/api/cart/*`):
- `GET /api/cart/cart/<id>` - Get user cart
- `GET /api/cart/add/<id>/<sku>/<qty>` - Add item to cart
- `DELETE /api/cart/cart/<id>` - Delete cart
- `POST /api/cart/shipping/<id>` - Add shipping info

**Shipping Service** (`/api/shipping/*`):
- `GET /api/shipping/calc/<id>` - Calculate shipping cost
- `POST /api/shipping/confirm/<id>` - Confirm shipment

**Payment Service** (`/api/payment/*`):
- `POST /api/payment/pay/<id>` - Process payment

### 3. Complete MSA Trace Flows

**Checkout Flow** (creates multi-service trace):
```javascript
export function checkoutFlow() {
  const userId = randomUserId();
  const sku = randomSku();

  // 1. Browse catalogue (catalogue service)
  GET /api/catalogue/products

  // 2. Register user (user service → MongoDB)
  POST /api/user/register

  // 3. Add to cart (cart service → catalogue → Redis)
  GET /api/cart/add/${userId}/${sku}/1

  // 4. Calculate shipping (shipping → cart → MySQL)
  GET /api/shipping/calc/${userId}

  // 5. Process payment (payment → user + cart → RabbitMQ)
  POST /api/payment/pay/${userId}
}
```

This creates a **distributed trace across 5+ services** with proper parent-child relationships!

### 4. Realistic Data

**Before:**
```javascript
// Hardcoded fake data
productId: Math.floor(Math.random() * 1000)
```

**After:**
```javascript
// Real robot-shop SKUs
const skus = ['ARCL-001', 'STNS-001', 'HEX-001', ...];
function randomSku() {
  return skus[Math.floor(Math.random() * skus.length)];
}
```

---

## Usage

### Run Corrected Script

```bash
# With port-forward to web service
kubectl port-forward -n robot-shop2 svc/web 8080:8080 &

# Run k6 (15 minutes total)
k6 run k6-scripts/k6_robot_shop_corrected.js

# Or specify custom base URL
k6 run --env BASE_URL=http://localhost:8080 k6-scripts/k6_robot_shop_corrected.js
```

### Timeline

```
0:00 - 2:00   Baseline (10 VUs, normal traffic)
2:00 - 4:00   Latency Spike (10→40 VUs, heavy browsing)
4:00 - 6:00   DB Exhaustion (100 req/s, search queries)
6:00 - 8:00   CPU Saturation (20→60 VUs, category filters)
8:00 - 10:00  Cache Miss Storm (40 VUs, random products)
10:00 - 12:00 Dependency Bottleneck (10→40 req/s, full checkout)
12:00 - 14:00 Timeout Scenario (30 VUs, user/cart operations)
14:00 - 15:00 Error Spike (10→50 VUs, invalid operations)
```

---

## Expected Results

### Before Fix

```
Dataset Analysis:
  Total spans: 6,441
  Unique traces: 6,288
  Avg spans/trace: 1.02  ← PROBLEM: Almost all single-span

  Anomaly labels:
    normal: 6,441 (100%)  ← PROBLEM: No anomalous traces
```

### After Fix

```
Dataset Analysis:
  Total spans: ~15,000-20,000
  Unique traces: ~3,000-5,000
  Avg spans/trace: 3-5  ← GOOD: MSA chains

  Anomaly labels:
    normal: ~10,000 (60%)
    anomalous: ~6,000 (40%)  ← GOOD: Mixed labels

  Service distribution:
    catalogue: ~4,000 spans
    user: ~3,500 spans
    cart: ~3,000 spans
    shipping: ~2,500 spans
    payment: ~2,000 spans

  Parent-child relationships:
    Root spans: ~3,500
    Child spans: ~12,000  ← GOOD: Proper MSA traces
```

### Per-Anomaly-Type Files

After extraction, you should see:

```
dataset/
├── traces_labeled_*.csv              # Full dataset (~15K spans)
├── traces_normal_*.csv               # Normal only (~10K)
├── traces_anomalous_*.csv            # Anomalous only (~6K)
├── traces_latency_spike_*.csv        # ~1,200 spans
├── traces_db_exhaustion_*.csv        # ~1,500 spans
├── traces_cpu_saturation_*.csv       # ~1,000 spans
├── traces_cache_miss_*.csv           # ~800 spans
├── traces_dependency_bottleneck_*.csv # ~1,000 spans
├── traces_timeout_*.csv              # ~600 spans
└── traces_error_spike_*.csv          # ~500 spans
```

---

## Verification Steps

### 1. Test Single Request

```bash
# Before running full k6, test one request
kubectl port-forward -n robot-shop2 svc/web 8080:8080 &

curl -H "x-anomaly-type: test" \
     -H "x-anomaly-label: anomalous" \
     http://localhost:8080/api/catalogue/products

# Should return JSON array of products
```

### 2. Run Short Test

Modify script for quick validation:

```javascript
export const options = {
  scenarios: {
    quickTest: {
      executor: 'constant-vus',
      vus: 5,
      duration: '30s',
      exec: 'checkoutFlow',  // Test full MSA flow
    },
  },
};
```

### 3. Check Traces Immediately

```bash
# After 30s test, wait for export
sleep 30

# Copy traces
OTEL_POD=$(kubectl get pods -n robot-shop2 -l app=opentelemetry-collector -o jsonpath='{.items[0].metadata.name}')
kubectl cp robot-shop2/$OTEL_POD:/var/log/otel/traces.json ./data/traces_test.json

# Extract
python3 python-scripts/extract-labeled-dataset.py \
  --traces ./data/traces_test.json \
  --output ./data/dataset_test

# Analyze
python3 tmp_analyze_traces.py dataset_test/traces_labeled_*.csv
```

**Expected output:**
```
Unique traces: ~30-50
Avg spans/trace: 4-6  ← Should see MSA chains!
Anomaly labels:
  anomalous: 30-50 (100%)  ← All checkout flows labeled!
```

---

## Differences from Original

| Aspect | Original | Corrected |
|--------|----------|-----------|
| **Base path** | `/` | `/api/<service>/` |
| **Endpoints** | Non-existent | Real robot-shop APIs |
| **Flows** | Single requests | Multi-service traces |
| **Data** | Random numbers | Real SKUs, user IDs |
| **Load** | Unrealistic (200 req/s) | Realistic (100 req/s max) |
| **Duration** | 15 minutes | 15 minutes (same) |
| **Headers** | ✅ Correct | ✅ Correct (unchanged) |
| **Result** | 0 anomalous traces | ~40% anomalous traces |

---

## Implementation Status

- ✅ Script created: `k6-scripts/k6_robot_shop_corrected.js`
- ✅ All endpoints verified against source code
- ✅ MSA trace flows designed
- ✅ Anomaly labels preserved from original
- ⚠️ **Needs testing** - Run short validation test first

---

## Next Steps

1. **Test the corrected script**:
   ```bash
   kubectl port-forward -n robot-shop2 svc/web 8080:8080 &
   k6 run k6-scripts/k6_robot_shop_corrected.js
   ```

2. **Wait for traces to export** (check OTel collector logs)

3. **Extract dataset**:
   ```bash
   OTEL_POD=$(kubectl get pods -n robot-shop2 -l app=opentelemetry-collector -o jsonpath='{.items[0].metadata.name}')
   kubectl cp robot-shop2/$OTEL_POD:/var/log/otel/traces.json ./data/traces.json

   python3 python-scripts/extract-labeled-dataset.py \
     --traces ./data/traces.json \
     --output ./dataset
   ```

4. **Verify results**:
   ```bash
   python3 tmp_analyze_traces.py dataset/traces_labeled_*.csv
   ```

5. **Check for anomalous labels**:
   ```bash
   cat dataset/traces_labeled_*.csv | cut -d',' -f17 | sort | uniq -c
   ```

---

**Status**: Ready for testing
**Expected outcome**: Proper MSA traces with anomaly labels
