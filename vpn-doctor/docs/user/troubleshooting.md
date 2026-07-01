# Troubleshooting

## `vpn-doctor diagnose` says gateway unreachable

The default demo profile uses `vpn.example.com`, which is not your real VPN.

This is expected until profile management is implemented.

## `openfortivpn` missing

Install it with your distribution package manager.

Fedora:

```bash
sudo dnf install openfortivpn
```

## Do not put real secrets in the repository

Use placeholders in documentation and examples.
