# Autolitics - Project Context Summary
Generated: April 28, 2026

## What is Autolitics?
A car price monitoring app for Uruguay (expanding to Argentina and Brazil) that scrapes MercadoLibre, stores raw HTML, parses into structured data, and generates buy signals when underpriced cars appear.

## Repository
- GitHub: github.com/gollerdev/autolitics
- Local: C:\Users\German\Desktop\python\autolitics

## Architecture
```
ECS Fargate (scraper) → S3 (raw HTML) → SQS → Parser Lambda → S3 (JSONL) → SQS → Loader Lambda → PostgreSQL
```

## AWS Infrastructure
- S3 bucket: `autolitics-data` (us-east-2)
- SQS queue: `autolitics-raw-queue`
- ECR repo: `autolitics-ingestor`
- ECS cluster: `autolitics`
- ECS task: `autolitics-ingestor` (1 vCPU, 2GB, Fargate)
- EventBridge: every 2hrs, 8am-10pm Uruguay `cron(0 11,13,15,17,19,21,23 * * ? *)`
- CloudWatch log group: `/ecs/autolitics-ingestor` (7 day retention)

## Proxy Setup (WORKING)
- Old Android phone running **Every Proxy** on port 8080
- Router forwards port 8080 to phone's local IP (192.168.1.13)
- Cloudflare DNS: `proxy.autolitics.org` → home public IP
- Termux on phone runs `ddns.sh` via cron every 5 minutes to update DNS if IP changes
- Fargate env var: `PROXY_SERVER=http://proxy.autolitics.org:8080`
- If IP gets blocked: restart router → new IP → ddns.sh updates DNS automatically

## Cloudflare
- Domain: autolitics.org
- DNS record: proxy.autolitics.org (A record, TTL 60, not proxied)
- Zone ID: d960f2c99a358dc9a22fec772521f51a
- API Token: <REDACTED> (expires Jan 31 2027)

## Ingestor Service (WORKING)
Location: `services/ingestor/data_ingestion_service.py`

Navigation flow:
1. goto mercadolibre.com.uy
2. Scroll around (warmup)
3. goto autos.mercadolibre.com.uy directly
4. Paginate via offset URLs: `https://autos.mercadolibre.com.uy/_Desde_{offset}_PublishedToday_YES_NoIndex_True`
5. Save each page as `raw/{run_id}/offset_{N}.html` to S3
6. Publish SQS message when done

Data extraction: Nordic script tag `__NORDIC_RENDERING_CTX__` → `_n.ctx.r=` → JSON → `search_api.results`

## Key Files
```
services/ingestor/
  data_ingestion_service.py      ← main scraper
  storage_service/
    s3_storage_service.py        ← S3 upload
    fs_storage_service.py        ← local filesystem
  queue_service/
    sqs_queue_service.py         ← SQS publish
  Dockerfile                     ← playwright:v1.58.0-jammy + xvfb
  entrypoint.sh                  ← starts Xvfb :99, then runs script
  requirements.txt
infrastructure/
  main.tf
  variables.tf
  outputs.tf
  terraform.tf
  fargate.tf
.github/workflows/
  deploy-ingestor.yml            ← CI/CD pipeline
```

## Environment Variables (Fargate)
```
AWS_REGION=us-east-2
S3_BUCKET=autolitics-data
SQS_RAW_QUEUE_URL=https://sqs.us-east-2.amazonaws.com/448648302142/autolitics-raw-queue
PROXY_SERVER=http://proxy.autolitics.org:8080
PROXY_USERNAME=
PROXY_PASSWORD=
```

## SQS Message Format (ingestor → parser)
```json
{
  "run_id": "20260428_052824",
  "started_at": "...",
  "finished_at": "...",
  "enqueued_at": "...",
  "pages_collected": 10,
  "offsets": [0, 48, 96, ...],
  "storage_backend": "s3",
  "bucket": "autolitics-data",
  "base_path": "raw/20260428_052824/",
  "source_url": "https://autos.mercadolibre.com.uy",
  "country": "UY"
}
```

## Known Issues / TODO
- [ ] Build parser Lambda (reads HTML from S3, extracts JSONL, uploads to S3, publishes to SQS)
- [ ] Build loader Lambda (reads JSONL from S3, inserts into PostgreSQL)
- [ ] Set up PostgreSQL (RDS or local)
- [ ] CloudWatch alarm for ECS task failures → SNS email
- [ ] Expand to Argentina and Brazil

## ddns.sh (runs on phone via Termux cron every 5 mins)
```bash
#!/bin/bash
TOKEN="<REDACTED>"
ZONE_ID="d960f2c99a358dc9a22fec772521f51a"
RECORD_NAME="proxy.autolitics.org"

CURRENT_IP=$(curl -s https://api.ipify.org)
RECORD=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records?name=$RECORD_NAME&type=A" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")
RECORD_ID=$(echo $RECORD | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
DNS_IP=$(echo $RECORD | grep -o '"content":"[^"]*' | head -1 | cut -d'"' -f4)

if [ "$CURRENT_IP" != "$DNS_IP" ]; then
  curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$RECORD_ID" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    --data "{\"type\":\"A\",\"name\":\"$RECORD_NAME\",\"content\":\"$CURRENT_IP\",\"ttl\":60,\"proxied\":false}"
fi
```

## Next Steps
3. Build parser Lambda
4. Build loader Lambda
5. Set up PostgreSQL
6. Add CloudWatch alarms
