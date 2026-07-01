# Fortinet SSL-VPN Case Study

## Environment

- Fedora 44 GNOME.
- FortiGate SSL-VPN.
- Gateway: `195.135.0.91`.
- Custom port: `44443`.
- User realm: `CAMERUS-AD`.
- NetworkManager plugin: `NetworkManager-fortisslvpn-1.4.1`.
- CLI backend: `openfortivpn-1.23.1`.

## Problem 1 - Custom port in GNOME

FortiClient Windows has a "custom port" checkbox.

NetworkManager does not expose this as a separate checkbox. The port must be included in the gateway field:

```text
195.135.0.91:44443
```

## Problem 2 - Self-signed FortiGate certificate

`openfortivpn` reported:

```text
Gateway certificate validation failed
```

The solution was to trust the SHA-256 digest:

```text
683f3065a488a98cea81ddef8a1def8d26c6f36b03fc6414621fc64e40570be2
```

For `openfortivpn`:

```bash
sudo openfortivpn 195.135.0.91:44443 \
  -u rentplus \
  --trusted-cert 683f3065a488a98cea81ddef8a1def8d26c6f36b03fc6414621fc64e40570be2
```

For NetworkManager:

```bash
nmcli connection modify Camerus +vpn.data trusted-cert=683f3065a488a98cea81ddef8a1def8d26c6f36b03fc6414621fc64e40570be2
```

## Problem 3 - Full tunnel breaking existing connections

NetworkManager initially installed a default route through `ppp0`:

```text
default dev ppp0 proto static scope link metric 50
```

This interrupted existing RDP sessions and Internet traffic.

Split tunnel was restored with:

```bash
nmcli connection modify Camerus ipv4.never-default yes
nmcli connection modify Camerus ipv6.never-default yes
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
10.27.27.2 > 192.168.104.253: ICMP echo request
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
