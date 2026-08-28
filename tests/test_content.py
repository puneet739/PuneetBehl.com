import datetime as dt
import shutil

import pytest
import yaml
from pydantic import ValidationError

import app.content as content_module
from app.content import (
    CONTENT_DIR,
    get_content,
    get_post,
    get_project,
    featured_projects,
    load_content,
    project_types,
)


@pytest.fixture(scope="module")
def content():
    return get_content()


def test_counts(content):
    assert len(content.projects) == 8
    assert len(content.packages) == 3
    assert len(content.roles) == 6
    assert len(content.posts) == 4
    assert len(content.skills) == 30


def test_project_order(content):
    slugs = [p.slug for p in content.projects]
    assert slugs == [
        "loaderhouse",
        "chartwell",
        "relayd",
        "northgate-rails",
        "kubestat",
        "tenderfoot",
        "specflow",
        "anchor-cli",
    ]


def test_project_fields_verbatim(content):
    p = content.projects[0]
    assert p.name == "Loaderhouse"
    assert p.mono == "LH"
    assert p.domain == "loaderhouse.com"
    assert p.type == "Website"
    assert p.year == "2026"
    assert p.role == "Architect and lead engineer"
    assert p.tint == "var(--color-accent)"
    assert p.headline == "3.1M loads matched a year"
    assert p.metrics[0].value == "240ms"
    assert p.metrics[0].label == "p95 search latency, down from 11s"
    assert p.metrics[2].value == "3.1M"
    assert len(p.approach) == 4
    assert p.approach[0] == (
        "Rebuilt search as a read-optimised projection in Postgres with "
        "Redis-backed geo indexes, taking p95 search latency from 11s to 240ms."
    )
    assert p.stack == [
        "Next.js",
        "Spring Boot",
        "Postgres",
        "Redis",
        "ECS Fargate",
        "Terraform",
    ]
    # em-dash preserved in summary
    assert "—" in p.summary
    # straight apostrophe preserved verbatim (source uses ASCII ')
    assert "truck's route" in p.summary


def test_non_ascii_symbols_preserved(content):
    chartwell = get_project("chartwell")
    # cent sign in a metric value must survive transcription
    assert chartwell.metrics[2].value == "0.9¢"
    # middle-dot separator in a domain field
    assert chartwell.domain == "Healthcare SaaS · internal product"


def test_get_project(content):
    assert get_project("chartwell").name == "Chartwell Summary"
    assert get_project("anchor-cli").headline == "1,240 stars, 40-minute bootstrap"
    assert get_project("nope") is None


def test_packages(content):
    pkg = content.packages[0]
    assert pkg.kicker == "Fixed price · 2 weeks"
    assert pkg.name == "Architecture Sprint"
    assert pkg.price == "$6,500"
    assert pkg.terms == "or ₹5.4L · two weeks, one architect"
    assert pkg.cta == "Scope a sprint"
    assert len(pkg.items) == 4
    assert content.packages[1].name == "Build and Ship"
    assert content.packages[2].price == "From $3,800"


def test_roles(content):
    r = content.roles[0]
    assert r.years == "Aug 2021 — Aug 2026"
    assert r.title == "Technical Architect / Engineering Manager"
    assert r.company == "AthenaHealth, Bengaluru"
    assert content.roles[-1].company == "Utiba Mobility / Amdocs, Gurgaon"


def test_skills(content):
    assert content.skills[0] == "Java"
    assert content.skills[1] == "Spring Boot"
    assert content.skills[-1] == "Linux"
    assert "HL7 FHIR" in content.skills
    assert "SMART on FHIR" in content.skills


def test_site_config(content):
    site = content.site
    assert site.tagline_role == "Technical Architect · Bengaluru"
    assert site.availability_short == "2 slots · Oct 2026"
    assert site.email == "puneet739@gmail.com"
    assert site.phone == "+91 97116 16135"
    assert site.location == "Bengaluru, India · UTC+5:30"
    assert site.testimonial.author == "Ravi Menon — VP Engineering, Northgate Financial"
    assert site.home_stats[0].value == "50M+"
    assert site.home_stats[1].value == "99.99%"
    assert site.home_stats[3].label == "Engineers across 7 teams on that workflow"
    assert len(site.home_stats) == 4


def test_posts_sorted_desc(content):
    dates = [p.date for p in content.posts]
    assert dates == sorted(dates, reverse=True)
    assert content.posts[0].slug == "agents-are-distributed-systems"
    assert content.posts[0].date == dt.date(2026, 8, 12)
    assert content.posts[-1].slug == "interoperability-is-a-people-problem"
    assert content.posts[-1].date == dt.date(2026, 3, 18)


def test_post_renders_html(content):
    post = get_post("the-eval-set-is-the-product")
    assert post is not None
    assert post.title == "The eval set is the product"
    assert post.read == "6 min read"
    assert post.date == dt.date(2026, 5, 2)
    assert post.date_display == "2 May 2026"
    assert "<p>" in post.body_html
    # 5 body paragraphs -> 5 <p> tags
    assert post.body_html.count("<p>") == 5
    # verbatim phrase from the source body
    assert "twelve hundred de-identified charts scored by clinicians" in post.body_html


def test_post_date_display_no_leading_zero(content):
    post = get_post("interoperability-is-a-people-problem")
    assert post.date_display == "18 March 2026"


def test_get_post_missing():
    assert get_post("nope") is None


def test_featured_order(content):
    slugs = [p.slug for p in featured_projects()]
    assert slugs == ["loaderhouse", "relayd", "chartwell", "kubestat"]


def test_project_types(content):
    types = project_types()
    assert types == ["All", "Website", "Agentic AI", "Platform", "App", "Open source"]


def test_models_are_frozen(content):
    with pytest.raises(ValidationError):
        content.projects[0].name = "mutated"


def test_load_content_raises_on_missing(tmp_path):
    with pytest.raises((FileNotFoundError, ValidationError)):
        load_content(tmp_path)


def test_load_content_raises_validation_error_on_missing_key(tmp_path):
    # A complete, valid tree except site.yaml is missing a required key.
    dst = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, dst)
    site = yaml.safe_load((dst / "site.yaml").read_text())
    del site["email"]
    (dst / "site.yaml").write_text(yaml.safe_dump(site, allow_unicode=True))
    with pytest.raises(ValidationError):
        load_content(dst)


def test_get_content_is_cached_singleton(monkeypatch):
    # get_content() must build the Content once and hand back the same object.
    saved = content_module._content
    try:
        content_module._content = None
        calls = {"n": 0}
        real_load = content_module.load_content

        def counting_load(*args, **kwargs):
            calls["n"] += 1
            return real_load(*args, **kwargs)

        monkeypatch.setattr(content_module, "load_content", counting_load)

        first = get_content()
        second = get_content()
        third = get_content()

        assert calls["n"] == 1
        assert first is second is third
        assert get_content() is get_content()
    finally:
        content_module._content = saved


def test_content_dir_points_at_repo_content():
    assert CONTENT_DIR.name == "content"
    assert (CONTENT_DIR / "site.yaml").exists()
