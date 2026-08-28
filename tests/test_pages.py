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
    body = client.get("/").text
    assert "var(--color-text)" in body
    assert "nav_active" not in body  # loop/if variable fully resolved


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
ROUTABLE_PAGES = ["/"]

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
