# Phase 14: Application Packages + Menu - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the discussion.

**Date:** 2026-04-05
**Phase:** 14-application-packages-menu
**Mode:** discuss
**Areas analyzed:** App definition file format, Menu screen evolution, Agent filtering architecture, App-scoped chat UI

## Assumptions Presented

### Pre-discussion codebase state
| Item | Observation |
|------|------------|
| `MenuScreen.tsx` | Static, hardcoded "Chat" + "SuperChat" cards |
| `SubAgentRegistry` | Loads all agents from `agents/*/AGENT.md` glob — no app scoping |
| `build_orchestrator_graph()` | Single graph with all agents at startup |
| `app_id` in threads | Hardcoded "chat" or "superchat" from mode field |
| `SuperChatApp.tsx` | Multi-agent chat with thread sidebar — candidate for reuse |

## Gray Areas Discussed

### App definition file format
| Option | Chosen |
|--------|--------|
| APP.md in apps/ folder (YAML frontmatter, same as AGENT.md) | ✓ Selected |
| apps.yaml single config file | — |
| Python config in app/ | — |

**Decision:** `apps/<slug>/APP.md` with YAML frontmatter (`name`, `description`, `icon`, `agents: []`). Mirrors AGENT.md pattern exactly.

### Menu screen evolution
| Option | Chosen |
|--------|--------|
| Dynamic app cards replace Chat/SuperChat entirely | ✓ Selected |
| Dynamic cards added below existing hardcoded cards | — |
| Single unified list from API (Chat/SuperChat injected by backend) | — |

**Decision:** Hardcoded cards removed. MenuScreen fetches from `GET /api/apps`. Chat and SuperChat become `apps/chat/APP.md` and `apps/superchat/APP.md`.

### Agent filtering architecture
| Option | Chosen |
|--------|--------|
| One compiled graph per app at startup | ✓ Selected |
| Single graph, filter candidates per invocation | — |

**Decision:** AppRegistry loads APP.md files, builds per-app filtered SubAgentRegistry, compiles per-app OrchestratorGraph. Stored as `app_graphs[slug]` dict. Per-request: look up graph by app slug.

### App-scoped chat UI
| Option | Chosen |
|--------|--------|
| Reuse SuperChatApp with appId/appName props | ✓ Selected |
| New AppChatApp component | — |
| Reuse SuperChatApp with no visible app indicator | — |

**Decision:** `SuperChatApp.tsx` receives `appId` (slug) and `appName` props. `App.tsx` adds `activeApp: AppDefinition | null` state. Header shows active app name.

## Corrections Made

No corrections — all recommended options were accepted.

## Todos Reviewed

- "チャットのコンテキストにてユーザー情報も入れるようにする" — not folded (out of scope for Phase 14)
- "Implement Gem and Canvas feature" — not folded (separate feature)
- "Investigate Agent-Skills integration mechanism" — not folded (separate research)
