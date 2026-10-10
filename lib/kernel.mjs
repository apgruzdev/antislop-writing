// Shared by the installer and the Claude Code SessionStart hook.
import { existsSync, readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
export const LEVELS = [20, 40, 60, 80, 100];
export const DEFAULT_LEVEL = 80;
export const BEGIN = '<!-- antislop-writing:begin -->';
export const END = '<!-- antislop-writing:end -->';

const FALLBACK = `## Antislop writing
Уровень письма: {{LEVEL}}
Первая фраза — ответ. Факт вместо оценки. Не выдумывай факты. Без канцелярита, штампов и «не X, а Y» чаще раза на 1000 слов. Один термин на понятие. Предложение до 25 слов. Код и цитаты не меняй. Source: https://github.com/apgruzdev/antislop-writing`;

// Round to the nearest step. A tie rounds down: 90 -> 80.
export function snapLevel(n) {
  const x = Number(n);
  if (!Number.isFinite(x)) return DEFAULT_LEVEL;
  let best = LEVELS[0];
  for (const l of LEVELS) if (Math.abs(l - x) < Math.abs(best - x)) best = l;
  return best;
}

export function kernelTemplate(root = ROOT) {
  try {
    return readFileSync(join(root, 'prompts', 'kernel.md'), 'utf8').trim();
  } catch {
    return FALLBACK;
  }
}

export function renderKernel(level, root = ROOT) {
  return kernelTemplate(root).replaceAll('{{LEVEL}}', String(snapLevel(level)));
}

export function wrapBlock(level, root = ROOT) {
  return `${BEGIN}\n${renderKernel(level, root)}\n${END}`;
}

const BLOCK_RE = new RegExp(`${BEGIN}[\\s\\S]*?${END}\\n?`);

export function hasBlock(text) {
  return text.includes(BEGIN) && text.includes(END);
}

export function blockLevel(text) {
  const m = text.match(new RegExp(`${BEGIN}[\\s\\S]*?Уровень письма:\\s*(\\d+)[\\s\\S]*?${END}`));
  return m ? snapLevel(m[1]) : null;
}

// Insert the block, or replace the existing one. Text outside the markers stays untouched.
export function upsertBlock(text, level, root = ROOT) {
  const block = wrapBlock(level, root);
  if (hasBlock(text)) return text.replace(BLOCK_RE, block + '\n');
  const sep = text.length === 0 ? '' : text.endsWith('\n\n') ? '' : text.endsWith('\n') ? '\n' : '\n\n';
  return `${text}${sep}${block}\n`;
}

// Remove the block and the one blank line that upsertBlock put before it.
const REMOVE_RE = new RegExp(`\\n?${BEGIN}[\\s\\S]*?${END}\\n?`);

export function removeBlock(text) {
  if (!hasBlock(text)) return text;
  return text.replace(REMOVE_RE, '').replace(/^\n+/, '');
}

// Level for the hook: ANTISLOP_LEVEL, then ~/.config/antislop-writing/level, then 80.
export function configuredLevel(env = process.env, home = homedir()) {
  if (env.ANTISLOP_LEVEL) return snapLevel(env.ANTISLOP_LEVEL);
  const file = join(env.XDG_CONFIG_HOME || join(home, '.config'), 'antislop-writing', 'level');
  if (existsSync(file)) {
    try {
      return snapLevel(readFileSync(file, 'utf8').trim());
    } catch {
      /* fall through */
    }
  }
  return DEFAULT_LEVEL;
}
