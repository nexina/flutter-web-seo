# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-24

### Added
- `build`: per-route static shells from a built Flutter `index.html` (title,
  meta description, canonical, Open Graph, Twitter, JSON-LD, visually-hidden
  `#seo-content`, boot-title text, noscript fallback), plus `sitemap.xml`
  (lastmod from git) and `robots.txt`.
- `validate`: title length, meta description length, uniqueness, path and
  sitemap rules, output re-check.
- `indexnow`: submit URLs to IndexNow (with `--dry-run`).
- Examples: Flutter demo app, `routes.json`, nginx config, GitHub Actions deploy.
