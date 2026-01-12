/**
 * Robot Shop - Corrected k6 Load Test Script with Anomaly Labels
 *
 * Usage Examples:
 *
 * 1. Quick test (30s per scenario, ~4 minutes total):
 *    k6 run --env DURATION=30s --env RAMP_DURATION=15s k6_robot_shop_corrected.js
 *
 * 2. Default test (2m per scenario, ~15 minutes total):
 *    k6 run k6_robot_shop_corrected.js
 *
 * 3. Long test (5m per scenario, ~40 minutes total):
 *    k6 run --env DURATION=5m --env RAMP_DURATION=2m k6_robot_shop_corrected.js
 *
 * 4. Custom baseline + scenarios:
 *    k6 run --env BASELINE_DURATION=1m --env DURATION=45s k6_robot_shop_corrected.js
 *
 * 5. With custom base URL:
 *    k6 run --env BASE_URL=http://192.168.1.100:8080 --env DURATION=1m k6_robot_shop_corrected.js
 *
 * Environment Variables:
 *   DURATION          - Duration for each anomaly scenario (default: 2m)
 *   RAMP_DURATION     - Ramp up/down duration for ramping scenarios (default: 1m)
 *   BASELINE_DURATION - Duration for baseline normal traffic (default: same as DURATION)
 *   BASE_URL          - Robot shop base URL (default: http://localhost:8080)
 */

import http from 'k6/http';
import { check, sleep } from 'k6';

/* =========================
   Configurable Durations
========================= */

// Environment variables for duration control
const DURATION = __ENV.DURATION || '2m';           // Duration for each scenario
const RAMP_DURATION = __ENV.RAMP_DURATION || '1m'; // Ramp up/down duration
const BASELINE_DURATION = __ENV.BASELINE_DURATION || DURATION;

// Calculate start times dynamically based on durations
function parseDuration(duration) {
  const match = duration.match(/^(\d+)([smh])$/);
  if (!match) return 120; // Default 2 minutes in seconds
  const value = parseInt(match[1]);
  const unit = match[2];
  if (unit === 's') return value;
  if (unit === 'm') return value * 60;
  if (unit === 'h') return value * 3600;
  return 120;
}

const durationSec = parseDuration(DURATION);
const rampDurationSec = parseDuration(RAMP_DURATION);
const baselineDurationSec = parseDuration(BASELINE_DURATION);

// Calculate start times (cumulative)
const startTimes = {
  baseline: 0,
  latencySpike: baselineDurationSec,
  dbExhaustion: baselineDurationSec + (durationSec * 2),
  cpuSaturation: baselineDurationSec + (durationSec * 4),
  cacheMissStorm: baselineDurationSec + (durationSec * 6),
  dependencyBottleneck: baselineDurationSec + (durationSec * 8),
  timeoutScenario: baselineDurationSec + (durationSec * 10),
  errorSpike: baselineDurationSec + (durationSec * 12),
};

/* =========================
   Canonical Anomaly Registry
========================= */

const ANOMALY = {
  normal: {
    type: 'none',
    root_cause: 'none',
    label: 'normal',
    msg: 'baseline healthy traffic',
  },

  latency_spike: {
    type: 'latency_spike',
    root_cause: 'slow_database_query',
    label: 'anomalous',
    msg: 'high latency caused by slow DB queries',
  },

  db_exhaustion: {
    type: 'db_exhaustion',
    root_cause: 'connection_pool_exhaustion',
    label: 'anomalous',
    msg: 'DB connection pool exhausted under load',
  },

  cpu_saturation: {
    type: 'cpu_saturation',
    root_cause: 'high_cpu_usage',
    label: 'anomalous',
    msg: 'CPU saturated due to expensive request processing',
  },

  cache_miss: {
    type: 'cache_miss',
    root_cause: 'cache_key_explosion',
    label: 'anomalous',
    msg: 'cache miss storm due to unique request keys',
  },

  dependency_bottleneck: {
    type: 'dependency_bottleneck',
    root_cause: 'external_payment_latency',
    label: 'anomalous',
    msg: 'checkout slowed by external payment service',
  },

  timeout: {
    type: 'timeout',
    root_cause: 'downstream_service_timeout',
    label: 'anomalous',
    msg: 'service response timed out',
  },

  error_spike: {
    type: 'error_spike',
    root_cause: 'service_unavailable',
    label: 'anomalous',
    msg: 'high volume of 5xx errors',
  },
};

/* =========================
   k6 Scenarios (Sequential)
========================= */

