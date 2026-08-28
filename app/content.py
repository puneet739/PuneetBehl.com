from __future__ import annotations

import datetime as dt
from pathlib import Path

import frontmatter
import yaml
from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
_md = MarkdownIt("commonmark", {"typographer": True}).enable(["replacements", "smartquotes"])


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class Metric(_Frozen):
    value: str
    label: str


class Project(_Frozen):
    slug: str
    name: str
    mono: str
    domain: str
    type: str
    year: str
    role: str
    tint: str
    headline: str
    summary: str
    problem: str
    architecture: str
    approach: list[str]
    metrics: list[Metric]
    stack: list[str]


class Package(_Frozen):
    kicker: str
    name: str
    price: str
    terms: str
    blurb: str
    cta: str
    items: list[str]


class Role(_Frozen):
    years: str
    title: str
    company: str
    note: str


class Post(_Frozen):
    slug: str
    title: str
    excerpt: str
    read: str
    date: dt.date
    body_html: str

    @property
    def date_display(self) -> str:
        d = self.date
        return f"{d.day} {d.strftime('%B %Y')}"


class Testimonial(_Frozen):
    quote: str
    author: str


class HomeStat(_Frozen):
    value: str
    label: str


class SiteConfig(_Frozen):
    tagline_role: str
    availability_short: str
    availability_long: str
    email: str
    phone: str
    linkedin: str
    github: str
    location: str
    footer_blurb: str
    credentials: str
    testimonial: Testimonial
    home_stats: list[HomeStat]


class Content(_Frozen):
    site: SiteConfig
    projects: list[Project]
    packages: list[Package]
    roles: list[Role]
    skills: list[str]
    posts: list[Post]


def _read_yaml(path: Path):
    with path.open() as fh:
        return yaml.safe_load(fh)


def load_content(root: Path = CONTENT_DIR) -> Content:
    root = Path(root)
    site = SiteConfig(**_read_yaml(root / "site.yaml"))
    projects = [Project(**p) for p in _read_yaml(root / "projects.yaml")]
    packages = [Package(**p) for p in _read_yaml(root / "packages.yaml")]
    roles = [Role(**r) for r in _read_yaml(root / "roles.yaml")]
    skills = list(_read_yaml(root / "skills.yaml"))

    posts: list[Post] = []
    writing_dir = root / "writing"
    md_files = sorted(writing_dir.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"no posts in {writing_dir}")
    for md_path in md_files:
        fm = frontmatter.load(md_path)
        d = fm["date"]
        if isinstance(d, str):
            d = dt.date.fromisoformat(d)
        posts.append(
            Post(
                slug=fm.get("slug", md_path.stem),
                title=fm["title"],
                excerpt=fm["excerpt"],
                read=fm["read"],
                date=d,
                body_html=_md.render(fm.content),
            )
        )
    posts.sort(key=lambda p: p.date, reverse=True)

    return Content(
        site=site,
        projects=projects,
        packages=packages,
        roles=roles,
        skills=skills,
        posts=posts,
    )


_content: Content | None = None


def get_content() -> Content:
    global _content
    if _content is None:
        _content = load_content()
    return _content


def get_project(slug: str) -> Project | None:
    return next((p for p in get_content().projects if p.slug == slug), None)


def get_post(slug: str) -> Post | None:
    return next((p for p in get_content().posts if p.slug == slug), None)


def featured_projects() -> list[Project]:
    p = get_content().projects
    return [p[0], p[2], p[1], p[4]]


def project_types() -> list[str]:
    seen: list[str] = []
    for pr in get_content().projects:
        if pr.type not in seen:
            seen.append(pr.type)
    return ["All"] + seen
