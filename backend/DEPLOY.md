# Backend deployment (AWS)

Migrated off Fly.io in July 2026 (Fly deploys were blocked by overdue invoices).

## Why ECS Fargate + ALB + CloudFront instead of App Runner

App Runner and Lightsail Container Service were both blocked by a
`SubscriptionRequiredException` / service-limit hold on this AWS account —
a common restriction on newly-verified accounts. ECS Fargate and RDS worked
fine, so the stack below is a small step up from the App Runner plan:
ALB + CloudFront in front of Fargate instead of App Runner's built-in
HTTPS endpoint. CloudFront is only there to provide a default `*.cloudfront.net`
HTTPS URL (the ALB alone only serves HTTP, and the frontend on Vercel is
HTTPS-only — browsers block mixed-content fetches from an HTTP API).

If App Runner opens up on this account later, this could be simplified by
dropping the ALB/CloudFront in favor of an App Runner service pulling the
same ECR image.

## Resources (region: ap-southeast-1 / Singapore)

| Resource | Name / ID |
|---|---|
| RDS PostgreSQL | `octane-db` — `octane-db.c3q0ae68eyze.ap-southeast-1.rds.amazonaws.com` (private, not publicly accessible) |
| ECR repository | `octane-api` — `308324916290.dkr.ecr.ap-southeast-1.amazonaws.com/octane-api` |
| ECS cluster | `octane-cluster` (Fargate) |
| ECS service | `octane-api-svc` |
| ECS task definition family | `octane-api` |
| Application Load Balancer | `octane-alb` — `octane-alb-84715979.ap-southeast-1.elb.amazonaws.com` (HTTP only, internal use) |
| Target group | `octane-tg` (port 8000, health check `GET /`) |
| CloudFront distribution | `E2W3WXQNNMJY1I` — **`https://d2w9pgvodb18rj.cloudfront.net`** (public API URL) |
| VPC | default VPC `vpc-0c19637fa1fce9031`, peered with Lightsail VPC (unused after the App Runner/Lightsail pivot, harmless to leave) |

## IAM

- `octane-gh-actions-role` — OIDC role assumed by GitHub Actions (trust restricted to `repo:ArdenoStudio/octane:*`). No static AWS keys are stored in GitHub. Grants: ECR push, ECS deploy, `secretsmanager:GetSecretValue` on `octane/database-url`.
- `octane-ecs-execution-role` — ECS task execution role (pulls image from ECR, reads `octane/database-url` from Secrets Manager, writes logs).
- `octane-ecs-task-role` — empty for now (no AWS API calls from inside the app).

## Secrets

- **`octane/database-url`** (AWS Secrets Manager, ap-southeast-1) — the Postgres connection string. Read by the ECS task at container start (`secrets` in the task definition). No `DATABASE_URL` GitHub secret is used anymore.
- **`DISPATCH_SECRET`** (GitHub Actions secret) — rotated during this migration since the old Fly-era value couldn't be read back. Injected into the ECS task definition at deploy time by `deploy-backend.yml`.
- `SMTP_HOST` / `SMTP_USER` / `SMTP_PASS` / `ALERT_FROM_EMAIL` / `SITE_URL` (GitHub Actions secrets, optional) — same as before, unchanged.

## Why scrape.yml/digest.yml run as one-off ECS tasks instead of on the runner directly

RDS is in a private VPC with no public access (deliberately — the original plan called for a
locked-down security group, not the whole internet). GitHub-hosted runners have no network path
into that VPC, so `scrape.yml`, `scrape-news.yml`, and `digest.yml` no longer run Python directly
on the runner. Instead they call `aws ecs run-task` (via the OIDC role) to run the exact same
container image with an overridden command inside the VPC, wait for it to stop, and check its
exit code. The task reads `DATABASE_URL` from Secrets Manager itself via the ECS execution role,
same as the live service. The `price_changed` step output (used to conditionally dispatch AI
sentiment analysis) is recovered by grepping the task's CloudWatch log stream, since the script
can't write to the runner's `GITHUB_OUTPUT` file from inside the container.

## Deploying

Push to `master` with changes under `backend/**` (or run `deploy-backend.yml` manually via
workflow_dispatch). The workflow assumes `octane-gh-actions-role` via OIDC, builds and pushes
the Docker image to ECR, renders a new task definition revision, and updates the ECS service.

## First-time schema setup

RDS starts empty — `python -m app.db.init` (schema) was run once as a one-off ECS task before
the first scrape. `app/main.py` only runs incremental migrations on startup, not the base schema.

## Estimated monthly cost

RDS db.t4g.micro ~$13, Fargate 0.5 vCPU/1GB ~$9, ALB ~$16, CloudFront ~$0–1 at this traffic ≈ **~$38–40/month**.
