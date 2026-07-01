# Case Study - Fortinet, NetworkManager and OpenFortiVPN

## Context

A Linux user needed to connect to a FortiGate SSL VPN using Fedora GNOME.

The available options were:

- NetworkManager FortiSSLVPN plugin;
- `openfortivpn`;
- official FortiClient.

## Observed behaviour

`openfortivpn` connected successfully after the FortiGate certificate fingerprint was
trusted.

NetworkManager could establish a PPP tunnel but traffic did not return through the
tunnel in the tested environment.

## Lessons

This case showed why VPN Doctor should exist:

- users need clear certificate diagnostics;
- users need route and DNS inspection;
- users need backend comparison;
- "tunnel is up" does not always mean "VPN works".

## Sanitization

All hostnames, IP addresses, usernames and certificate fingerprints from the original
case must remain sanitized in public documentation.