export const options = {
  scenarios: {
    // Normal baseline traffic
    baseline: {
      executor: 'constant-vus',
      vus: 10,
      duration: BASELINE_DURATION,
      exec: 'baselineTraffic',
    },

    // Latency spike: heavy product browsing
    latencySpike: {
      executor: 'ramping-vus',
      startVUs: 10,
      stages: [
        { duration: RAMP_DURATION, target: 40 },
        { duration: RAMP_DURATION, target: 40 },
      ],
      startTime: `${startTimes.latencySpike}s`,
      exec: 'latencySpike',
    },

    // DB exhaustion: high rate of search queries
    dbExhaustion: {
      executor: 'constant-arrival-rate',
      rate: 100,
      timeUnit: '1s',
      duration: DURATION,
      preAllocatedVUs: 30,
      startTime: `${startTimes.dbExhaustion}s`,
      exec: 'dbExhaustion',
    },

    // CPU saturation: complex product filtering
    cpuSaturation: {
      executor: 'ramping-vus',
      startVUs: 20,
      stages: [
        { duration: RAMP_DURATION, target: 60 },
        { duration: RAMP_DURATION, target: 60 },
      ],
      startTime: `${startTimes.cpuSaturation}s`,
      exec: 'cpuSaturation',
    },

    // Cache miss storm: random product requests
    cacheMissStorm: {
      executor: 'constant-vus',
      vus: 40,
      duration: DURATION,
      startTime: `${startTimes.cacheMissStorm}s`,
      exec: 'cacheMissStorm',
    },

    // Dependency bottleneck: full checkout flow
    dependencyBottleneck: {
      executor: 'ramping-arrival-rate',
      startRate: 10,
      timeUnit: '1s',
      stages: [
        { duration: RAMP_DURATION, target: 40 },
        { duration: RAMP_DURATION, target: 40 },
      ],
      preAllocatedVUs: 30,
      startTime: `${startTimes.dependencyBottleneck}s`,
      exec: 'checkoutFlow',
    },

    // Timeout scenario: user operations with delays
    timeoutScenario: {
      executor: 'constant-vus',
      vus: 30,
      duration: DURATION,
      startTime: `${startTimes.timeoutScenario}s`,
      exec: 'timeoutScenario',
    },

    // Error spike: invalid operations
    errorSpike: {
      executor: 'ramping-vus',
      startVUs: 10,
      stages: [{ duration: RAMP_DURATION, target: 50 }],
      startTime: `${startTimes.errorSpike}s`,
      exec: 'errorSpike',
    },
  },
};

/* =========================
   Helper: OTEL-aware Request
========================= */

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

function otelRequest(method, url, ctx, body = null) {
  const params = {
    headers: {
      'Content-Type': 'application/json',
      // OTEL anomaly label propagation
      'x-anomaly-type': ctx.type,
      'x-anomaly-root-cause': ctx.root_cause,
      'x-anomaly-label': ctx.label,
      'x-anomaly-msg': ctx.msg,
    },
  };

  if (method === 'GET') return http.get(url, params);
  if (method === 'POST') return http.post(url, body, params);
  if (method === 'DELETE') return http.del(url, null, params);
}

/* =========================
   Helper Functions
========================= */

// Generate random user ID (numeric for shipping service compatibility)
function randomUserId() {
  return Math.floor(Math.random() * 10000) + 1;
}

// Generate random SKU from actual product list in database
function randomSku() {
  const skus = [
    'Watson', 'Ewooid', 'HPTD', 'UHJ', 'EPE', 'EMM',
    'SHCE', 'RED', 'RMC', 'STAN-1', 'CNA',
  ];
  return skus[Math.floor(Math.random() * skus.length)];
}

/* =========================
   Scenario Functions
========================= */

// Baseline: Simple product browsing
export function baselineTraffic() {
  const res = otelRequest('GET', `${BASE_URL}/api/catalogue/products`, ANOMALY.normal);
  check(res, { 'baseline OK': r => r.status === 200 });
  sleep(1);
}

// Latency spike: Browse products and categories extensively
export function latencySpike() {
  // Get all products
  let res = otelRequest('GET', `${BASE_URL}/api/catalogue/products`, ANOMALY.latency_spike);
  check(res, { 'products loaded': r => r.status === 200 });

  sleep(0.5);

  // Get categories
  res = otelRequest('GET', `${BASE_URL}/api/catalogue/categories`, ANOMALY.latency_spike);
  check(res, { 'categories loaded': r => r.status === 200 });

  sleep(0.5);

  // Get specific product
  const sku = randomSku();
  res = otelRequest('GET', `${BASE_URL}/api/catalogue/product/${sku}`, ANOMALY.latency_spike);
  check(res, { 'product detail loaded': r => r.status === 200 || r.status === 404 });

  sleep(1);
}

// DB exhaustion: Heavy search load
export function dbExhaustion() {
  const searchTerms = ['robot', 'arduino', 'sensor', 'kit', 'motor', 'led'];
  const term = searchTerms[Math.floor(Math.random() * searchTerms.length)];

  const res = otelRequest(
    'GET',
    `${BASE_URL}/api/catalogue/search/${term}`,
    ANOMALY.db_exhaustion
  );

  check(res, { 'search completed': r => r.status === 200 });
  sleep(0.2);
}

