# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Stan's Robot Shop is a polyglot microservices application designed as a sandbox for testing containerized application orchestration and monitoring. It consists of 8 application services written in different languages (Node.js, Java, Python, Go, PHP) plus infrastructure services (MongoDB, MySQL, Redis, RabbitMQ, Nginx).

**Important:** This is a demonstration application - error handling is minimal and security is not built in.

### Current Research Environment

**Active Namespace**: `robot-shop2` (for anomaly detection research)
- This is the primary namespace for ongoing research work
- All kubectl commands should target `robot-shop2` unless otherwise specified
- Enhanced OpenTelemetry configuration with anomaly labeling support
- See [docs/otel-collector-fixes.md](docs/otel-collector-fixes.md) for recent fixes

## Development Commands

### Local Development (Docker Compose)

```bash
# Build all services from source (requires INSTANA_AGENT_KEY for Nginx tracing)
export INSTANA_AGENT_KEY="<your-key>"
docker-compose build

# Pull pre-built images from Docker Hub
docker-compose pull

# Start all services
docker-compose up

# Start with load generation
docker-compose -f docker-compose.yaml -f docker-compose-load.yaml up

# Push images to custom registry (after modifying .env)
docker-compose push
```

### Kubernetes Deployment

```bash
# Helm v3 installation
kubectl create ns robot-shop
helm install robot-shop --namespace robot-shop K8s/helm/

# With custom parameters
helm install robot-shop \
  --set image.version=2.1.0 \
  --set nodeport=true \
  --namespace robot-shop K8s/helm/

# For minikube/minishift
helm install robot-shop --set nodeport=true --namespace robot-shop K8s/helm/

# For OpenShift
helm install robot-shop --set openshift=true --namespace robot-shop K8s/helm/

# Deploy load generator in K8s
kubectl -n robot-shop apply -f K8s/load-deployment.yaml

# Enable autoscaling
K8s/autoscale.sh
```

### Load Generation

```bash
# Build load generator
cd load-gen
./build.sh push

# Run load generator locally
./load-gen.sh

# Run via Docker with custom settings
docker run -d --rm --name="loadgen" --network=host \
  -e "HOST=http://localhost:8080/" \
  -e "NUM_CLIENTS=5" \
  -e "RUN_TIME=1h30m" \
  -e "ERROR=1" \
  -e "SILENT=1" \
  robotshop/rs-load
```

### Testing & Monitoring

```bash
# Access the application
open http://localhost:8080

# Check service health
curl http://localhost:8080/api/catalogue/health
curl http://localhost:8080/api/user/health
curl http://localhost:8080/api/cart/health

# View Prometheus metrics
curl http://localhost:8080/api/cart/metrics
curl http://localhost:8080/api/payment/metrics

# For Kubernetes
minikube ip  # Get cluster IP
kubectl get svc web  # Get NodePort
```

## Architecture Overview

### Service Map & Dependencies

```
                         ┌──────────────┐
                         │  Web (Nginx) │
                         │   Port 8080  │
                         └──────┬───────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
         ┌──────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐
         │  Catalogue  │ │   User    │ │    Cart     │
         │  (Node.js)  │ │ (Node.js) │ │  (Node.js)  │
         └──────┬──────┘ └─────┬─────┘ └──────┬──────┘
                │               │               │
         ┌──────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐
         │   MongoDB   │ │   Redis   │ │   Redis     │
         └─────────────┘ └───────────┘ └─────────────┘

         ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
         │  Shipping   │ │   Ratings   │ │   Payment   │
         │   (Java)    │ │    (PHP)    │ │  (Python)   │
         └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
                │               │               │
         ┌──────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐
         │    MySQL    │ │   MySQL   │ │  RabbitMQ   │
         └─────────────┘ └───────────┘ └──────┬──────┘
                                               │
                                        ┌──────▼──────┐
                                        │  Dispatch   │
                                        │    (Go)     │
                                        └─────────────┘
```

### Service Technologies

- **Web** - Nginx 1.21.6 (reverse proxy, static AngularJS frontend)
- **Catalogue** - Node.js/Express + MongoDB (product catalog)
- **User** - Node.js/Express + MongoDB + Redis (authentication, sessions)
- **Cart** - Node.js/Express + Redis (shopping cart storage)
- **Shipping** - Java/Spring Boot + MySQL (shipping calculations, city lookup)
- **Ratings** - PHP 8.1/Apache + Symfony + MySQL (product ratings)
- **Payment** - Python/Flask + RabbitMQ (payment processing, order publishing)
- **Dispatch** - Go + RabbitMQ (order fulfillment, async consumer)

