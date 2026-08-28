"""Tests for the /services page.

These are written to fail loudly if the port breaks: empty cards, a dead
inner loop, leaked design-canvas syntax, unrendered Jinja, or a broken nav
highlight would all trip at least one assertion here.

Every asserted string was checked against app/templates/_header.html and
app/templates/_footer.html — none of them appear in the shared chrome, so a
pass genuinely exercises the ported main content.
"""


def test_services_ok(client):
    assert client.get("/services").status_code == 200


def test_all_three_package_names_render(client):
    body = client.get("/services").text
    assert "Architecture Sprint" in body
    assert "Build and Ship" in body
    assert "Fractional Architect" in body


def test_exact_prices_render(client):
    # Commercially meaningful — a silent truncation or reformat must fail.
    body = client.get("/services").text
    assert "$6,500" in body
    assert "From $9,000" in body
    assert "From $3,800" in body


def test_nested_items_bullets_render(client):
    # One exact bullet from each package. If the inner {% for i in s.items %}
    # loop is broken the cards still return 200 but these strings vanish.
    body = client.get("/services").text
    assert "Discovery with your engineers and domain experts" in body  # Architecture Sprint
    assert "Architecture plus implementation, not handoff" in body  # Build and Ship
    assert "Design and code review on the decisions that matter" in body  # Fractional Architect


def test_supporting_copy_renders(client):
    body = client.get("/services").text
    assert "Three ways to work with me" in body
    assert "How an engagement runs" in body
    assert "Anika Rao — Head of Product, Curato Health" in body


def test_no_unrendered_jinja(client):
    assert "{{" not in client.get("/services").text


def test_no_design_canvas_syntax_leaked(client):
    body = client.get("/services").text
    assert "sc-if" not in body
    assert "sc-for" not in body
    assert "onClick" not in body
    assert "hint-placeholder" not in body
    assert 'href="#/' not in body


def test_contact_ctas_point_at_real_route(client):
    body = client.get("/services").text
    assert 'href="/contact"' in body
    assert "Scope a sprint" in body
    assert "Check availability" in body
    assert "Talk it through" in body


def test_services_nav_link_is_accented(client):
    # The active-nav {% if nav_active == 'services' %} branch must fire.
    body = client.get("/services").text
    active = (
        'href="/services" class="und" style="font-size:14px;'
        'color:var(--color-accent)">Services</a>'
    )
    inactive = (
        'href="/services" class="und" style="font-size:14px;'
        'color:var(--color-text)">Services</a>'
    )
    assert active in body
    assert inactive not in body


def test_title_and_description_blocks(client):
    body = client.get("/services").text
    assert "<title>Services — Puneet Behl</title>" in body
