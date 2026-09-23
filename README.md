# dr-teachers-auto-post

家庭教師ライフカラー（Instagram: [@dr._teachers](https://www.instagram.com/dr._teachers)）へ、
gifu-teacher.com のブログ記事をリライトして毎日自動投稿する仕組みです。

GitHub Actions が毎日決まった時刻に実行され、`content/queue.json` の中から
まだ投稿していない記事を1件選んで、画像つきでInstagramに投稿します。

## セットアップ手順（最初の1回だけ）

### 1. Secretsを登録する

このリポジトリの **Settings → Secrets and variables → Actions → New repository secret** から、
以下の2つを登録してください。

| Name | Value |
|---|---|
| `IG_ACCESS_TOKEN` | Instagramの長期アクセストークン |
| `IG_USER_ID` | InstagramビジネスアカウントID（`17841402245236126`） |

### 2. GitHub Pagesを有効にする

投稿する画像はGitHub Pagesで公開する必要があります（Instagram側は画像を直接アップロードできず、公開URLでしか受け取れないため）。

**Settings → Pages** で、以下のように設定してください。

- Source: `Deploy from a branch`
- Branch: `main` / `/ (root)`

保存すると、数分で `https://osa0508.github.io/dr-teachers-auto-post/` が使えるようになります。
（ワークフロー内の `PAGES_BASE_URL` もこのURLに合わせてあります）

### 3. 動作確認（手動実行）

上記2つの設定が終わったら、**Actions タブ → Daily Instagram Post → Run workflow** から
手動で1回実行して、実際にInstagramに投稿されるか確認してください。

成功すると、`content/queue.json` の該当記事が自動的に `posted: true` に更新され、
リポジトリにコミットされます。

## 日々の運用

- 毎日 **21:00 (JST)** に自動実行されます（`.github/workflows/daily-post.yml` の cron設定）
- 投稿するネタがなくなったら、`content/queue.json` に新しい記事を追記してください
  （`scripts/generate_eyecatch.py` で画像を作成 → `content/images/` に保存 → queue.jsonに追加）

## トークンの更新について

Instagramの長期アクセストークンは60日で失効します。期限が近づいたら、
**Actions タブ → Refresh Instagram Token (manual) → Run workflow** を実行してください。

実行ログに新しいトークンが出力されるので、それをコピーして
`IG_ACCESS_TOKEN` のSecretsを手動で上書き保存してください。

## ファイル構成

```
content/
  queue.json          … 投稿予定の記事一覧（キャプション・画像パス・投稿済みフラグ）
  images/              … アイキャッチ画像
scripts/
  generate_eyecatch.py … アイキャッチ画像を生成するスクリプト
  post_daily.py         … キューから次の記事を選んでInstagramに投稿するスクリプト
  refresh_token.py       … アクセストークンを更新するスクリプト
.github/workflows/
  daily-post.yml         … 毎日の自動投稿ワークフロー
  refresh-token.yml       … トークン更新用ワークフロー（手動実行）
```
