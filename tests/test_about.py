"""Tests for the /about page.

These assertions are written to genuinely fail if the port breaks:
a truncated roles loop, an unrendered skills loop, leaked design-canvas
syntax, or a broken nav highlight would each trip a specific check below.

Strings were chosen to appear ONLY in the about page's main content, not
in the shared header (_header.html) or footer (_footer.html). In
particular the footer renders site.credentials
("AWS Certified Solutions Architect · CKAD · Certified ScrumMaster"),
so bare "AWS Certified Solutions Architect" is avoided; the intro
paragraphs mention "AthenaHealth", "Java", "Kubernetes", "Hcentive" and
"Utiba" in prose, so the role/skill checks below key on the loop-only
markup (title/company pairings, date ranges, and the
`<span class="tag tag-neutral">` wrappers) instead.
"""


def _body(client):
    resp = client.get("/about")
    assert resp.status_code == 200
    return resp.text


def test_about_returns_200(client):
    assert client.get("/about").status_code == 200


def test_no_unrendered_jinja(client):
    assert "{{" not in _body(client)
    assert "{%" not in _body(client)


def test_no_design_canvas_syntax_leaked(client):
    body = _body(client)
    for token in ("sc-if", "sc-for", "onClick", "onSubmit", "hint-placeholder", 'href="#/'):
        assert token not in body, f"design-canvas token leaked: {token!r}"


def test_page_headings_and_intro_copy(client):
    body = _body(client)
    assert '<h1 style="font-size:46px;margin:0 0 22px">About</h1>' in body
    assert '<h2 style="font-size:26px;margin:0 0 18px">Experience</h2>' in body
    # verbatim owner copy (British spelling "summarisation" must survive)
    assert "clinical summarisation engine that cut record-review time 35%" in body
    assert "migrated production workloads from ECS to EKS by hand" in body


def test_all_six_roles_render_with_title_and_company(client):
    body = _body(client)
    # (distinctive title fragment, company string) for each of the 6 roles
    pairs = [
        ("Technical Architect / Engineering Manager", "AthenaHealth, Bengaluru"),
        ("Lead Member Technical Staff", "AthenaHealth, Bengaluru"),
        ("Senior Software Engineer", "Hcentive, Noida"),
        ("Team Lead", "Sapient Global Markets, Gurgaon"),
        ("Senior Software Engineer", "Nagarro, Gurgaon"),
        ("Java Software Engineer", "Utiba Mobility / Amdocs, Gurgaon"),
    ]
    for title, company in pairs:
        assert title in body, f"missing role title: {title!r}"
        assert company in body, f"missing role company: {company!r}"

    # both AthenaHealth rows must be present and distinct
    assert body.count("AthenaHealth, Bengaluru") == 2
    # "Senior Software Engineer" is the title for two different companies
    assert body.count("Senior Software Engineer") == 2


def test_role_notes_render(client):
    body = _body(client)
    fragments = [
        "the spec-driven\nworkflow adopted by 35 engineers. Managed a team of ten.".replace("\n", " "),
        "HLD\nand LLD, microservices and event-driven patterns".replace("\n", " "),
        "mobile micro-financial product",
        "low-latency capital-markets platform",
        "Built the seller panel from scratch on Spring Boot",
        "role-based access control and JUnit test suites on\nenterprise telecom".replace("\n", " "),
    ]
    for frag in fragments:
        assert frag in body, f"missing role note fragment: {frag!r}"


def test_role_date_ranges_render_with_em_dash(client):
    body = _body(client)
    ranges = [
        "Aug 2021 — Aug 2026",
        "Aug 2018 — Aug 2021",
        "Jul 2016 — Aug 2018",
        "Dec 2014 — Jul 2016",
        "Feb 2014 — Dec 2014",
        "Jan 2010 — Feb 2014",
    ]
    for r in ranges:
        assert r in body, f"missing date range: {r!r}"
    # sanity: the em-dash, not a hyphen, is what shipped
    assert "Aug 2021 - Aug 2026" not in body


def test_skills_render_as_neutral_tags(client):
    body = _body(client)
    for skill in ("Java", "Spring Boot", "HL7 FHIR", "Kubernetes"):
        assert f'<span class="tag tag-neutral">{skill}</span>' in body, (
            f"missing skill tag: {skill!r}"
        )
    # loop-only skills (these strings appear nowhere else on the page)
    for skill in ("Spring Cloud", "SMART on FHIR", "CloudFormation", "OpenSearch"):
        assert f'<span class="tag tag-neutral">{skill}</span>' in body, (
            f"missing skill tag: {skill!r}"
        )
    # all 30 skills must render, not just the first
    assert body.count("tag-neutral") >= 30, body.count("tag-neutral")


def test_aside_static_blocks_render(client):
    body = _body(client)
    assert "AWS Certified Solutions Architect — Associate" in body
    assert "Certified Kubernetes Application Developer (CKAD)" in body
    assert "AI Leader — AthenaHealth, 2026" in body
    assert "Exceptional Delivery — Utiba, 2012" in body
    assert ">Stack</h3>" in body
    assert ">Certifications</h3>" in body
    assert ">Awards</h3>" in body
    assert ">Speaking</h3>" in body


def test_hash_links_rewritten_to_real_paths(client):
    body = _body(client)
    assert '<a href="/contact">Get in touch</a>' in body
    assert "#/contact" not in body


def test_nav_highlight_active_on_about(client):
    body = _body(client)
    # the About nav link renders in the accent colour when active
    assert (
        '<a href="/about" class="und" style="font-size:14px;color:var(--color-accent)">About</a>'
        in body
    )
    # a non-active link stays on the text colour
    assert (
        '<a href="/work" class="und" style="font-size:14px;color:var(--color-text)">Work</a>'
        in body
    )
    # var(--color-accent) with a closing paren appears exactly once (the About link);
    # var(--color-accent-700) etc. do not match this substring
    assert body.count("color:var(--color-accent)") == 1
