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

For outside sharing, prefer read-only mode:

```powershell
.\start_public_dashboard.ps1 -TunnelName fahuo-dashboard -ReadOnly
```

If Cloudflare provides a tunnel token, run:

```powershell
.\start_public_dashboard.ps1 -TunnelToken "PASTE_TOKEN_HERE"
```

If an administrator must upload Excel through the public tunnel, set an admin token and send it as `X-Admin-Token` or `adminToken` on write requests:

```powershell
.\start_public_dashboard.ps1 -TunnelName fahuo-dashboard -ReadOnly -AdminToken "CHANGE_THIS_TOKEN"
```

The normal browser UI is intended for local uploads first. Outside users should view the historical dashboard from `data\history.sqlite`.

## Security Checklist

- Turn on Cloudflare Access.
- Allow only approved email addresses.
- Do not publish the upload page without access control.
- Use `-ReadOnly` for outside access unless remote uploading is explicitly needed.
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

The dashboard now uses this SQLite history database after local uploads. Back it up together with reports and config.
