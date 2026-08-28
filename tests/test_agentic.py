"""Tests for the /agentic page.

These assert on prose fragments that appear ONLY in this page's main content
(verified absent from _header.html and _footer.html), so a dropped section
makes the relevant test fail rather than passing for the wrong reason.
"""


def test_agentic_returns_200(client):
    resp = client.get("/agentic")
    assert resp.status_code == 200


def test_agentic_h1_present(client):
    body = client.get("/agentic").text
    assert "Agents that survive production, not just the demo" in body


def test_agentic_opening_copy_present(client):
    body = client.get("/agentic").text
    assert "Agentic AI engagements" in body
    assert (
        "a clinical summarisation engine handling 1.4M notes a month, and a "
        "spec-driven development workflow adopted by 35 engineers" in body
    )
    assert "That is the standard I bring to your build." in body


def test_agentic_figure_caption_present(client):
    body = client.get("/agentic").text
    assert (
        "The shape of every agentic engagement: grounded context in, typed "
        "tool calls out, a human in the loop where it matters" in body
    )


def test_agentic_four_week_path_section_present(client):
    body = client.get("/agentic").text
    assert "A four-week path to something running" in body
    assert "Map the work" in body
    assert "Architecture and evals" in body
    assert "Build the thin slice" in body
    assert "Harden and hand over" in body


def test_agentic_prompt_engineer_section_present(client):
    body = client.get("/agentic").text
    assert "What I bring that a prompt engineer does not" in body
    assert (
        "the failure modes of agent orchestration are the failure modes of "
        "event-driven systems with worse error messages" in body
    )


def test_agentic_typical_engagements_section_present(client):
    body = client.get("/agentic").text
    assert "Typical engagements" in body
    assert "Internal copilot over your own data" in body
    assert (
        "The pattern behind Chartwell: extraction, structured output, "
        "reviewer workflow, measurable time saved." in body
    )


def test_agentic_architecture_sprint_cta_present(client):
    body = client.get("/agentic").text
    assert "Start with the architecture sprint" in body
    assert "Two weeks, fixed price, ends in a build plan you own." in body
    assert "See packages" in body


def test_agentic_no_unrendered_jinja(client):
    body = client.get("/agentic").text
    assert "{{" not in body
    assert "}}" not in body


def test_agentic_no_design_canvas_syntax_leaked(client):
    body = client.get("/agentic").text
    assert "sc-if" not in body
    assert "sc-for" not in body
    assert "onClick" not in body
    assert "hint-placeholder" not in body
    assert 'href="#/' not in body


def test_agentic_internal_links_rewritten(client):
    body = client.get("/agentic").text
    # The two closing-CTA buttons are unique to this page's main content, so
    # these fragments prove the "#/services" / "#/contact" rewrite happened
    # here and not merely in the shared header/footer.
    assert (
        'href="/services" class="btn btn-secondary" style="font-size:15px">'
        "See packages</a>" in body
    )
    assert (
        'href="/contact" class="btn btn-primary" style="font-size:15px">'
        "Book a call</a>" in body
    )


def test_agentic_nav_highlight_active(client):
    body = client.get("/agentic").text
    # The Agentic AI nav link must render with the accent colour on this page.
    assert 'color:var(--color-accent)">Agentic AI</a>' in body
    # And a non-active link stays on the default text colour.
    assert 'color:var(--color-text)">Work</a>' in body
