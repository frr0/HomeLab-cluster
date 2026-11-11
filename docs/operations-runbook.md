# Operational Runbook & Maintenance Guide

## 1. Routine Health Checks

Routine health inspection can be performed via `kubectl`, Headlamp, or the cluster Telegram bot.

### Quick Verification via Kubectl
```bash
# Verify cluster node status and readiness
kubectl get nodes -o wide

# Check health of all homelab pods
kubectl get pods -n homelab -o wide

# Verify current CPU and RAM consumption
kubectl top nodes
kubectl top pods -n homelab
```

### Quick Verification via Telegram Bot
- Send `/pods` to view real-time status indicators across namespaces.
- Send `/top` to receive CPU and RAM telemetry summaries.
- Send `/apps` to trigger an automated HTTP reachability probe.

---

## 2. Workload Maintenance & Upgrades

### Modifying a Deployment
Workloads are declared in `k8s-manifests/`. Do not apply ad-hoc changes directly on the server.
1. Update the appropriate manifest in `k8s-manifests/` on the workstation.
2. Commit and push changes:
   ```bash
   git commit -am "chore(k8s): adjust nextcloud memory limits"
   git push origin main
   ```
3. ArgoCD will reconcile the cluster state within seconds.

### Manual Force Rolling Restart
If a service must be restarted without Git updates:
```bash
kubectl rollout restart deployment/paperless-web -n homelab
kubectl rollout restart deployment/nextcloud -n homelab
```

---

## 3. Incident Response & Troubleshooting

### Scenario A: Pod in `CrashLoopBackOff`
1. Check the previous container termination logs:
   ```bash
   kubectl logs -n homelab -l app=<app-name> --previous
   ```
2. Inspect the pod lifecycle events:
   ```bash
   kubectl describe pod -n homelab -l app=<app-name>
   ```
3. Verify that database credentials in `homelab-secrets` are valid and reachable.

### Scenario B: ArgoCD Reports `OutOfSync`
1. Access the ArgoCD Web UI at `http://192.168.1.100:30200`.
2. Inspect the red application card to identify the syntax error or schema mismatch.
3. Fix the manifest locally, commit, and push to Git.

### Scenario C: Host Storage Permissions Issue
Containers mounting `hostPath` volumes must have permission to read and write to the designated host paths:
```bash
# Verify directory ownership on the Fedora Server
ls -ld /home/server/homelab-storage/<service-name>

# Fix Nextcloud permissions (UID 33: www-data)
sudo chown -R 33:33 /home/server/homelab-storage/nextcloud/html

# Fix standard user permissions (UID 1000)
sudo chown -R 1000:1000 /home/server/homelab-storage/<service-name>
```

---

## 4. Backup & Disaster Recovery Strategy

- **Declarative Manifests**: All workload specifications, ingress rules, and configurations reside in this Git repository.
- **Relational Databases (MariaDB)**: Automated nightly database dumps via `mysqldump`:
  ```bash
  kubectl exec -n homelab deploy/firefly-db -- mysqldump -u root -p${ROOT_PW} firefly > firefly_backup_$(date +%F).sql
  ```
- **Persistent Data Storage**: Host directories under `/home/server/homelab-storage/` are replicated off-site or to secondary workstations via Syncthing and restic snapshots.
