/**
 * Robot Shop - Deep Trace Scenarios for Graph-Based Anomaly Detection
 *
 * Research Goal: Generate distributed traces with 4-7 service hops for GAN/GNN training
 *
 * Key Features:
 * - Complex user journeys with 5-7 service call chains
 * - 60% simple / 30% complex / 10% edge case workload mix
 * - Configurable anomaly injection rate (default 10%) with labeled traces
 * - Optimized for graph structure diversity (depth, breadth, cycles)
 *
 * Usage Examples:
 *
 * 1. Quick test (30s per scenario):
 *    k6 run --env DURATION=30s --env RAMP_DURATION=15s deep-trace-scenarios.js
 *
 * 2. Default test (2m per scenario):
 *    k6 run deep-trace-scenarios.js
 *
 * 3. Long test (5m per scenario):
 *    k6 run --env DURATION=5m --env RAMP_DURATION=2m deep-trace-scenarios.js
 *
 * 4. Custom baseline + scenarios:
 *    k6 run --env BASELINE_DURATION=1m --env DURATION=45s deep-trace-scenarios.js
 *
 * 5. With custom base URL:
 *    k6 run --env BASE_URL=http://10.0.0.2:8080 --env DURATION=2m deep-trace-scenarios.js
 *
 * Environment Variables:
 *   DURATION          - Duration for each scenario (default: 2m)
 *   RAMP_DURATION     - Ramp up/down duration for ramping scenarios (default: 1m)
 *   BASELINE_DURATION - Duration for baseline normal traffic (default: same as DURATION)
 *   ANOMALY_RATE      - Probability of injecting an anomaly (default: 0.1)
 *   BASE_URL          - Robot shop base URL (default: http://localhost:8080)
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

/* =========================
   Configurable Durations
========================= */

// Environment variables for duration control
const DURATION = __ENV.DURATION || '2m';           // Duration for each scenario
const RAMP_DURATION = __ENV.RAMP_DURATION || '1m'; // Ramp up/down duration
const BASELINE_DURATION = __ENV.BASELINE_DURATION || DURATION;
const ANOMALY_RATE = parseFloat(__ENV.ANOMALY_RATE || '0.1'); // Anomaly injection rate

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

// Calculate start times (cumulative) for sequential execution
const startTimes = {
  baseline: 0,
  simpleBrowsing: baselineDurationSec,
  complexCheckout: baselineDurationSec + (durationSec * 2),
  productDiscovery: baselineDurationSec + (durationSec * 4),
  edgeCases: baselineDurationSec + (durationSec * 6),
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

/* =========================
   Workload Distribution & Sequential Scenarios
   Research-backed: 60% simple, 30% complex, 10% edge cases
========================= */

export const options = {
  scenarios: {
    // Baseline: Normal traffic (optional, can be disabled)
    baseline: {
      executor: 'constant-vus',
      vus: 10,
      duration: BASELINE_DURATION,
      startTime: `${startTimes.baseline}s`,
      exec: 'baselineTraffic',
    },

    // 60% - Simple flows (2-3 hops): Browse, view product, check cart
    simple_browsing: {
      executor: 'constant-vus',
      vus: 12,
      duration: DURATION,
      startTime: `${startTimes.simpleBrowsing}s`,
      exec: 'simpleBrowsing',
    },

    // 30% - Complex flows (4-7 hops): Full checkout with deep call chains
    complex_checkout: {
      executor: 'ramping-vus',
      startVUs: 5,
      stages: [
        { duration: RAMP_DURATION, target: 10 },
        { duration: RAMP_DURATION, target: 10 },
      ],
      startTime: `${startTimes.complexCheckout}s`,
      exec: 'complexCheckout',
    },

    // 30% - Product discovery + purchase (6 hops)
    product_discovery: {
      executor: 'ramping-vus',
      startVUs: 3,
      stages: [
        { duration: RAMP_DURATION, target: 6 },
        { duration: RAMP_DURATION, target: 6 },
      ],
      startTime: `${startTimes.productDiscovery}s`,
      exec: 'productDiscoveryPurchase',
    },

    // 10% - Edge cases (5-7 hops with retries/errors)
    edge_cases: {
      executor: 'constant-vus',
      vus: 2,
      duration: DURATION,
      startTime: `${startTimes.edgeCases}s`,
      exec: 'edgeCaseFlows',
    },
  },

  thresholds: {
    http_req_duration: ['p(95)<5000'], // 95% of requests under 5s
    http_req_failed: ['rate<0.3'],     // Allow up to 30% failures (anomalies expected)
  },
};

/* =========================
   Anomaly Types
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
    msg: 'database query latency spike',
  },

  cascading_failure: {
    type: 'cascading_failure',
    root_cause: 'service_dependency_timeout',
    label: 'anomalous',
    msg: 'cascading timeout across services',
  },

  resource_exhaustion: {
    type: 'resource_exhaustion',
    root_cause: 'memory_pressure',
    label: 'anomalous',
    msg: 'high memory utilization causing slowdown',
  },

  error_propagation: {
    type: 'error_propagation',
    root_cause: 'upstream_service_error',
    label: 'anomalous',
    msg: 'error propagating through call chain',
  },

  data_corruption: {
    type: 'data_corruption',
    root_cause: 'invalid_payload',
    label: 'anomalous',
    msg: 'malformed data causing processing errors',
  },
};

/* =========================
   Helper Functions
========================= */

function otelRequest(method, url, anomalyCtx, body = null) {
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'x-anomaly-type': anomalyCtx.type,
      'x-anomaly-root-cause': anomalyCtx.root_cause,
      'x-anomaly-label': anomalyCtx.label,
      'x-anomaly-msg': anomalyCtx.msg,
    },
    timeout: '10s', // Allow time for complex flows
  };

  if (method === 'GET') return http.get(url, params);
  if (method === 'POST') return http.post(url, body, params);
  if (method === 'DELETE') return http.del(url, null, params);
}

