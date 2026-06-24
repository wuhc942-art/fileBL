# Cloudflare Tunnel Deployment

This dashboard is a local Python service. Cloudflare Tunnel can expose it through an HTTPS address without opening router ports.

## Prerequisites

- A Cloudflare account.
- A domain already added to Cloudflare if you want a stable hostname such as `fahuo.example.com`.
- `cloudflared` installed on the dashboard computer.
- Cloudflare Access enabled before sharing the address outside the office.

## Local Service

Start locally:

```powershell
.\start_dashboard.ps1
```

Local URL:

```text
http://127.0.0.1:8765/
```

## Temporary Test Tunnel

Use this only for a short test:

```powershell
.\start_quick_test_tunnel.ps1
```

Cloudflare will print a temporary HTTPS URL in the terminal.

## Named Tunnel

Create the tunnel and route a hostname in Cloudflare first. Then run:

```powershell
.\start_public_dashboard.ps1 -TunnelName fahuo-dashboard
```

If Cloudflare provides a tunnel token, run:

```powershell
.\start_public_dashboard.ps1 -TunnelToken "PASTE_TOKEN_HERE"
```

## Security Checklist

- Turn on Cloudflare Access.
- Allow only approved email addresses.
- Do not publish the upload page without access control.
- Do not commit tunnel tokens, uploaded Excel files, reports, or logs to GitHub.
- Prefer read-only sharing for outside users until account roles are implemented.

## Maintenance

Back up these local paths regularly:

```text
shipment_config.json
reports\
uploads\
```

If a future SQLite history database is added, also back up:

```text
data\history.sqlite
```