// CPU saturation: Browse products by category
export function cpuSaturation() {
  const categories = ['robot', 'drone', 'toy', 'electronics'];
  const cat = categories[Math.floor(Math.random() * categories.length)];

  const res = otelRequest(
    'GET',
    `${BASE_URL}/api/catalogue/products/${cat}`,
    ANOMALY.cpu_saturation
  );

  check(res, { 'category browse OK': r => r.status === 200 || r.status === 404 });
  sleep(0.5);
}

// Cache miss storm: Random unique product requests
export function cacheMissStorm() {
  const sku = randomSku();

  const res = otelRequest(
    'GET',
    `${BASE_URL}/api/catalogue/product/${sku}`,
    ANOMALY.cache_miss
  );

  check(res, { 'product request OK': r => r.status === 200 || r.status === 404 });
  sleep(0.3);
}

// Full checkout flow: Creates complete MSA trace
export function checkoutFlow() {
  const userId = randomUserId();
  const sku = randomSku();

  // 1. Browse products (catalogue service)
  let res = otelRequest(
    'GET',
    `${BASE_URL}/api/catalogue/products`,
    ANOMALY.dependency_bottleneck
  );
  check(res, { '1. catalogue OK': r => r.status === 200 });
  sleep(0.3);

  // 2. Register/login user (user service)
  const userPayload = JSON.stringify({
    username: userId,
    password: 'password',
    email: `${userId}@example.com`,
  });

  res = otelRequest(
    'POST',
    `${BASE_URL}/api/user/register`,
    ANOMALY.dependency_bottleneck,
    userPayload
  );
  check(res, { '2. user register attempted': r => r.status < 500 });
  sleep(0.3);

  // 3. Add item to cart (cart service)
  res = otelRequest(
    'GET',
    `${BASE_URL}/api/cart/add/${userId}/${sku}/1`,
    ANOMALY.dependency_bottleneck
  );
  check(res, { '3. cart add OK': r => r.status === 200 || r.status === 201 });
  sleep(0.3);

  // 4. Calculate shipping (shipping service → cart service)
  res = otelRequest(
    'GET',
    `${BASE_URL}/api/shipping/calc/${userId}`,
    ANOMALY.dependency_bottleneck
  );
  check(res, { '4. shipping calc OK': r => r.status === 200 });
  sleep(0.3);

  // 5. Get cart data (to pass to payment)
  res = otelRequest(
    'GET',
    `${BASE_URL}/api/cart/cart/${userId}`,
    ANOMALY.dependency_bottleneck
  );
  check(res, { '5. cart fetch OK': r => r.status === 200 });

  let cartData = null;
  if (res.status === 200) {
    try {
      cartData = JSON.parse(res.body);
    } catch (e) {
      cartData = res.json();
    }
  }
  sleep(0.3);

  // 6. Process payment (payment service → user + cart)
  if (cartData) {
    res = otelRequest(
      'POST',
      `${BASE_URL}/api/payment/pay/${userId}`,
      ANOMALY.dependency_bottleneck,
      JSON.stringify(cartData)
    );
    check(res, { '6. payment attempted': r => r.status < 500 });
  }

  sleep(1);
}

// Timeout scenario: User operations
export function timeoutScenario() {
  const userId = randomUserId();

  // Check user existence (might timeout on slow DB)
  let res = otelRequest(
    'GET',
    `${BASE_URL}/api/user/check/${userId}`,
    ANOMALY.timeout
  );
  check(res, { 'user check completed': r => r.status < 500 });

  sleep(0.5);

  // Get cart (might timeout if cart service is slow)
  res = otelRequest(
    'GET',
    `${BASE_URL}/api/cart/cart/${userId}`,
    ANOMALY.timeout
  );
  check(res, { 'cart fetch completed': r => r.status < 500 });

  sleep(1);
}

// Error spike: Invalid operations that may cause errors
export function errorSpike() {
  const userId = randomUserId();

  // Try to get non-existent product
  let res = otelRequest(
    'GET',
    `${BASE_URL}/api/catalogue/product/INVALID-SKU-${Math.random()}`,
    ANOMALY.error_spike
  );
  check(res, { 'error expected': r => r.status === 404 || r.status === 500 });

  sleep(0.3);

  // Try to pay with invalid user
  res = otelRequest(
    'POST',
    `${BASE_URL}/api/payment/pay/invalid-user-${Math.random()}`,
    ANOMALY.error_spike,
    JSON.stringify({ amount: -1 })  // Invalid amount
  );
  check(res, { 'payment error expected': r => r.status >= 400 });

  sleep(0.5);

  // Try to delete non-existent cart
  res = otelRequest(
    'DELETE',
    `${BASE_URL}/api/cart/cart/nonexistent-${Math.random()}`,
    ANOMALY.error_spike
  );
  check(res, { 'delete attempted': r => true });  // Any response is OK

  sleep(1);
}