function randomUserId() {
  return Math.floor(Math.random() * 10000) + 1;
}

function randomSku() {
  const skus = [
    'STAN-1', 'Watson', 'Ewooid', 'HPTD', 'UHJ', 'EPE',
    'EMM', 'SHCE', 'RED', 'RMC', 'CNA',
  ];
  return skus[Math.floor(Math.random() * skus.length)];
}

// Variable anomaly injection rate (default 10%)
function getAnomalyContext() {
  if (Math.random() < ANOMALY_RATE) {
    const anomalies = [
      ANOMALY.latency_spike,
      ANOMALY.cascading_failure,
      ANOMALY.resource_exhaustion,
      ANOMALY.error_propagation,
    ];
    return anomalies[Math.floor(Math.random() * anomalies.length)];
  }
  return ANOMALY.normal;
}

/* =========================
   Scenario Functions
========================= */

// Baseline: Normal traffic without anomalies
export function baselineTraffic() {
  const res = otelRequest('GET', `${BASE_URL}/api/catalogue/products`, ANOMALY.normal);
  check(res, { 'baseline OK': r => r.status === 200 });
  sleep(1);
}

/* =========================
   Scenario 1: Simple Browsing (2-3 hops)
   60% of workload
========================= */

export function simpleBrowsing() {
  const ctx = getAnomalyContext();

  // Flow: Web → Catalogue (2 hops)
  let res = otelRequest('GET', `${BASE_URL}/api/catalogue/products`, ctx);
  check(res, { 'browse products OK': r => r.status === 200 });

  sleep(randomIntBetween(1, 3));

  // Flow: Web → Catalogue → MongoDB (3 hops with internal DB call)
  const sku = randomSku();
  res = otelRequest('GET', `${BASE_URL}/api/catalogue/product/${sku}`, ctx);
  check(res, { 'view product OK': r => r.status === 200 || r.status === 404 });

  sleep(randomIntBetween(2, 5));
}

/* =========================
   Scenario 2: Complex Checkout (7 hops)
   Research Priority: HIGHEST VALUE for graph diversity

   Flow: Web → Cart → Catalogue → Cart → Shipping → Payment → User
========================= */

