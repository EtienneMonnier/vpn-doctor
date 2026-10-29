# Case Study: "The VPN Works, but Remote Desktop Fails"

All addresses and names in this document are sanitized.

## Symptom

A Linux user connected to a WireGuard VPN could not open a Remote Desktop
session on a Windows server behind it with Remmina. The first suspicion was
a wrong password or a broken VPN.

## Investigation, phase by phase

| Phase | Check | Result |
| --- | --- | --- |
| Tunnel | handshake, ping to the VPN gateway, DNS | OK |
| Path MTU | ping with "don't fragment" up to the tunnel MTU | OK |
| TCP | `192.0.2.41:3389` | open |
| X.224 negotiation | server selected NLA (CredSSP) | OK |
| TLS | handshake with the self-signed certificate | OK |
| NLA | credentials | **accepted** |
| Licensing | client log | **aborted by the server** |

The decisive FreeRDP lines were:

```text
[rdp_client_connect_license]: license connection sequence aborted.
CONNECTION_STATE_LICENSING status STATE_RUN_FAILED
```

A wrong password fails earlier, during NLA, with `ERRCONNECT_LOGON_FAILURE`.
Reaching the licensing phase proves the credentials were accepted.

The Kerberos `default realm` errors in the same log were noise: FreeRDP tries
Kerberos, then falls back to NTLM.

## Confirmation

Connecting in console mode (Remmina: *Advanced > Attach to console*, xfreerdp:
`/admin`) bypasses Remote Desktop licensing. It worked immediately.

## Root cause

The Remote Desktop Services licensing grace period had expired on the server,
or its license server was unreachable. Nothing was wrong with the VPN, the
Linux workstation or the password.

## What VPN Doctor learned

```bash
journalctl --user -b -o cat | vpn-doctor rdp 192.0.2.41 --log -
```

The `rdp` command probes phases TCP, negotiation and TLS without credentials,
then explains the client log. It turned a half-day investigation into one
command.
