#!/usr/bin/env node
// Installer for antislop-writing.
//
//   npx github:apgruzdev/antislop-writing                install skills and the always-on rules
//   npx github:apgruzdev/antislop-writing --level 60     set the writing level
//   npx github:apgruzdev/antislop-writing --skills-only  skills only
//   npx github:apgruzdev/antislop-writing --rules-only   rules only
//   npx github:apgruzdev/antislop-writing --project      for the current project instead of your user
//   npx github:apgruzdev/antislop-writing uninstall
//   npx github:apgruzdev/antislop-writing status

import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import {
  DEFAULT_LEVEL, blockLevel, hasBlock, removeBlock, snapLevel, upsertBlock,
} from '../lib/kernel.mjs';

const SOURCE = 'apgruzdev/antislop-writing';
const HELP = `antislop-writing: установка правил письма против нейрослопа

Команды:
  (без команды)  установить навыки и правило «всегда включено»
  uninstall      убрать правило и навыки
  status         показать, что установлено

Параметры:
  --level N        уровень 20, 40, 60, 80 или 100 (по умолчанию: прежний или 80)
  --skills-only    только навыки
  --rules-only     только правило «всегда включено»
  --project        для текущего проекта (./AGENTS.md и навыки в проекте), а не для пользователя
  --agents a,b     не определять агентов, а взять этих (id из \`npx skills\`: claude-code, codex, opencode, gemini-cli, cursor ...)
  --source SRC     откуда ставить навыки (по умолчанию ${SOURCE})
  --dry-run        показать, что будет сделано, и ничего не менять
  -h, --help       эта справка
`;

function parse(argv) {
  const o = { cmd: 'install', level: null, skills: true, rules: true, project: false, agents: null, source: SOURCE, dryRun: false, home: null, cwd: process.cwd() };
  const a = [...argv];
  while (a.length) {
    const x = a.shift();
    if (['install', 'uninstall', 'status'].includes(x)) o.cmd = x;
    else if (x === '--level') o.level = snapLevel(a.shift());
    else if (x.startsWith('--level=')) o.level = snapLevel(x.slice(8));
    else if (x === '--skills-only') o.rules = false;
    else if (x === '--rules-only') o.skills = false;
    else if (x === '--project') o.project = true;
    else if (x === '--agents') o.agents = a.shift().split(',').map((s) => s.trim()).filter(Boolean);
    else if (x === '--source') o.source = a.shift();
    else if (x === '--dry-run') o.dryRun = true;
    else if (x === '--home') o.home = resolve(a.shift());
    else if (x === '--cwd') o.cwd = resolve(a.shift());
    else if (x === '-h' || x === '--help') o.cmd = 'help';
    else { console.error(`Неизвестный параметр: ${x}\n`); o.cmd = 'help'; o.bad = true; }
  }
  return o;
}

const AGENTS = [
  { id: 'claude-code', name: 'Claude Code', dir: ['.claude'], rules: ['.claude', 'CLAUDE.md'] },
  { id: 'codex', name: 'Codex', dir: ['.codex'], rules: ['.codex', 'AGENTS.md'] },
  { id: 'opencode', name: 'OpenCode', dir: ['.config', 'opencode'], rules: ['.config', 'opencode', 'AGENTS.md'] },
  { id: 'gemini-cli', name: 'Gemini CLI', dir: ['.gemini'], rules: ['.gemini', 'GEMINI.md'] },
  { id: 'windsurf', name: 'Windsurf', dir: ['.codeium', 'windsurf'], rules: ['.codeium', 'windsurf', 'memories', 'global_rules.md'] },
  { id: 'cursor', name: 'Cursor', dir: ['.cursor'], rules: null, note: 'Cursor хранит глобальные правила в настройках. Вставьте prompts/kernel.md в Settings, Rules.' },
  { id: 'github-copilot', name: 'GitHub Copilot', dir: ['.copilot'], rules: null, note: 'Для Copilot используйте --project: он читает AGENTS.md проекта.' },
];