export function complexCheckout() {
  const userId = randomUserId();
  const sku = randomSku();
  const ctx = getAnomalyContext();

  // If anomalous, add latency to simulate anomaly
  if (ctx.label === 'anomalous' && ctx.type === 'latency_spike') {
    sleep(randomIntBetween(1, 3));
  }

  // Step 1: Web → Catalogue (browse products)
  let res = otelRequest('GET', `${BASE_URL}/api/catalogue/products`, ctx);
  check(res, { 'checkout step 1: browse OK': r => r.status === 200 });
  sleep(0.5);

  // Step 2: Web → Cart → Catalogue (add to cart, cart calls catalogue for product info)
  res = otelRequest('GET', `${BASE_URL}/api/cart/add/${userId}/${sku}/1`, ctx);
  check(res, { 'checkout step 2: add to cart OK': r => r.status === 200 || r.status === 201 });
  sleep(0.5);

  // Step 3: Web → Shipping → Cart (calculate shipping, shipping calls cart)
  res = otelRequest('GET', `${BASE_URL}/api/shipping/calc/${userId}`, ctx);
  check(res, { 'checkout step 3: shipping calc OK': r => r.status === 200 });
  sleep(0.5);

  // Step 4: Web → Cart (fetch cart data for payment)
  res = otelRequest('GET', `${BASE_URL}/api/cart/cart/${userId}`, ctx);
  check(res, { 'checkout step 4: fetch cart OK': r => r.status === 200 });

  let cartData = null;
  if (res.status === 200) {
    try {
      cartData = res.json();
    } catch (e) {
      cartData = { items: [], total: 0 };
    }
  }
  sleep(0.5);

  // Step 5: Web → Payment → User + Cart (payment verifies user and cart)
  if (cartData) {
    res = otelRequest(
      'POST',
      `${BASE_URL}/api/payment/pay/${userId}`,
      ctx,
      JSON.stringify(cartData)
    );
    check(res, { 'checkout step 5: payment OK': r => r.status < 500 });
  }

  // Note: Dispatch (step 6) is async via RabbitMQ, happens in background

  sleep(randomIntBetween(2, 5));
}

/* =========================
   Scenario 3: Product Discovery + Purchase (6 hops)
   Research Goal: Star topology with Cart as hub node

   Flow: Web → Catalogue → Ratings → Cart → Catalogue → User
========================= */

export function productDiscoveryPurchase() {
  const userId = randomUserId();
  const sku = randomSku();
  const ctx = getAnomalyContext();

  // Step 1: Web → Catalogue (search/browse)
  let res = otelRequest('GET', `${BASE_URL}/api/catalogue/products`, ctx);
  check(res, { 'discovery step 1: search OK': r => r.status === 200 });
  sleep(0.3);

  // Step 2: Web → Catalogue (get product details)
  res = otelRequest('GET', `${BASE_URL}/api/catalogue/product/${sku}`, ctx);
  check(res, { 'discovery step 2: product details OK': r => r.status === 200 || r.status === 404 });
  sleep(0.3);

  // Step 3: Web → Ratings (fetch product ratings)
  res = otelRequest('GET', `${BASE_URL}/api/ratings/api/fetch/${sku}`, ctx);
  check(res, { 'discovery step 3: ratings OK': r => r.status < 500 });
  sleep(0.3);

  // Step 4: Web → User (check if logged in / get session)
  res = otelRequest('GET', `${BASE_URL}/api/user/check/${userId}`, ctx);
  check(res, { 'discovery step 4: user check OK': r => r.status < 500 });
  sleep(0.3);

  // Step 5: Web → Cart → Catalogue (add item, cart validates with catalogue)
  res = otelRequest('GET', `${BASE_URL}/api/cart/add/${userId}/${sku}/1`, ctx);
  check(res, { 'discovery step 5: add to cart OK': r => r.status === 200 || r.status === 201 });
  sleep(0.3);

  // Step 6: Web → Cart (view updated cart)
  res = otelRequest('GET', `${BASE_URL}/api/cart/cart/${userId}`, ctx);
  check(res, { 'discovery step 6: view cart OK': r => r.status === 200 });

  sleep(randomIntBetween(2, 4));
}

