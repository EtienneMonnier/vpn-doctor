# Error Taxonomy

VPN Doctor should classify failures.

## Categories

- `gateway_unreachable`
- `certificate_untrusted`
- `authentication_failed`
- `mfa_required`
- `saml_unsupported`
- `tunnel_not_created`
- `route_missing`
- `dns_missing`
- `tunnel_up_no_traffic`
- `backend_missing`
- `permission_denied`
- `process_timeout`

## Why taxonomy matters

A normalized error type allows:

- consistent UI messages;
- translations;
- testable diagnostics;
- support reports;
- automatic suggestions.
