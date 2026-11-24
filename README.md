# flutter-web-seo

Make Flutter web apps indexable. A small, dependency-free Python CLI that turns
a built Flutter `index.html` plus a JSON routes file into **one static HTML
shell per URL**, with the right `<title>`, meta tags, canonical, JSON-LD and
real page text, plus `sitemap.xml`, `robots.txt`, validation and IndexNow.

```
routes.json  +  build/web/index.html   ->   build/web/word-counter/index.html
                                            build/web/sitemap.xml, robots.txt ...
```

## The problem

A Flutter web app is one HTML file that loads a JavaScript (or WebAssembly)
bundle and draws everything on a `<canvas>`. A crawler that does not run that
bundle sees an empty page, and one that does sees pixels, not text. Every URL
has the same `<title>`, no meta description, no canonical and nothing to
quote. Many AI crawlers and link-preview bots do not execute JavaScript at all.

## How it works

1. You mark two places in `web/index.html` with comments (`SEO_HEAD`,
   `SEO_CONTENT`) and give the splash text an id (`boot-title`).
2. You describe each route in `routes.json`: title, description, h1, body,
   FAQ, breadcrumbs, og image.
3. After `flutter build web`, `flutter-web-seo build` takes the built
   `index.html` as the template and writes `<route>/index.html` for every
   route. Each file is the **same Flutter bundle** with that route's head tags
   and a text version of the page inside `#seo-content`.
4. Your web server serves `/word-counter` from `word-counter/index.html`.
   Crawlers read the HTML; browsers boot Flutter, which takes over.

### Why `#seo-content` is visually hidden, not `display:none`

The content is hidden with the usual "screen-reader-only" technique (1px box,
`clip`, `overflow:hidden`), never `display:none`, `visibility:hidden` or the
`hidden` attribute. Content that is not rendered at all is what search engines
may discount, and it is invisible to assistive technology. A clipped box is
still rendered and still read aloud. With JavaScript off (`<noscript>`) the
same block is revealed in full, so the shell is also a usable fallback page.
Keep the hidden text **identical in substance** to what the app shows; text
that differs from the visible page is cloaking.

## Quick start

```bash
pip install flutter-web-seo           # or: git+https://github.com/nexina/flutter-web-seo
```

**1. Add markers to `web/index.html`:**

```html
<head>
  <base href="/">
  <!-- SEO_HEAD_START -->
  <title>My app</title>
  <!-- SEO_HEAD_END -->
</head>
<body>
  <div id="boot-splash"><p id="boot-title">My app</p></div>
  <!-- SEO_CONTENT_START -->
  <div id="seo-content" class="visually-hidden"></div>
  <!-- SEO_CONTENT_END -->
  <script src="flutter_bootstrap.js" async></script>
</body>
```

Use `usePathUrlStrategy()` (from `flutter_web_plugins`) so your routes are
real paths, not `#/fragments`. See [`examples/flutter_demo`](examples/flutter_demo).

**2. Write `routes.json`** (see [`examples/routes.json`](examples/routes.json)).

**3. Build and generate:**

```bash
flutter build web --release
flutter-web-seo build --config routes.json --template build/web/index.html --strict
```

Run it from your repository (not a shallow clone) so `lastmod` can read git
history. The command validates first, writes the shells into the template's
directory (or `--out`), then re-checks what it wrote. It is idempotent: it
can run again on its own output.

## Config reference

```jsonc
{
  "site": {
    "url": "https://example.com",       // required: https origin, no path
    "name": "Example",                  // og:site_name, WebSite in JSON-LD
    "default_og_image": "/og/default.png",  // absolute or site-relative
    "locale": "en_US",
    "twitter_site": "@handle",          // optional
    "application_category": "UtilitiesApplication",
    "operating_system": "Web",
    "offer": {"price": "0", "currency": "USD"},  // set to null for no "offers"
    "faq_heading": "Frequently asked questions",
    "related_heading": "Related",
    "home_breadcrumb": "Home",
    "indexnow_key": "",                 // optional; build writes <key>.txt
    "robots": {"disallow": ["/admin"], "extra": []}
  },
  "routes": [
    {
      "path": "/word-counter",          // required; lower case, no trailing slash
      "title": "...",                   // <= 60 chars
      "description": "...",             // 120-160 chars
      "h1": "Word counter",             // defaults to title
      "body": "markdown-lite",          // or "body_html": "<p>trusted html</p>"
      "faq": [{"q": "...", "a": "markdown-lite"}],
      "breadcrumbs": [{"name": "Tools", "path": "/tools"}],  // ancestors only
      "items": [{"name": "...", "path": "/x", "description": "..."}],  // ItemList + link list
      "schema": "WebApplication",       // WebApplication | SoftwareApplication | WebPage (default) | none
      "og_image": "/og/word-counter.png",
      "boot_title": "...",              // splash text; defaults to h1
      "noindex": false,                 // adds robots noindex, leaves it out of the sitemap
      "sitemap": true,
      "lastmod": "2026-01-31",          // overrides git
      "sources": ["lib/pages/word.dart"] // files whose git date becomes lastmod
    }
  ]
}
```

