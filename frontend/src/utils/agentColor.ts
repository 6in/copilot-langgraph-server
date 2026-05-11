// Deterministic per-agent color palette — shared by AgentSelector chips and chat bubbles.
// Each palette: light/dark bubble background + accent for chip border/selected state.

const AGENT_PALETTES = [
  { light: '#eef3ff', dark: '#1c2340', accent: '#4a7fcb' },
  { light: '#f0faf0', dark: '#1a2e1c', accent: '#3d9a50' },
  { light: '#fff8ee', dark: '#2e2214', accent: '#c87820' },
  { light: '#f8f0ff', dark: '#221a30', accent: '#8a50cb' },
  { light: '#fff0f5', dark: '#2e1a22', accent: '#cb4a80' },
  { light: '#f0fffe', dark: '#162e2e', accent: '#2a9a9a' },
  { light: '#fffbee', dark: '#2a2614', accent: '#b89a20' },
  { light: '#f5f0ff', dark: '#1e1a30', accent: '#7a50cb' },
];

function hashName(name: string): number {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) & 0xffff;
  return hash % AGENT_PALETTES.length;
}

export function agentBgColor(name: string, theme: string): string {
  const p = AGENT_PALETTES[hashName(name)];
  return theme === 'dark' ? p.dark : p.light;
}

export function agentAccentColor(name: string): string {
  return AGENT_PALETTES[hashName(name)].accent;
}
