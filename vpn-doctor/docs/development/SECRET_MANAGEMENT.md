# Secret Management

## Goal

Use the Linux Secret Service API for passwords and tokens.

GNOME Keyring is the reference implementation.

## Design

`VPNProfile` must not store passwords.

Future flow:

1. User selects a profile.
2. Controller asks SecretService for password.
3. SecretService retrieves from GNOME Keyring.
4. Backend receives password only at runtime.
5. Password is sent to subprocess stdin if required.
6. Password is never logged.

## Future API sketch

```python
class SecretService:
    def get_password(self, profile_id: str) -> str | None:
        ...

    def set_password(self, profile_id: str, password: str) -> None:
        ...

    def delete_password(self, profile_id: str) -> None:
        ...
```
