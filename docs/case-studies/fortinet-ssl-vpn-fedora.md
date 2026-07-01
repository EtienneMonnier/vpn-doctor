# Case Study: Fortinet SSL-VPN on Fedora

## Purpose

This case study records the real-world debugging session that inspired VPN Doctor.

Sensitive values have been sanitized.

## Environment

- Fedora GNOME
- FortiGate SSL-VPN
- Custom VPN port
- OpenFortiVPN CLI backend
- NetworkManager FortiSSLVPN plugin

## Symptoms

1. GNOME NetworkManager did not expose a "custom port" checkbox.
2. The FortiGate used a certificate that was not trusted locally.
3. NetworkManager connected but broke existing Internet/RDP sessions because of a default route through the VPN.
4. After split tunnel correction, NetworkManager showed the tunnel as connected but internal traffic did not return.
5. OpenFortiVPN worked correctly with the same credentials and gateway.

## Lessons learned

### Custom port

NetworkManager expects:

```text
gateway.example.com:44443
```

instead of a separate custom port checkbox.

### Certificate

OpenFortiVPN can display a trusted certificate fingerprint suggestion:

```bash
--trusted-cert <sha256-fingerprint>
```

NetworkManager can store it manually:

```bash
nmcli connection modify <profile> +vpn.data trusted-cert=<sha256-fingerprint>
```

### Full tunnel

A default route through `ppp0` can break existing Internet traffic.

Possible NetworkManager correction:

```bash
nmcli connection modify <profile> ipv4.never-default yes
nmcli connection modify <profile> ipv6.never-default yes
```

### Tunnel up but unusable

A tunnel can appear connected while no reply traffic returns.

Useful checks:

```bash
ip route
ip addr
resolvectl status
sudo tcpdump -ni ppp0 icmp
```

## Product opportunity

A normal VPN client only says "failed" or "connected".

VPN Doctor should say:

```text
The tunnel is up, packets leave the VPN interface, but no replies return.
This suggests a backend-specific issue or a remote policy/routing problem.
Try OpenFortiVPN instead of NetworkManager FortiSSLVPN.
```
