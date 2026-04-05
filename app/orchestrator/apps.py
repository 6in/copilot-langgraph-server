"""Application Package Registry — APP-01.

AppRegistry scans an apps/ directory for APP.md files, parses their YAML frontmatter,
and returns AppDefinition objects. This is metadata-only — no ChatCopilot instantiation
and no GitHub token required at startup (D-07/D-08 REVISED).

Design rationale:
  The GitHub Copilot token is per-user (acquired via Device Flow). ChatCopilot cannot
  be instantiated at server startup before any user has authenticated. AppRegistry only
  reads frontmatter, which is safe at startup with no credentials.
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter as fm

logger = logging.getLogger(__name__)


@dataclass
class AppDefinition:
    """Parsed representation of a single APP.md package file."""

    slug: str                      # Directory name (e.g. "chat", "superchat")
    name: str                      # Frontmatter: name
    description: str               # Frontmatter: description
    icon: str                      # Frontmatter: icon (emoji or text)
    agents: list[str] = field(default_factory=list)  # Frontmatter: agents[]


class AppRegistry:
    """Scans apps_dir for APP.md files and builds an in-memory registry.

    Usage:
        registry = AppRegistry("./apps")
        apps = registry.all()                  # -> list[AppDefinition]
        app  = registry.get("chat")            # -> AppDefinition | None
        names = registry.get_agent_names("chat")  # -> list[str]

    Thread-safety: read-only after __init__, safe for concurrent access.
    """

    def __init__(self, apps_dir: str) -> None:
        self.apps_dir = Path(apps_dir)
        self.apps: dict[str, AppDefinition] = {}
        self._scan()

    def _scan(self) -> None:
        """Scan apps_dir for */APP.md and populate self.apps.

        Malformed files (missing `name`) are logged and skipped (T-14-05).
        Non-existent agent names are logged as warnings (startup check only).
        """
        if not self.apps_dir.exists():
            logger.warning("AppRegistry: apps_dir does not exist: %s", self.apps_dir)
            return

        for app_md in sorted(self.apps_dir.glob("*/APP.md")):
            slug = app_md.parent.name
            try:
                post = fm.load(str(app_md))
                name = post.metadata.get("name", "")
                if not name:
                    logger.warning(
                        "AppRegistry: skipping %s — missing required 'name' field", slug
                    )
                    continue

                description = post.metadata.get("description", "")
                icon = post.metadata.get("icon", "")
                agents: list[str] = post.metadata.get("agents") or []

                # Startup check: warn about agents that do not have a matching folder.
                # This is informational only — the app is still registered.
                agent_dir = self.apps_dir.parent / "agents"
                for agent_name in agents:
                    agent_folder = agent_dir / agent_name
                    if not agent_folder.exists():
                        logger.warning(
                            "AppRegistry: app '%s' references agent '%s' "
                            "which has no matching folder in %s",
                            slug,
                            agent_name,
                            agent_dir,
                        )

                self.apps[slug] = AppDefinition(
                    slug=slug,
                    name=str(name),
                    description=str(description).strip(),
                    icon=str(icon),
                    agents=list(agents),
                )
            except Exception as e:
                logger.warning(
                    "AppRegistry: failed to load APP.md for '%s': %s — skipping",
                    slug,
                    e,
                )

    def all(self) -> list[AppDefinition]:
        """Return all discovered app definitions, sorted by slug."""
        return sorted(self.apps.values(), key=lambda a: a.slug)

    def get(self, slug: str) -> AppDefinition | None:
        """Return the AppDefinition for the given slug, or None if not found."""
        return self.apps.get(slug)

    def get_agent_names(self, slug: str) -> list[str]:
        """Return the agents list for the given app slug, or [] if not found."""
        app = self.apps.get(slug)
        return app.agents if app is not None else []
