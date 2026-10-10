import assert from 'node:assert/strict';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { spawnSync } from 'node:child_process';
import { ROOT, blockLevel, hasBlock } from '../lib/kernel.mjs';

const BIN = join(ROOT, 'bin', 'antislop-writing.mjs');

function sandbox(dirs = []) {
  const home = mkdtempSync(join(tmpdir(), 'antislop-test-'));
  for (const d of dirs) mkdirSync(join(home, d), { recursive: true });
  return home;
}
function run(home, ...args) {
  return spawnSync('node', [BIN, '--home', home, ...args], { encoding: 'utf8' });
}
const read = (...p) => readFileSync(join(...p), 'utf8');

test('rules-only writes the block for each detected agent and keeps user text', () => {
  const home = sandbox(['.claude', '.codex', '.gemini']);
  writeFileSync(join(home, '.claude', 'CLAUDE.md'), '# Мои правила\n');
  const r = run(home, '--rules-only', '--level', '60');
  assert.equal(r.status, 0, r.stderr);
  assert.ok(read(home, '.claude', 'CLAUDE.md').startsWith('# Мои правила\n'));
  for (const f of ['.claude/CLAUDE.md', '.codex/AGENTS.md', '.gemini/GEMINI.md']) {
    assert.equal(blockLevel(read(home, f)), 60, f);
  }
  rmSync(home, { recursive: true, force: true });
});

test('a second run changes nothing, and the level survives a run without --level', () => {
  const home = sandbox(['.codex']);
  run(home, '--rules-only', '--level', '40');
  const first = read(home, '.codex', 'AGENTS.md');
  const r = run(home, '--rules-only');
  assert.equal(r.status, 0);
  assert.equal(read(home, '.codex', 'AGENTS.md'), first);
  assert.equal(blockLevel(first), 40);
  rmSync(home, { recursive: true, force: true });
});

test('OpenCode: no new AGENTS.md when it would hide ~/.claude/CLAUDE.md', () => {
  const home = sandbox(['.claude', '.config/opencode']);
  const r = run(home, '--rules-only');
  assert.match(r.stdout, /OpenCode читает/);
  assert.ok(!existsSync(join(home, '.config', 'opencode', 'AGENTS.md')));
  rmSync(home, { recursive: true, force: true });
});

test('OpenCode alone gets its own AGENTS.md', () => {
  const home = sandbox(['.config/opencode']);
  run(home, '--rules-only');
  assert.ok(hasBlock(read(home, '.config', 'opencode', 'AGENTS.md')));
  rmSync(home, { recursive: true, force: true });
});

test('Codex: AGENTS.override.md wins when it exists', () => {
  const home = sandbox(['.codex']);
  writeFileSync(join(home, '.codex', 'AGENTS.override.md'), 'временно\n');
  run(home, '--rules-only');
  assert.ok(hasBlock(read(home, '.codex', 'AGENTS.override.md')));
  assert.ok(!existsSync(join(home, '.codex', 'AGENTS.md')));
  rmSync(home, { recursive: true, force: true });
});

test('uninstall removes the block, keeps user text, deletes files that became empty', () => {
  const home = sandbox(['.claude', '.codex']);
  writeFileSync(join(home, '.claude', 'CLAUDE.md'), '# Мои правила\n');
  run(home, '--rules-only');
  const r = run(home, 'uninstall', '--skills-only');
  assert.equal(r.status, 0, r.stderr);
  assert.equal(read(home, '.claude', 'CLAUDE.md'), '# Мои правила\n');
  assert.ok(!existsSync(join(home, '.codex', 'AGENTS.md')));
  rmSync(home, { recursive: true, force: true });
});

test('--dry-run changes nothing', () => {
  const home = sandbox(['.codex']);
  const r = run(home, '--rules-only', '--dry-run');
  assert.equal(r.status, 0);
  assert.match(r.stdout, /dry-run/);
  assert.ok(!existsSync(join(home, '.codex', 'AGENTS.md')));
  rmSync(home, { recursive: true, force: true });
});

test('--project writes AGENTS.md and a CLAUDE.md import', () => {
  const home = sandbox(['.claude']);
  const cwd = mkdtempSync(join(tmpdir(), 'antislop-proj-'));
  const r = spawnSync('node', [BIN, '--home', home, '--cwd', cwd, '--project', '--rules-only', '--level', '100'], { encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr);
  assert.equal(blockLevel(read(cwd, 'AGENTS.md')), 100);
  assert.equal(read(cwd, 'CLAUDE.md'), '@AGENTS.md\n');
  rmSync(home, { recursive: true, force: true });
  rmSync(cwd, { recursive: true, force: true });
});

test('a bad option prints help and fails', () => {
  const r = spawnSync('node', [BIN, '--nope'], { encoding: 'utf8' });
  assert.equal(r.status, 1);
  assert.match(r.stdout, /Команды/);
});
