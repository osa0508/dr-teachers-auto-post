"""
Instagram長期アクセストークン（60日間有効）の期限が近づいたら、
期限切れ前に呼び出して新しいトークンに更新するスクリプト。

新しいトークンは GitHub Actions のログに出力されます。
出力された値を、リポジトリの Settings > Secrets and variables > Actions で
IG_ACCESS_TOKEN に手動で上書き保存してください。
"""
import os
import sys
import json
import urllib.request
import urllib.parse

GRAPH_API_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


def _get(url, params):
    qs = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{url}?{qs}") as resp:
        return json.loads(resp.read().decode())


def refresh_long_lived_token(access_token):
    url = f"{GRAPH_BASE}/refresh_access_token"
    params = {"grant_type": "ig_refresh_token", "access_token": access_token}
    return _get(url, params)


if __name__ == "__main__":
    access_token = os.environ.get("IG_ACCESS_TOKEN")
    if not access_token:
        print("IG_ACCESS_TOKEN を環境変数にセットしてください", file=sys.stderr)
        sys.exit(1)

    result = refresh_long_lived_token(access_token)
    if "access_token" not in result:
        print(f"トークン更新に失敗しました: {result}", file=sys.stderr)
        sys.exit(1)

    print("=== 新しいアクセストークン（この値をSecretsのIG_ACCESS_TOKENに上書き保存してください） ===")
    print(result["access_token"])
    print(f"有効期限（秒）: {result.get('expires_in')}")
