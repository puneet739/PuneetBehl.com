def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_openapi_disabled(client):
    assert client.get("/openapi.json").status_code == 404


def test_home_has_chrome(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.text
    assert "PUNEET BEHL" in body
    assert 'href="/work"' in body
    assert 'href="/contact"' in body
    assert "© 2026 Puneet Behl" in body
    assert "{{" not in body  # no unrendered vars


def test_static_css_served(client):
    r = client.get("/static/css/styles.css")
    assert r.status_code == 200
    assert "--color-accent" in r.text


def test_plates_filters_reach_page(client):
    # The print-plate SVG partial must be inlined and non-empty — a silently
    # empty _plates.svg would still render a valid page, so assert the real
    # filter ids are present in the served HTML.
    body = client.get("/").text
    assert 'id="sep-all"' in body
    assert 'id="sep-c"' in body
    assert 'id="sep-k"' in body
    assert "feColorMatrix" in body


def test_header_nav_active_colouring(client):
    # Home has no active nav item, so every nav link uses --color-text, and
    # the accent-active branch must not leak onto the home page.
    home = client.get("/").text
    assert "var(--color-text)" in home
    assert "nav_active" not in home  # loop/if variable fully resolved

    home_work_link = (
        'href="/work" class="und" style="font-size:14px;color:var(--color-text)">Work</a>'
    )
    accent_work_link = (
        'href="/work" class="und" style="font-size:14px;color:var(--color-accent)">Work</a>'
    )
    # On the home page the Work link is NOT accented.
    assert home_work_link in home
    assert accent_work_link not in home

    # On /work the active-nav {% if nav_active == 'work' %} branch really fires:
    # the Work link renders with the accent colour, and no longer with --color-text.
    work = client.get("/work").text
    assert accent_work_link in work
    assert home_work_link not in work


def test_footer_newsletter_form_wired(client):
    body = client.get("/").text
    assert 'action="/subscribe"' in body
    assert 'method="post"' in body
    assert 'name="website"' in body  # honeypot
    assert 'name="ts"' in body
    assert 'name="from"' in body


def test_footer_subscribed_panel(client):
    body = client.get("/?subscribed=1").text
    assert "Subscribed" in body
    assert 'action="/subscribe"' not in body  # form hidden when subscribed


def test_static_site_css_served(client):
    r = client.get("/static/css/site.css")
    assert r.status_code == 200
    assert ".hp" in r.text


def test_site_js_stub_served(client):
    r = client.get("/static/js/site.js")
    assert r.status_code == 200
    assert "classList.add('js')" in r.text


def test_favicon_served(client):
    r = client.get("/static/favicon.svg")
    assert r.status_code == 200
    assert "<svg" in r.text


import re  # noqa: E402
from urllib.parse import urljoin  # noqa: E402

# Pages that are routable today. Tasks 5–12 add routes; extend this list so the
# asset-resolution guard below automatically covers them.
ROUTABLE_PAGES = [
    "/",
    "/work",
    "/work/loaderhouse",
    "/agentic",
    "/services",
    "/about",
    "/writing",
    "/writing/the-eval-set-is-the-product",
]

_SKIP_REF_PREFIXES = ("data:", "http://", "https://", "//", "mailto:", "tel:", "#")


def _html_static_refs(html, page_path):
    """Asset URLs a browser would fetch for a page served at ``page_path``.

    Collects every ``src="…"`` (img/script/iframe) and ``href="…"`` on ``<link>``
    elements only — stylesheets and icons — and resolves each the way a browser
    would, against the requesting page's URL. References are collected whether or
    not they are already ``/static/``-prefixed, so a malformed ``src="assets/x"``
    resolves to ``/assets/x`` and is caught as a 404.

    ``<a href>`` navigation is deliberately excluded: routes like /work, /contact
    and /agentic are built by later tasks and legitimately 404 today.
    """
    raw = re.findall(r'\ssrc="([^"]+)"', html)
    raw += re.findall(r'<link\b[^>]*?\shref="([^"]+)"', html)
    refs = set()
    for val in raw:
        val = val.strip()
        if not val or val.startswith(_SKIP_REF_PREFIXES):
            continue
        refs.add(urljoin(page_path, val))
    return refs


def _css_url_refs(css_text, base_dir="/static/css/"):
    """url(...) targets from a stylesheet served under base_dir, resolved the way a
    browser would: root-relative kept as-is, otherwise joined onto base_dir."""
    refs = set()
    for m in re.finditer(r"""url\(\s*['"]?([^'")]+?)['"]?\s*\)""", css_text):
        val = m.group(1).strip()
        if val.startswith(("data:", "http://", "https://", "//")):
            continue
        refs.add(val if val.startswith("/") else base_dir + val)
    return refs


def test_referenced_static_assets_resolve(client):
    # Regression guard: nothing else asserts that a *referenced* asset actually
    # resolves. Extract every /static/ reference from each routable page plus
    # every url(...) in the served site.css, then fetch each one.
    refs = set()
    for page in ROUTABLE_PAGES:
        r = client.get(page)
        assert r.status_code == 200, f"page {page!r} did not load ({r.status_code})"
        refs |= _html_static_refs(r.text, page)

    css = client.get("/static/css/site.css")
    assert css.status_code == 200
    refs |= _css_url_refs(css.text)

    assert len(refs) >= 12, (
        f"only extracted {len(refs)} asset references ({sorted(refs)}) — the "
        f"extractor is broken; this test must not pass vacuously"
    )

    failures = [
        f"{client.get(u).status_code} {u}"
        for u in sorted(refs)
        if client.get(u).status_code != 200
    ]
    assert not failures, "referenced static assets that 404:\n" + "\n".join(failures)


def test_home_content(client):
    body = client.get("/").text
    assert "I design distributed systems that stay up" in body
    assert "50M+" in body
    assert "Selected work" in body
    # featured projects present with real links
    assert 'href="/work/loaderhouse"' in body
    assert 'href="/work/kubestat"' in body
    assert "Ravi Menon" in body
    assert 'href="/contact"' in body


def test_home_stat_values_all_render(client):
    # The four home stats come from site.yaml home_stats, rendered via a loop.
    # If the loop broke or a value went missing, one of these would vanish.
    body = client.get("/").text
    for value in ("50M+", "99.99%", "60%", "35"):
        assert value in body, f"missing home stat value {value!r}"
    # Each stat numeral is echoed by the paper span plus three CMYK plate spans
    # for the misregister effect — assert all four spans exist for one value.
    assert body.count('>50M+<') >= 4, "cmyk-num needs paper + 3 plate spans per value"


def test_home_featured_projects_in_yaml_order(client):
    # featured_projects() returns projects[0], [2], [1], [4] from projects.yaml
    # (loaderhouse, relayd, chartwell, kubestat). A wrong index would silently
    # surface the wrong project, so pin every slug's link.
    body = client.get("/").text
    for slug in ("loaderhouse", "relayd", "chartwell", "kubestat"):
        assert f'href="/work/{slug}"' in body, f"missing featured link for {slug}"
    # northgate-rails is projects[3] and must NOT be featured on the home page
    assert 'href="/work/northgate-rails"' not in body
    # links appear in featured order
    order = [
        body.index('href="/work/loaderhouse"'),
        body.index('href="/work/relayd"'),
        body.index('href="/work/chartwell"'),
        body.index('href="/work/kubestat"'),
    ]
    assert order == sorted(order), "featured project links out of expected order"


def test_home_testimonial_from_site_yaml(client, app):
    # Prove the testimonial is wired to site.testimonial and not left as the
    # design's hard-coded markup: swap in a sentinel author, then require the
    # sentinel to appear and the real author to be gone.
    orig = app.state.content
    sentinel = "Q. A. Sentinel — Verification Bot, Nowhere Inc"
    patched_site = orig.site.model_copy(
        update={"testimonial": orig.site.testimonial.model_copy(update={"author": sentinel})}
    )
    app.state.content = orig.model_copy(update={"site": patched_site})

    body = client.get("/").text
    assert sentinel in body, "testimonial author is not rendered from site.testimonial"
    assert "Ravi Menon" not in body, "design's hard-coded testimonial author still present"
    assert "the payments core has not had a Sev-1" in body


# ---------------------------------------------------------------------------
# Task 5: /work index and /work/{slug} project detail pages
# ---------------------------------------------------------------------------


def test_work_index(client):
    body = client.get("/work").text
    assert client.get("/work").status_code == 200
    for slug in ["loaderhouse", "chartwell", "relayd", "northgate-rails",
                 "kubestat", "tenderfoot", "specflow", "anchor-cli"]:
        assert f'href="/work/{slug}"' in body
    assert "Agentic AI" in body  # a filter label


def test_project_detail(client):
    r = client.get("/work/northgate-rails")
    assert r.status_code == 200
    assert "Northgate Rails" in r.text
    assert "50M+" in r.text
    assert "append-only" in r.text  # from problem/approach text


def test_project_detail_unknown_is_404(client):
    r = client.get("/work/does-not-exist")
    assert r.status_code == 404
    assert "text/html" in r.headers["content-type"]


def test_work_index_filter_labels_come_from_project_types(client):
    # Filter buttons are data-derived via project_types() in first-seen order —
    # NOT the design's hard-coded FILTERS array, which orders App before
    # Agentic AI. Pin the exact data-derived order and rendered markup.
    body = client.get("/work").text
    labels = re.findall(
        r'<button type="button" class="tag filter-btn(?: is-active)?" '
        r'aria-pressed="(?:true|false)" data-filter="([^"]+)">\1</button>',
        body,
    )
    assert labels == ["All", "Website", "Agentic AI", "Platform", "App", "Open source"]


def test_work_cards_carry_client_filter_hooks(client):
    # Task 14's client-side filter depends on BOTH hooks on every card.
    body = client.get("/work").text
    assert body.count('class="g-row work-card lift"') == 8
    assert 'data-type="Website"' in body        # loaderhouse
    assert 'data-type="Platform"' in body       # northgate-rails
    assert 'data-type="Open source"' in body    # anchor-cli
    assert body.count('data-type="Agentic AI"') == 3  # chartwell, relayd, specflow


def test_work_index_renders_all_eight_cards_with_stack_and_summary(client):
    body = client.get("/work").text
    # exactly one "/work/{slug}" card link per project; header/footer link to
    # "/work" (no trailing slash) so they are not counted here.
    assert body.count('href="/work/') == 8
    # loaderhouse summary prose (rendered from the projects loop, not hard-coded)
    assert "A freight load board for mid-size Indian carriers" in body
    # per-card stack chips
    assert "Spring Boot" in body and "Cassandra" in body
    # headline column
    assert "50M+ requests a day at 99.99%" in body  # northgate-rails headline


def test_project_detail_unique_content(client):
    # Content that exists ONLY on northgate-rails; a stub or the wrong project
    # would fail each of these.
    body = client.get("/work/northgate-rails").text
    assert "synchronous writes across four databases inside the request path" in body  # problem
    assert "Kafka as the event backbone with schema" in body  # architecture prose
    assert "month-end close, down from 3 days" in body  # a metric label
    assert "6 hrs" in body                              # its metric value
    assert body.count("Cassandra") >= 2                 # stack chips + request-path row
    assert "freight load board" not in body             # sibling prose must not leak


def test_project_detail_next_link_is_cyclic(client):
    # anchor-cli is projects[7] (last); its "next" wraps to projects[0] loaderhouse.
    body = client.get("/work/anchor-cli").text
    assert 'href="/work/loaderhouse"' in body
    assert "Next: Loaderhouse" in body
    # loaderhouse -> chartwell
    body2 = client.get("/work/loaderhouse").text
    assert 'href="/work/chartwell"' in body2
    assert "Next: Chartwell Summary" in body2


def test_project_detail_has_back_to_work_and_metrics_loop(client):
    body = client.get("/work/kubestat").text
    assert 'href="/work"' in body
    assert "All work" in body
    # all three kubestat metric values from the metrics loop
    for value in ("31%", "340", "11"):
        assert value in body
    assert "average cluster spend removed" in body  # a metric label


def test_project_detail_no_unrendered_vars(client):
    body = client.get("/work/relayd").text
    assert "{{" not in body
    assert "nextProject" not in body  # design var name fully converted
    assert "artAlt" not in body


def test_404_unknown_slug_renders_html_page_not_json(client):
    r = client.get("/work/nope")
    assert r.status_code == 404
    assert "text/html" in r.headers["content-type"]
    assert "application/json" not in r.headers["content-type"]
    assert '"detail"' not in r.text          # not the default JSON body
    assert "That page doesn" in r.text       # 404.html copy
    assert "PUNEET BEHL" in r.text           # rendered with full site chrome
    assert "{{" not in r.text


def test_404_unknown_top_level_path(client):
    r = client.get("/nonsense")
    assert r.status_code == 404
    assert "text/html" in r.headers["content-type"]
    assert "Not found" in r.text
    assert "PUNEET BEHL" in r.text
    assert '"detail"' not in r.text


def test_404_unknown_nested_post_style_path(client):
    # Future /writing/{slug} territory: still the HTML 404, never a JSON detail.
    r = client.get("/writing/does-not-exist")
    assert r.status_code == 404
    assert "text/html" in r.headers["content-type"]
    assert '"detail"' not in r.text
    assert "That page doesn" in r.text


# ---------------------------------------------------------------------------
# Phase 1: placeholder routes for /agentic, /services, /about, /writing,
# /writing/{slug} — real page markup is ported by follow-on agents.
# ---------------------------------------------------------------------------


def test_new_placeholder_routes_return_200(client):
    for path in [
        "/agentic",
        "/services",
        "/about",
        "/writing",
        "/writing/the-eval-set-is-the-product",
    ]:
        r = client.get(path)
        assert r.status_code == 200, f"{path} returned {r.status_code}"
        assert "text/html" in r.headers["content-type"]


def test_writing_unknown_slug_is_html_404(client):
    r = client.get("/writing/no-such-post")
    assert r.status_code == 404
    assert "text/html" in r.headers["content-type"]
    assert "application/json" not in r.headers["content-type"]
    assert '"detail"' not in r.text


def test_site_js_served(client):
    r = client.get("/static/js/site.js")
    assert r.status_code == 200
    assert "IntersectionObserver" in r.text


def test_work_cards_have_filter_hooks(client):
    body = client.get("/work").text
    assert 'class="g-row work-card' in body
    assert 'data-type="Agentic AI"' in body


def test_forms_are_progressively_enhanced(client):
    for path in ["/contact", "/interviews"]:
        assert "data-ajax" in client.get(path).text


def test_pages_render_without_js(client):
    # .reveal starts visible; only site.js adding .js to <html> hides it first.
    css = client.get("/static/css/site.css").text
    assert ".reveal { opacity: 1; }" in css
    assert ".js .reveal:not(.in)" in css
