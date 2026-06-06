"""Exchange a Google EmbeddedSetup oauth_token for a master token without printing it."""

from __future__ import annotations

import argparse
import secrets
import stat
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exchange a Google EmbeddedSetup oauth_token for a Google master token."
    )
    parser.add_argument("--email", required=True, help="Google account email address.")
    parser.add_argument(
        "--oauth-token",
        required=True,
        help="oauth_token cookie value from https://accounts.google.com/EmbeddedSetup.",
    )
    parser.add_argument(
        "--out",
        default="master_token.txt",
        help="File to write the master token to. Defaults to master_token.txt.",
    )
    parser.add_argument(
        "--android-id",
        default=None,
        help="Optional Android ID. A random 16 hex-character value is generated if omitted.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        import gpsoauth
    except ImportError:
        print(
            "gpsoauth is not installed. Install it with: uv add gpsoauth",
            file=sys.stderr,
        )
        return 2

    android_id = args.android_id or secrets.token_hex(8)
    response = gpsoauth.exchange_token(args.email, args.oauth_token, android_id)
    token = response.get("Token")
    if not token:
        error = response.get("Error") or response
        print(
            f"No Token returned. The oauth_token may be expired or already used: {error}",
            file=sys.stderr,
        )
        return 1

    output_path = Path(args.out).expanduser().resolve()
    output_path.write_text(token, encoding="utf-8")
    try:
        output_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass

    print(f"Master token written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
