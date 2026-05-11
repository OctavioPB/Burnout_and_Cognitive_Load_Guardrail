# Secrets Rotation Runbook

> **Audience:** Platform Engineering / Security team.
> All secrets are stored in AWS Secrets Manager (or HashiCorp Vault for self-hosted).
> Rotate on schedule **or** immediately on suspected compromise.

---

## Rotation schedule

| Secret | Rotation frequency | Owner |
|---|---|---|
| `POSTGRES_PASSWORD` | 90 days | Platform Engineering |
| `REDIS_PASSWORD` | 90 days | Platform Engineering |
| `KAFKA_SASL_PASSWORD` | 90 days | Platform Engineering |
| `GOOGLE_SERVICE_ACCOUNT_KEY` | 180 days or on staff change | Platform Engineering |
| `JIRA_API_TOKEN` | 90 days | Platform Engineering |
| `SLACK_BOT_TOKEN` | On-demand (Slack rotates automatically on revocation) | Platform Engineering |
| `GITHUB_APP_PRIVATE_KEY` | 365 days | Platform Engineering |
| JWT signing key (`JWT_SECRET`) | 90 days | Backend team |

---

## Step-by-step: rotate a secret

### 1. Generate the new credential
- **Database password:** `openssl rand -base64 32`
- **JWT secret:** `openssl rand -hex 64`
- **API tokens:** use the provider's admin portal (Jira, Slack, GitHub)

### 2. Write the new value to Secrets Manager
```bash
aws secretsmanager put-secret-value \
  --secret-id burnout-guardrail/<env>/<secret-name> \
  --secret-string "<new-value>"
```
Tag the rotation: `--version-stages AWSPENDING`

### 3. Validate the new credential in staging
```bash
# For DB passwords:
PGPASSWORD=<new-password> psql -h $DB_HOST -U $DB_USER -d burnout_guardrail -c "SELECT 1"

# For API tokens: use the connector smoke test:
SECRET=<new-token> python scripts/test_connector.py --connector jira
```

### 4. Promote to AWSCURRENT and demote old value
```bash
aws secretsmanager update-secret-version-stage \
  --secret-id burnout-guardrail/<env>/<secret-name> \
  --version-stage AWSCURRENT \
  --move-to-version-id <new-version-id> \
  --remove-from-version-id <old-version-id>
```

### 5. Roll the affected pods to pick up the new secret
```bash
kubectl rollout restart deployment/<service-name> -n guardrail
kubectl rollout status deployment/<service-name> -n guardrail
```

### 6. Verify in production
- Check Grafana: no spike in 5xx errors after pod restart
- Run: `curl -s https://guardrail.example.com/health | jq .status`

### 7. Invalidate the old credential
- Database: `ALTER USER burnout_app PASSWORD '<new-password>';` (after all pods are on new secret)
- API tokens: revoke the old token in the provider's admin portal

---

## Emergency rotation (suspected compromise)

If you suspect a secret has been leaked:

1. **Immediately** revoke the old credential at the source (DB, Jira admin, Slack app settings, etc.).
2. Generate a new credential and write it to Secrets Manager (Steps 1–4 above).
3. Roll all affected pods (Step 5).
4. File a security incident in the incident management system with:
   - Which secret was compromised
   - When it was first suspected compromised
   - Who had access to it
   - Any suspicious access patterns in audit logs
5. Notify the DPO if the compromised secret could allow access to personal data.
6. Conduct a post-incident review within 5 business days.

---

## Google Service Account key rotation

Google service account keys require special handling due to domain-wide delegation:

1. In Google Cloud Console → IAM → Service Accounts → select the SA.
2. Go to Keys tab → Add Key → Create new key (JSON).
3. Download the new key file.
4. Base64-encode: `base64 -i new-key.json | tr -d '\n'`
5. Write to Secrets Manager as `GOOGLE_SERVICE_ACCOUNT_KEY`.
6. Run smoke test (Step 3 above).
7. Roll pods (Step 5).
8. Delete the old key from Google Cloud Console (Keys tab).

---

## Notes
- Never commit secrets to git. The `.env` file is in `.gitignore`.
- Use `git secret` or `sops` for any config that must be stored encrypted in the repo.
- If a secret appears in a git commit by accident: immediately rotate it, then use `git filter-repo` to purge the history and force-push. Notify security.
