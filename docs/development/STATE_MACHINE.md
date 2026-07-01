# VPN Connection State Machine

## States

```text
disconnected
connecting
authenticating
configuring
connected
disconnecting
failed
unknown
```

## State transitions

```mermaid
stateDiagram-v2
    [*] --> disconnected
    disconnected --> connecting: connect()
    connecting --> authenticating: gateway reached
    authenticating --> configuring: auth ok
    configuring --> connected: tunnel up
    connected --> disconnecting: disconnect()
    disconnecting --> disconnected: cleanup ok
    connecting --> failed: gateway/cert error
    authenticating --> failed: auth error
    configuring --> failed: ppp/config error
    failed --> disconnected: reset
```

## Notes

Not every backend exposes all intermediate states. VPN Doctor should normalize best-effort
signals while preserving raw backend logs for troubleshooting.
