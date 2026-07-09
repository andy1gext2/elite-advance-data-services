"""Generate strong production secrets. Run once, paste into your host's env vars.

    py scripts/gen_secrets.py

Never commit the output. FERNET_KEY encrypts OAuth tokens at rest — if you rotate
it, previously stored tokens can no longer be decrypted (accounts must reconnect).
"""
from __future__ import annotations

import secrets

from cryptography.fernet import Fernet


def main() -> None:
    print("# --- Elite Advance production secrets (keep private) ---")
    print(f"APP_SECRET_KEY={secrets.token_urlsafe(48)}")
    print(f"JWT_SECRET={secrets.token_urlsafe(48)}")
    print(f"FERNET_KEY={Fernet.generate_key().decode()}")


if __name__ == "__main__":
    main()