/* =========================
   Scenario 4: Edge Cases (5-7 hops with retries/errors)
   Research Goal: Cyclic patterns, error recovery paths

   Includes: Payment retry loops, concurrent cart updates, error propagation
========================= */

export function edgeCaseFlows() {
  const userId = randomUserId();
  const ctx = Math.random() < 0.5 ? ANOMALY.error_propagation : ANOMALY.cascading_failure;

  // Randomly choose edge case pattern
  const pattern = Math.floor(Math.random() * 3);

  if (pattern === 0) {
    // Pattern A: Payment Retry Loop (creates cycle in trace graph)
    paymentRetryLoop(userId, ctx);
  } else if (pattern === 1) {
    // Pattern B: Concurrent Cart Operations
    concurrentCartOps(userId, ctx);
  } else {
    // Pattern C: Error Propagation Chain
    errorPropagationChain(userId, ctx);
  }

  sleep(randomIntBetween(3, 6));
}

// Edge Case Pattern A: Payment fails, retry with different method
function paymentRetryLoop(userId, ctx) {
  const sku = randomSku();

  // Add item to cart
  let res = otelRequest('GET', `${BASE_URL}/api/cart/add/${userId}/${sku}/1`, ctx);
  sleep(0.3);

  // Fetch cart
  res = otelRequest('GET', `${BASE_URL}/api/cart/cart/${userId}`, ctx);
  let cartData = null;
  if (res.status === 200) {
    try {
      cartData = res.json();
    } catch (e) {
      cartData = { items: [], total: 0 };
    }
  }
  sleep(0.3);

  // Payment attempt 1 (simulate failure with invalid data)
  if (cartData) {
    res = otelRequest(
      'POST',
      `${BASE_URL}/api/payment/pay/${userId}`,
      ctx,
      JSON.stringify({ ...cartData, amount: -1 }) // Invalid amount
    );
    sleep(0.5);

    // Payment attempt 2 (retry with valid data)
    res = otelRequest(
      'POST',
      `${BASE_URL}/api/payment/pay/${userId}`,
      ctx,
      JSON.stringify(cartData)
    );
    check(res, { 'payment retry OK': r => r.status < 500 });
  }
}

// Edge Case Pattern B: Multiple cart operations in sequence
function concurrentCartOps(userId, ctx) {
  const skus = [randomSku(), randomSku(), randomSku()];

  // Add multiple items
  for (const sku of skus) {
    otelRequest('GET', `${BASE_URL}/api/cart/add/${userId}/${sku}/1`, ctx);
    sleep(0.2);
  }

  // Fetch cart multiple times (simulating concurrent reads)
  for (let i = 0; i < 2; i++) {
    otelRequest('GET', `${BASE_URL}/api/cart/cart/${userId}`, ctx);
    sleep(0.2);
  }

  // Delete cart
  otelRequest('DELETE', `${BASE_URL}/api/cart/cart/${userId}`, ctx);
}

// Edge Case Pattern C: Trigger errors that propagate
function errorPropagationChain(userId, ctx) {
  // Request invalid product (triggers 404 in catalogue)
  let res = otelRequest('GET', `${BASE_URL}/api/catalogue/product/INVALID-${Date.now()}`, ctx);
  sleep(0.3);

  // Try to add invalid product to cart (error propagates)
  res = otelRequest('GET', `${BASE_URL}/api/cart/add/${userId}/INVALID-${Date.now()}/1`, ctx);
  sleep(0.3);

  // Fetch cart (should work despite previous errors)
  res = otelRequest('GET', `${BASE_URL}/api/cart/cart/${userId}`, ctx);
  sleep(0.3);

  // Payment with invalid user (error in payment service)
  res = otelRequest(
    'POST',
    `${BASE_URL}/api/payment/pay/INVALID-${Date.now()}`,
    ctx,
    JSON.stringify({ amount: 100 })
  );
  check(res, { 'error propagation handled': r => r.status >= 400 });
}

/* =========================
   Default Function (fallback)
========================= */

export default function() {
  simpleBrowsing();
}
