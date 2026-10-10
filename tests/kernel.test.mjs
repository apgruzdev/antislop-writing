import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { test } from 'node:test';
import { spawnSync } from 'node:child_process';
import {
  ROOT, blockLevel, configuredLevel, hasBlock, removeBlock, renderKernel, snapLevel, upsertBlock,
} from '../lib/kernel.mjs';

test('snapLevel rounds to the nearest step, ties down', () => {
  assert.equal(snapLevel(90), 80);
  assert.equal(snapLevel(70), 60);
  assert.equal(snapLevel('100'), 100);
  assert.equal(snapLevel(0), 20);
  assert.equal(snapLevel(999), 100);
  assert.equal(snapLevel('abc'), 80);
});

test('kernel fits the limits of the strictest platforms', () => {
  const kernel = renderKernel(80);
  assert.ok([...kernel].length <= 6000, 'Windsurf global rules: 6000 characters');
  const mini = readFileSync(join(ROOT, 'prompts', 'mini.md'), 'utf8');
  assert.ok([...mini].length <= 1500, 'ChatGPT Free custom instructions: 1500 characters');
  assert.ok(kernel.includes('Уровень письма: 80'));
  assert.ok(!kernel.includes('{{LEVEL}}'));
});

test('upsertBlock is idempotent and keeps outside text', () => {
  const user = '# Мои правила\n\nОтвечай кратко.\n';
  const once = upsertBlock(user, 80);
  assert.ok(once.startsWith(user));
  assert.ok(hasBlock(once));
  assert.equal(upsertBlock(once, 80), once);
  const changed = upsertBlock(once, 40);
  assert.equal(blockLevel(changed), 40);
  assert.ok(changed.startsWith(user));
  assert.equal(changed.match(/antislop-writing:begin/g).length, 1);
});

test('removeBlock restores the original text', () => {
  const user = '# Мои правила\n\nОтвечай кратко.\n';
  assert.equal(removeBlock(upsertBlock(user, 60)), user);
  assert.equal(removeBlock(upsertBlock('', 60)).trim(), '');
  assert.equal(removeBlock(user), user);
});

test('configuredLevel reads env, then file, then default', () => {
  assert.equal(configuredLevel({ ANTISLOP_LEVEL: '100' }, '/nonexistent'), 100);
  assert.equal(configuredLevel({}, '/nonexistent'), 80);
});

test('session hook prints the kernel with the configured level', () => {
  const r = spawnSync('node', [join(ROOT, 'hooks', 'session-start.mjs')], {
    env: { ...process.env, ANTISLOP_LEVEL: '60' }, encoding: 'utf8',
  });
  assert.equal(r.status, 0);
  assert.match(r.stdout, /Уровень письма: 60/);
  assert.ok(r.stdout.length < 9500, 'Claude Code caps hook output at 10,000 characters');
});

test('session hook exits 0 even when the plugin root is wrong', () => {
  const r = spawnSync('node', [join(ROOT, 'hooks', 'session-start.mjs')], {
    env: { ...process.env, CLAUDE_PLUGIN_ROOT: '/nonexistent' }, encoding: 'utf8',
  });
  assert.equal(r.status, 0);
  assert.match(r.stdout, /Антислоп|Antislop|Уровень письма/);
});