function detect(home, forced) {
  if (forced) return AGENTS.filter((a) => forced.includes(a.id)).concat(forced.filter((id) => !AGENTS.some((a) => a.id === id)).map((id) => ({ id, name: id, dir: [], rules: null })));
  return AGENTS.filter((a) => existsSync(join(home, ...a.dir)));
}

const read = (p) => (existsSync(p) ? readFileSync(p, 'utf8') : '');

// Files that receive the block. Each item: { file, agent, create }
function ruleTargets(o, home, agents, skipped = []) {
  const out = [];
  const seen = new Set();
  const push = (file, agent, content) => {
    if (seen.has(file)) return;
    seen.add(file);
    out.push({ file, agent, content });
  };
  if (o.project) {
    const has = (id) => agents.some((a) => a.id === id);
    push(join(o.cwd, 'AGENTS.md'), 'AGENTS.md (Codex, OpenCode, Cursor, Copilot, Windsurf и др.)');
    for (const [id, file, name] of [['claude-code', 'CLAUDE.md', 'Claude Code'], ['gemini-cli', 'GEMINI.md', 'Gemini CLI']]) {
      const p = join(o.cwd, file);
      const text = read(p);
      if (existsSync(p) && !text.includes('@AGENTS.md')) push(p, name);
      else if (!existsSync(p) && has(id)) push(p, name, '@AGENTS.md\n');
    }
    return out;
  }
  const claudeFile = join(home, '.claude', 'CLAUDE.md');
  for (const a of agents) {
    if (!a.rules) continue;
    let file = join(home, ...a.rules);
    if (a.id === 'codex' && existsSync(join(home, '.codex', 'AGENTS.override.md'))) file = join(home, '.codex', 'AGENTS.override.md');
    if (a.id === 'opencode' && !existsSync(file)) {
      // OpenCode falls back to ~/.claude/CLAUDE.md only while its own AGENTS.md is absent.
      // A new AGENTS.md would hide the user's Claude rules from OpenCode.
      if (existsSync(claudeFile) || agents.some((x) => x.id === 'claude-code')) {
        skipped.push('OpenCode читает ~/.claude/CLAUDE.md, пока нет своего AGENTS.md: отдельный файл не нужен');
        continue;
      }
    }
    push(file, a.name);
  }
  return out;
}

function currentLevel(targets) {
  for (const t of targets) {
    const l = blockLevel(read(t.file));
    if (l) return l;
  }
  return null;
}

function applyRules(o, home, agents) {
  const skipped = [];
  const targets = ruleTargets(o, home, agents, skipped);
  const level = o.level ?? currentLevel(targets) ?? DEFAULT_LEVEL;
  for (const msg of skipped) console.log(`  ${msg}`);
  if (!targets.length) console.log('Правило «всегда включено»: подходящих файлов не найдено. Вставьте prompts/kernel.md в инструкции агента вручную.');
  for (const t of targets) {
    const before = read(t.file);
    const body = t.content && !before ? t.content : upsertBlock(before, level);
    if (t.content && !before) {
      // A tiny import file, for example CLAUDE.md with "@AGENTS.md". It carries no block.
      console.log(`${o.dryRun ? '[dry-run] ' : ''}+ ${t.file}: импорт AGENTS.md (${t.agent})`);
      if (!o.dryRun) { mkdirSync(dirname(t.file), { recursive: true }); writeFileSync(t.file, t.content); }
      continue;
    }
    const verb = hasBlock(before) ? 'обновлён блок' : existsSync(t.file) ? 'добавлен блок' : 'создан файл';
    console.log(`${o.dryRun ? '[dry-run] ' : ''}+ ${t.file}: ${verb}, уровень ${level} (${t.agent})`);
    if (!o.dryRun) { mkdirSync(dirname(t.file), { recursive: true }); writeFileSync(t.file, body); }
  }
  for (const a of agents) if (a.note && !o.project) console.log(`  ${a.name}: ${a.note}`);
  return level;
}

