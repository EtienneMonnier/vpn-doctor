# Fortinet SSL-VPN Case Study

## Environment

- Fedora 44 GNOME.
- FortiGate SSL-VPN.
- Gateway: `192.0.2.10`.
- Custom port: `44443`.
- User realm: `EXAMPLE-AD`.
- NetworkManager plugin: `NetworkManager-fortisslvpn-1.4.1`.
- CLI backend: `openfortivpn-1.23.1`.

## Problem 1 - Custom port in GNOME

FortiClient Windows has a "custom port" checkbox.

NetworkManager does not expose this as a separate checkbox. The port must be included in the gateway field:

```text
192.0.2.10:44443
```

## Problem 2 - Self-signed FortiGate certificate

`openfortivpn` reported:

```text
Gateway certificate validation failed
```

The solution was to trust the SHA-256 digest:

```text
abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
```

For `openfortivpn`:

```bash
sudo openfortivpn 192.0.2.10:44443 \
  -u demo-user \
  --trusted-cert abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
```

For NetworkManager:

```bash
nmcli connection modify ExampleCorp +vpn.data trusted-cert=abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
```

## Problem 3 - Full tunnel breaking existing connections

NetworkManager initially installed a default route through `ppp0`:

```text
default dev ppp0 proto static scope link metric 50
```

This interrupted existing RDP sessions and Internet traffic.

Split tunnel was restored with:

```bash
nmcli connection modify ExampleCorp ipv4.never-default yes
nmcli connection modify ExampleCorp ipv6.never-default yes
```

## Problem 4 - NetworkManager tunnel up but no traffic returned

Observed behavior:

- NetworkManager connected successfully.
- Routes existed.
- `ppp0` existed.
- ICMP requests left through `ppp0`.
- No ICMP replies returned.
- `openfortivpn` worked with the same gateway and credentials.

Traffic capture showed outgoing packets only:

```text
203.0.113.2 > 198.51.100.253: ICMP echo request
```

No replies were captured.

## Hypothesis

The issue appears specific to the NetworkManager Fortinet plugin or its interaction with this FortiGate configuration.

`openfortivpn` directly launched `pppd` with:

```text
nodefaultroute mru 1354 ipcp-accept-local ipcp-accept-remote
```

NetworkManager used different handling and the tunnel was not functionally equivalent.

## Conclusion

For this case, the reliable backend is `openfortivpn`.

VPN Doctor should detect this type of divergence and clearly report:

```text
NetworkManager tunnel is established, but traffic does not return.
Direct openfortivpn backend works.
Recommendation: use openfortivpn for this profile or report plugin issue.
```