**Breadcrumbs:** Home and the current page are added for you; `breadcrumbs`
lists only the ancestors in between. `false` turns them off. The root route
has none.

**Markdown-lite:** paragraphs, `##`-`####` headings, `-` and `1.` lists,
`**bold**`, `*italic*`, `` `code` ``, `[text](url)`. Everything is HTML-escaped;
links must be `http(s)`, `mailto:`, `/path` or `#anchor`.

**What a shell contains:** `<title>`, meta description, canonical (no trailing
slash; the root keeps `/`), Open Graph, Twitter card, JSON-LD
(`WebApplication`/`SoftwareApplication`/`WebPage`, `BreadcrumbList`,
`FAQPage`, `ItemList`), the visually-hidden `#seo-content`, the boot-title
text, and a `<noscript>` fallback. The template's own default `<title>`,
description, canonical and og/twitter tags are removed so nothing is duplicated.

**lastmod:** the date of the last git commit that touched the route's
`sources` (default: the routes file). It is never the build date, because a
`lastmod` that is always "today" teaches search engines to ignore it. No git
history means no `<lastmod>`.

## nginx

[`examples/nginx/example.conf`](examples/nginx/example.conf) does the parts
that make the shells work in practice:

- `/path/` gets a `301` to `/path` (one canonical URL);
- `try_files $uri $uri/index.html =404` serves each shell and returns a
  **real 404** for unknown paths (a catch-all to `index.html` creates soft 404s);
- `X-Robots-Tag: noindex` on `.js`/`.wasm`/`.map` so bundles do not show up in results.

## Validation

```bash
flutter-web-seo validate --config routes.json            # config rules
flutter-web-seo validate --config routes.json --out build/web --strict   # + built output
```

| Rule | Level |
|---|---|
| title present and <= 60 chars; unique across routes | error |
| meta description 120-160 chars; unique across routes | error |
| path lower case, starts with `/`, no trailing slash, no duplicates | error |
| `site.url` is an https origin | error |
| sitemap: on site origin, no trailing slash (except `/`), no query, lower case, unique, `lastmod` is `YYYY-MM-DD`, a shell file exists for each URL | error |
| built shells: one `<title>`, canonical matches, `#seo-content` present, JSON-LD parses | error |
| thin body (< 40 words), breadcrumb/item pointing at an unknown route, no og image anywhere | warning |

`--strict` turns warnings into failures. Exit codes: `0` ok, `1` problems, `2`
bad usage or unreadable config.

## IndexNow

```bash
# the key is a public file at https://example.com/<key>.txt
export INDEXNOW_KEY=my-indexnow-key
flutter-web-seo indexnow --config routes.json --dry-run
flutter-web-seo indexnow --config routes.json                  # after deploying
flutter-web-seo indexnow --config routes.json --sitemap build/web/sitemap.xml
```

Setting `site.indexnow_key` makes `build` write the `<key>.txt` file for you.
Submit **after** the pages and key file are live. Bing, Yandex and others
accept IndexNow; Google does not, so keep the sitemap submitted in Search Console.

## FAQ

**Does this server-side render Flutter?** No. It writes static text next to
the app. The visible UI is still the canvas.

**Will Google treat the hidden text as cloaking?** Not if it matches what the
page shows and is not hidden from everyone (see above). Write the `body` as
the page's real content, not keywords.

**Can I use hash URLs (`#/path`)?** No. Crawlers drop the fragment. Use
`usePathUrlStrategy()`.

**Where do the route texts come from?** Anywhere: write `routes.json` by
hand, or generate it from your CMS, a database or Dart constants in an earlier
CI step.

**Do I need `--no-wasm`?** No. The shells do not depend on the renderer.

## Limitations

- Content is static: changing text means regenerating and redeploying.
- You maintain the hidden text and the Flutter UI separately; nothing checks
  that they agree.
- No dynamic routes (`/user/123`); list every URL you want indexed.
- No image generation for og images, and no localisation / hreflang yet.
- The template must keep the marker comments through your build tooling.
- Flutter's service worker may serve a cached shell after a deploy; the app's
  own route, not the shell, is the source of truth once it has booted.

## Who uses this

Used in production by TypeorDrop (https://www.typeordrop.com) - free online file tools.

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md). MIT, see [LICENSE](LICENSE).
