"""Tests for the writing index (/writing) and post detail (/writing/{slug}) pages.

Every assertion here is written to fail loudly if the corresponding piece of the
template port regresses. See parallel-writing-report.md for the accidental-pass audit.
"""

import re

POST_SLUGS = [
    "agents-are-distributed-systems",
    "ecs-to-eks-what-i-would-do-differently",
    "the-eval-set-is-the-product",
    "interoperability-is-a-people-problem",
]

POST_TITLES = [
    "Your agent is a distributed system wearing a prompt",
    "ECS to EKS: what I would do differently",
    "The eval set is the product",
    "FHIR is fine. Interoperability is a people problem",
]

POST_DATES = ["12 August 2026", "26 June 2026", "2 May 2026", "18 March 2026"]
POST_READS = ["8 min read", "11 min read", "6 min read", "7 min read"]

# A sentence that exists only in the body of the-eval-set-is-the-product.
EVAL_SENTENCE = (
    "It was twelve hundred de-identified charts scored by clinicians, "
    "with disagreements adjudicated and documented."
)

CANVAS_TOKENS = ["sc-if", "sc-for", "onClick", "onSubmit", "hint-placeholder", 'href="#/']


def _title_text(body: str) -> str:
    m = re.search(r"<title>(.*?)</title>", body, re.S)
    assert m, "no <title> element in response"
    return m.group(1)


def _writing_nav_is_highlighted(body: str) -> bool:
    # The header renders the Writing link with color:var(--color-accent) only when
    # nav_active == 'writing'; otherwise it is color:var(--color-text).
    return bool(
        re.search(
            r'href="/writing"[^>]*color:var\(--color-accent\)[^>]*>\s*Writing\s*</a>',
            body,
        )
    )


# --------------------------------------------------------------------------- #
# Index: /writing
# --------------------------------------------------------------------------- #

def test_writing_index_ok(client):
    assert client.get("/writing").status_code == 200


def test_writing_index_lists_all_four_titles(client):
    body = client.get("/writing").text
    for title in POST_TITLES:
        assert title in body, f"missing post title: {title!r}"


def test_writing_index_has_all_four_post_links(client):
    body = client.get("/writing").text
    for slug in POST_SLUGS:
        assert f'href="/writing/{slug}"' in body, f"missing link for slug: {slug!r}"


def test_writing_index_is_newest_first(client):
    body = client.get("/writing").text
    aug = body.index("/writing/agents-are-distributed-systems")  # 12 August 2026
    mar = body.index("/writing/interoperability-is-a-people-problem")  # 18 March 2026
    assert aug < mar, "August post must appear before the March post"


def test_writing_index_shows_human_dates_and_read_times(client):
    body = client.get("/writing").text
    for date in POST_DATES:
        assert date in body, f"missing human date string: {date!r}"
    for read in POST_READS:
        assert read in body, f"missing read-time string: {read!r}"


def test_writing_index_no_unrendered_jinja(client):
    assert "{{" not in client.get("/writing").text


def test_writing_index_no_canvas_syntax_leaked(client):
    body = client.get("/writing").text
    for token in CANVAS_TOKENS:
        assert token not in body, f"design-canvas token leaked into /writing: {token!r}"


def test_writing_index_nav_highlight(client):
    assert _writing_nav_is_highlighted(client.get("/writing").text)


# --------------------------------------------------------------------------- #
# Detail: /writing/the-eval-set-is-the-product
# --------------------------------------------------------------------------- #

DETAIL_URL = "/writing/the-eval-set-is-the-product"


def test_post_detail_ok(client):
    assert client.get(DETAIL_URL).status_code == 200


def test_post_detail_renders_title(client):
    assert "The eval set is the product" in client.get(DETAIL_URL).text


def test_post_detail_body_is_real_html_not_escaped(client):
    body = client.get(DETAIL_URL).text
    # With `| safe` the pre-rendered body HTML contains bare <p> tags.
    assert "<p>" in body, "body_html was not emitted as raw HTML"
    # Without `| safe` Jinja escapes it and the reader sees literal &lt;p&gt;.
    assert "&lt;p&gt;" not in body, "body_html was HTML-escaped (missing | safe filter)"


def test_post_detail_renders_exact_prose_sentence(client):
    assert EVAL_SENTENCE in client.get(DETAIL_URL).text


def test_post_detail_renders_single_digit_date(client):
    assert "2 May 2026" in client.get(DETAIL_URL).text


def test_post_detail_seo_title_override(client):
    title = _title_text(client.get(DETAIL_URL).text)
    assert "The eval set is the product" in title, f"<title> not overridden: {title!r}"


def test_post_detail_no_unrendered_jinja(client):
    assert "{{" not in client.get(DETAIL_URL).text


def test_post_detail_no_canvas_syntax_leaked(client):
    body = client.get(DETAIL_URL).text
    for token in CANVAS_TOKENS:
        assert token not in body, f"design-canvas token leaked into post page: {token!r}"


def test_post_detail_nav_highlight(client):
    assert _writing_nav_is_highlighted(client.get(DETAIL_URL).text)