function npxArgs(args) {
  if (process.platform === 'win32') {
    const q = args.map((x) => (/[\s*]/.test(x) ? `"${x}"` : x)).join(' ');
    return ['npx.cmd', [q], { shell: true }];
  }
  return ['npx', args, {}];
}

function runSkills(o, home, agents, kind) {
  const ids = agents.map((a) => a.id);
  const agentFlags = (ids.length ? ids : ['universal']).flatMap((id) => ['-a', id]);
  const args = kind === 'add'
    ? ['-y', 'skills', 'add', o.source, '--skill', '*', ...(o.project ? [] : ['-g']), '-y', ...agentFlags]
    : ['-y', 'skills', 'remove', o.source, ...(o.project ? [] : ['-g']), '-y'];
  const [cmd, a, extra] = npxArgs(args);
  console.log(`${o.dryRun ? '[dry-run] ' : ''}$ npx ${args.join(' ')}`);
  if (o.dryRun) return 0;
  const r = spawnSync(cmd, a, { stdio: 'inherit', cwd: o.cwd, env: { ...process.env, HOME: home, USERPROFILE: home }, ...extra });
  return r.status ?? 1;
}

function install(o, home, agents) {
  let code = 0;
  console.log(`Агенты: ${agents.length ? agents.map((a) => a.name).join(', ') : 'не найдены, ставлю в универсальный каталог ~/.agents/skills'}`);
  if (o.skills) code = runSkills(o, home, agents, 'add');
  if (code !== 0) { console.error('\nНавыки не установились. Правило «всегда включено» не тронуто.'); return code; }
  let level = null;
  if (o.rules) { console.log(''); level = applyRules(o, home, agents); }
  console.log('\nГотово. Перезапустите агента.');
  if (o.rules) console.log(`Сменить уровень: запустите установщик с --level N или поправьте число после «Уровень письма:» в файлах выше (сейчас ${level}).`);
  console.log('Проверка: попросите агента «объясни, что такое идемпотентность» и сравните ответ с обычным.');
  return 0;
}

function uninstall(o, home, agents) {
  const all = detect(home, null);
  const targets = ruleTargets(o, home, all.length ? all : AGENTS);
  const extra = [join(home, '.codex', 'AGENTS.override.md'), join(home, '.claude', 'CLAUDE.md'), join(home, '.config', 'opencode', 'AGENTS.md')];
  const files = new Set([...targets.map((t) => t.file), ...extra]);
  for (const file of files) {
    const text = read(file);
    if (!hasBlock(text)) continue;
    const next = removeBlock(text);
    console.log(`${o.dryRun ? '[dry-run] ' : ''}- ${file}: блок удалён${next.trim() ? '' : ', файл пуст и удалён'}`);
    if (o.dryRun) continue;
    if (next.trim()) writeFileSync(file, next);
    else rmSync(file);
  }
  if (o.skills) return runSkills(o, home, agents, 'remove');
  return 0;
}

function status(o, home, agents) {
  console.log(`Агенты: ${agents.map((a) => a.name).join(', ') || 'не найдены'}`);
  const files = ruleTargets({ ...o, project: false }, home, agents.length ? agents : AGENTS).map((t) => t.file);
  files.push(join(o.cwd, 'AGENTS.md'));
  for (const f of new Set(files)) {
    const text = read(f);
    console.log(`${hasBlock(text) ? 'есть ' : 'нет  '} ${f}${hasBlock(text) ? `  (уровень ${blockLevel(text)})` : ''}`);
  }
  console.log('Навыки: npx skills ls -g');
  return 0;
}

function main(argv) {
  const o = parse(argv);
  if (o.cmd === 'help') { console.log(HELP); return o.bad ? 1 : 0; }
  const home = o.home || homedir();
  const agents = detect(home, o.agents);
  if (o.cmd === 'uninstall') return uninstall(o, home, agents);
  if (o.cmd === 'status') return status(o, home, agents);
  return install(o, home, agents);
}

process.exit(main(process.argv.slice(2)));