### Communication Patterns

**Synchronous (HTTP/REST):**
- All services expose port 8080 (except Ratings on port 80)
- Health checks at `/health` endpoint
- Web reverse proxies to all backend services
- Cart calls Catalogue for product info
- Payment calls User and Cart services
- Shipping calls Cart to add shipping costs

**Asynchronous (RabbitMQ):**
- Payment publishes order messages to `robot-shop` exchange (routing key: `orders`)
- Dispatch consumes from `orders` queue
- Queue/exchange are durable for reliability

### Database Schema

**MongoDB (`catalogue` database):**
- Collection: `products` - Fields: `sku`, `name`, `categories[]`, `description`, `price`, `image`
- Collection: `users` - User accounts and order history
- Collection: `orders` - Order documents

**MySQL (shared by Shipping & Ratings):**
- Shipping tables: `cities`, `codes` - Geographic data for shipping calculations
- Ratings tables: Symfony ORM managed

**Redis:**
- Keys: User session IDs or cart IDs
- Values: JSON strings containing cart data `{items: [{sku, qty, price}], total}`

## Key Patterns & Conventions

### Observability

**All services include OpenTelemetry instrumentation:**

- **Node.js services**: Instana collector + OpenTelemetry SDK, Pino structured logging
- **Java (Shipping)**: OpenTelemetry Java agent downloaded at runtime
- **Python (Payment)**: OpenTelemetry CLI wrapper (`opentelemetry-instrument`)
- **Go (Dispatch)**: Native OpenTelemetry with gRPC exporter
- **PHP (Ratings)**: OpenTelemetry PHP extension
- **Nginx (Web)**: Instana sensor (requires `INSTANA_AGENT_KEY` during build)

**Prometheus Metrics:**
- Cart: Counter for items added (`/metrics`)
- Payment: Counters and histograms for purchases, cart value (`/metrics`)

**Datacenter Tagging:**
Node.js, Java, and Go services randomly tag themselves with datacenter regions (US-EAST-1, US-WEST-2, EU-WEST-1, EU-CENTRAL-1, AP-SOUTHEAST-2) to simulate distributed deployments.

### Environment Variables

Critical configuration via environment variables:

```bash
# Catalogue
MONGO_URL=mongodb://mongodb:27017/catalogue
GO_SLOW=0  # Simulate slow responses

# User
MONGO_URL=mongodb://mongodb:27017/users

# Cart
REDIS_HOST=redis
CATALOGUE_HOST=catalogue

# Shipping
DB_HOST=mysql
CART_ENDPOINT=http://cart:8080

# Payment
CART_HOST=cart
USER_HOST=user
PAYMENT_GATEWAY=https://www.paypal.com
PAYMENT_DELAY_MS=0  # Simulate payment latency

# Dispatch
AMQP_HOST=rabbitmq
DISPATCH_ERROR_PERCENT=0  # Simulate failures

# Web (Nginx)
CATALOGUE_HOST=catalogue
USER_HOST=user
CART_HOST=cart
SHIPPING_HOST=shipping
PAYMENT_HOST=payment
RATINGS_HOST=ratings
INSTANA_EUM_KEY=<optional>
INSTANA_EUM_REPORTING_URL=<optional>
```

### Container Build Strategy

**Multi-stage builds** are used for Java (Shipping) and Nginx (Web):
- Stage 1: Build artifacts (Maven compile, download dependencies)
- Stage 2: Minimal runtime image with only compiled binaries

**Base Images:**
- Node.js: `node:14`
- Python: `python:3.9`
- Java: `adoptopenjdk/openjdk8:latest`
- Go: `golang:1.20` (build) + `debian:12` (runtime)
- PHP: `php:8.1-apache`
- Nginx: `nginx:1.21.6`

### Health Check Pattern

All services implement `/health` endpoint returning JSON:

```json
{
  "app": "OK",
  "database": true,
  "redis": true
}
```

Docker Compose health checks: 10s interval, 10s timeout, 3 retries

### Logging Standards

**Node.js services** use Pino logger:
- Structured JSON logs
- Info level default
- Express middleware integration
- No pretty-print in production

