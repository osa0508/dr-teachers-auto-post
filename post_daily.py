"""
毎日1件、content/queue.json の中からまだ投稿していない記事を選んで
Instagram（@dr._teachers）に自動投稿するスクリプト。

前提:
- 環境変数 IG_ACCESS_TOKEN, IG_USER_ID がセットされていること（GitHub Actions の Secrets 経由）
- 画像は GitHub Pages で公開されていること
  （Graph API は image_url でしか画像を受け取れないため）
- GitHub Pages の公開URLは PAGES_BASE_URL で指定する
  （例: https://osa0508.github.io/dr-teachers-auto-post）

流れ:
  1. content/queue.json を読み込み、posted=false の最初の記事を選ぶ
  2. Instagram Graph API でメディアコンテナを作成 → 完了待ち → 公開
  3. 成功したら queue.json の該当記事を posted=true, posted_at=<日時> に更新して保存
     （GitHub Actions 側でこのファイルをコミット・プッシュする）
"""
import os
import sys
import time
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone

GRAPH_API_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
QUEUE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "queue.json")


def _post(url, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def _get(url, params):
    qs = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{url}?{qs}") as resp:
        return json.loads(resp.read().decode())


def create_container(ig_user_id, access_token, image_url, caption):
    url = f"{GRAPH_BASE}/{ig_user_id}/media"
    params = {"image_url": image_url, "caption": caption, "access_token": access_token}
    result = _post(url, params)
    if "id" not in result:
        raise RuntimeError(f"コンテナ作成に失敗しました: {result}")
    return result["id"]


def wait_until_ready(container_id, access_token, timeout=120, interval=5):
    url = f"{GRAPH_BASE}/{container_id}"
    waited = 0
    while waited < timeout:
        result = _get(url, {"fields": "status_code", "access_token": access_token})
        status = result.get("status_code")
        if status == "FINISHED":
            return True
        if status == "ERROR":
            raise RuntimeError(f"メディア処理でエラー: {result}")
        time.sleep(interval)
        waited += interval
    raise TimeoutError("メディア処理がタイムアウトしました")


def publish(ig_user_id, access_token, container_id):
    url = f"{GRAPH_BASE}/{ig_user_id}/media_publish"
    params = {"creation_id": container_id, "access_token": access_token}
    result = _post(url, params)
    if "id" not in result:
        raise RuntimeError(f"公開に失敗しました: {result}")
    return result["id"]


def main():
    ig_user_id = os.environ.get("IG_USER_ID")
    access_token = os.environ.get("IG_ACCESS_TOKEN")
    pages_base_url = os.environ.get("PAGES_BASE_URL", "").rstrip("/")

    if not ig_user_id or not access_token:
        print("IG_USER_ID と IG_ACCESS_TOKEN を環境変数にセットしてください", file=sys.stderr)
        sys.exit(1)
    if not pages_base_url:
        print("PAGES_BASE_URL を環境変数にセットしてください（例: https://osa0508.github.io/dr-teachers-auto-post）", file=sys.stderr)
        sys.exit(1)

    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        queue = json.load(f)

    next_post = None
    for item in queue:
        if not item.get("posted"):
            next_post = item
            break

    if next_post is None:
        print("投稿可能な記事がキューにありません。content/queue.json に新しい記事を追加してください。")
        sys.exit(0)

    image_url = f"{pages_base_url}/{next_post['image']}"
    caption = next_post["caption"]

    print(f"投稿対象: {next_post['id']} ({next_post['title']})")
    print(f"画像URL: {image_url}")

    container_id = create_container(ig_user_id, access_token, image_url, caption)
    print(f"コンテナ作成完了: {container_id}")
    wait_until_ready(container_id, access_token)
    print("メディア処理完了")
    media_id = publish(ig_user_id, access_token, container_id)
    print(f"投稿完了: media_id={media_id}")

    next_post["posted"] = True
    next_post["posted_at"] = datetime.now(timezone.utc).isoformat()

    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"queue.json を更新しました（{next_post['id']} を posted=true に）")


if __name__ == "__main__":
    main()
