"""
毎日1件、queue.json の中からまだ投稿していない記事を選んで
Instagram（@dr._teachers）に自動投稿するスクリプト。

前提:
- 環境変数 IG_ACCESS_TOKEN, IG_USER_ID がセットされていること（GitHub Actions の Secrets 経由）
- 画像は GitHub Pages で公開されていること
  （Graph API は image_url でしか画像を受け取れないため）
- GitHub Pages の公開URLは PAGES_BASE_URL で指定する
  （例: https://osa0508.github.io/dr-teachers-auto-post）

流れ:
  1. queue.json を読み込み、posted=false の最初の記事を選ぶ
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
GRAPH_BASE = f"https://graph.instagram.com/{GRAPH_API_VERSION}"
QUEUE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "queue.json")


def _post(url, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTPエラー詳細: {body}")
        raise


def _get(url, params):
    qs = urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(f"{url}?{qs}") as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTPエラー詳細: {body}")
        raise


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


THREADS_BASE = "https://graph.threads.net/v1.0"
THREADS_TEXT_LIMIT = 500


def build_threads_text(caption):
    """Instagram用キャプションをThreads用に整形する。
    - ハッシュタグだけの行を除去（Threadsはトピックタグ1つが基本）
    - 先頭のハッシュタグ1つだけをトピックタグとして末尾に付ける
    - 500文字を超える場合は切り詰める
    """
    lines = caption.split("\n")
    body_lines = []
    first_tag = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            tags = [t for t in stripped.split() if t.startswith("#")]
            if tags and first_tag is None:
                first_tag = tags[0]
            continue
        body_lines.append(line)
    text = "\n".join(body_lines).strip()
    suffix = f"\n\n{first_tag}" if first_tag else ""
    max_body = THREADS_TEXT_LIMIT - len(suffix)
    if len(text) > max_body:
        text = text[: max_body - 1].rstrip() + "…"
    return text + suffix


def post_to_threads(threads_user_id, threads_token, image_url, caption):
    """Threadsに画像つきで投稿する。成功したら投稿IDを返す。"""
    text = build_threads_text(caption)
    container = _post(
        f"{THREADS_BASE}/{threads_user_id}/threads",
        {
            "media_type": "IMAGE",
            "image_url": image_url,
            "text": text,
            "access_token": threads_token,
        },
    )
    if "id" not in container:
        raise RuntimeError(f"Threadsコンテナ作成に失敗しました: {container}")
    container_id = container["id"]
    print(f"Threadsコンテナ作成完了: {container_id}")

    # 画像の処理完了を待つ
    waited = 0
    while waited < 120:
        status = _get(
            f"{THREADS_BASE}/{container_id}",
            {"fields": "status,error_message", "access_token": threads_token},
        )
        if status.get("status") == "FINISHED":
            break
        if status.get("status") == "ERROR":
            raise RuntimeError(f"Threadsメディア処理でエラー: {status}")
        time.sleep(5)
        waited += 5
    else:
        raise TimeoutError("Threadsメディア処理がタイムアウトしました")

    published = _post(
        f"{THREADS_BASE}/{threads_user_id}/threads_publish",
        {"creation_id": container_id, "access_token": threads_token},
    )
    if "id" not in published:
        raise RuntimeError(f"Threads公開に失敗しました: {published}")
    return published["id"]


def main():
    ig_user_id = (os.environ.get("IG_USER_ID") or "").strip()
    access_token = (os.environ.get("IG_ACCESS_TOKEN") or "").strip()
    pages_base_url = (os.environ.get("PAGES_BASE_URL") or "").strip().rstrip("/")

    if not ig_user_id or not access_token:
        print("IG_USER_ID と IG_ACCESS_TOKEN を環境変数にセットしてください", file=sys.stderr)
        sys.exit(1)
    if not pages_base_url:
        print("PAGES_BASE_URL を環境変数にセットしてください（例: https://osa0508.github.io/dr-teachers-auto-post）", file=sys.stderr)
        sys.exit(1)

    print(f"DEBUG: IG_USER_ID='{ig_user_id}' (len={len(ig_user_id)})")
    print(f"DEBUG: access_token length={len(access_token)}, starts='{access_token[:6]}', ends='{access_token[-6:]}'")

    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        queue = json.load(f)

    next_post = None
    for item in queue:
        if not item.get("posted"):
            next_post = item
            break

    if next_post is None:
        print("投稿可能な記事がキューにありません。queue.json に新しい記事を追加してください。")
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

    # Threadsにも同じ内容を投稿（失敗してもInstagram側の記録には影響させない）
    threads_user_id = (os.environ.get("THREADS_USER_ID") or "").strip()
    threads_token = (os.environ.get("THREADS_ACCESS_TOKEN") or "").strip()
    if threads_user_id and threads_token:
        try:
            threads_id = post_to_threads(threads_user_id, threads_token, image_url, caption)
            next_post["threads_posted_at"] = datetime.now(timezone.utc).isoformat()
            print(f"Threads投稿完了: id={threads_id}")
        except Exception as e:  # noqa: BLE001
            print(f"WARNING: Threads投稿に失敗しました（Instagramは投稿済み）: {e}", file=sys.stderr)
    else:
        print("THREADS_USER_ID / THREADS_ACCESS_TOKEN が未設定のため、Threads投稿はスキップします")

    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"queue.json を更新しました（{next_post['id']} を posted=true に）")


if __name__ == "__main__":
    main()