## Common Development Workflows

### Adding a New Service

1. Create service directory with Dockerfile
2. Add service to `docker-compose.yaml` with proper `depends_on`
3. Add Kubernetes deployment/service in `K8s/helm/templates/`
4. Update `K8s/helm/values.yaml` with service configuration
5. Include health check endpoint
6. Add OpenTelemetry instrumentation
7. Update Web Nginx config to reverse proxy new endpoint (if needed)

### Modifying Database Schema

**MongoDB:**
- Update initialization script in `mongo/docker-entrypoint-initdb.d/`
- Data seeded on container first start

**MySQL:**
- Update SQL scripts in `mysql/docker-entrypoint-initdb.d/`
- For Shipping: Modify Spring JPA entities
- For Ratings: Modify Symfony ORM entities

### Testing Service Communication

```bash
# Test from within a service container
docker exec -it robot-shop-cart-1 sh
curl http://catalogue:8080/products

# Test RabbitMQ queue
docker exec -it robot-shop-rabbitmq-1 rabbitmqctl list_queues
docker exec -it robot-shop-rabbitmq-1 rabbitmqctl list_exchanges

# Monitor Redis
docker exec -it robot-shop-redis-1 redis-cli
> KEYS *
> GET <cart-id>
```

## File Structure Reference

```
robot-shop/
├── cart/              - Node.js cart service
├── catalogue/         - Node.js catalogue service
├── user/              - Node.js user service
├── payment/           - Python payment service
├── shipping/          - Java Spring Boot shipping service
├── ratings/           - PHP Symfony ratings service
├── dispatch/          - Go dispatch service
├── web/               - Nginx reverse proxy + AngularJS frontend
├── mongo/             - MongoDB with init scripts
├── mysql/             - MySQL with init scripts
├── load-gen/          - Python Locust load generator
├── K8s/
│   ├── helm/          - Helm chart for Kubernetes
│   └── *.yaml         - Raw K8s manifests
├── OpenShift/         - OpenShift-specific configs
├── DCOS/              - Marathon/DCOS manifests
├── Swarm/             - Docker Swarm configs
├── fluentd/           - Log aggregation config
├── docker-compose.yaml
└── .env               - Image registry and version tags
```

## Deployment Targets

This application supports multiple orchestration platforms:

- **Docker Compose** - Local development
- **Kubernetes** - Production via Helm chart
- **OpenShift** - Set `openshift=true` in Helm
- **Minikube/Minishift** - Set `nodeport=true` in Helm
- **Docker Swarm** - See `Swarm/` directory
- **Marathon/DCOS** - See `DCOS/` directory

## Performance & Scaling

### Kubernetes Resource Limits (from Helm chart)

Default per service:
```yaml
limits:
  cpu: 200m
  memory: 100Mi
requests:
  cpu: 100m
  memory: 50Mi
```

### Autoscaling

Enable Horizontal Pod Autoscaler:
```bash
# Requires metrics-server in kube-system
kubectl -n kube-system get deployment metrics-server

# Apply autoscaling
K8s/autoscale.sh
```

### Load Testing Strategy

Locust-based load generator simulates:
- Product browsing
- User registration/login
- Adding items to cart
- Checkout process
- Random delays between actions

Configure via environment variables: `NUM_CLIENTS`, `RUN_TIME`, `ERROR`, `SILENT`

## Security Notes

- **No authentication** is implemented between services
- **No input validation** on most endpoints
- **CORS is wide open** (`Access-Control-Allow-Origin: *`)
- **Database credentials** are hardcoded in service configs
- **Do not use in production** - this is a learning sandbox only

## Troubleshooting

### Services not communicating

Check Docker network or K8s DNS:
```bash
# Docker Compose
docker network inspect robot-shop_robot-shop

# Kubernetes
kubectl -n robot-shop get svc
kubectl -n robot-shop get endpoints
```

### Database connection failures

Services implement exponential backoff retries. Check logs:
```bash
docker logs robot-shop-catalogue-1
kubectl -n robot-shop logs deployment/catalogue
```

### RabbitMQ messages not flowing

Verify queue bindings:
```bash
docker exec robot-shop-rabbitmq-1 rabbitmqctl list_bindings
```

Expected: `robot-shop` exchange bound to `orders` queue with routing key `orders`