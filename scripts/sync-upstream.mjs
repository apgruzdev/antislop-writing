#!/usr/bin/env node
// Vendor third-party skills at pinned commits.
//
//   node scripts/sync-upstream.mjs            copy the pinned commits into skills/
//   node scripts/sync-upstream.mjs --check    exit 1 if skills/ differs from the pinned commits
//   node scripts/sync-upstream.mjs --update   move every pin to the current head of its ref, then copy
//
// Each vendored skill directory gets two extra files: LICENSE (the upstream
// license text) and NOTICE.md (where the copy came from). Nothing else changes.

import { execFileSync } from 'node:child_process';
import {
  cpSync, existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync,
  rmSync, statSync, writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const CONFIG = join(ROOT, 'upstream.json');
const SKIP = new Set(['.git', '.DS_Store']);

const args = new Set(process.argv.slice(2));
const mode = args.has('--update') ? 'update' : args.has('--check') ? 'check' : 'sync';

function git(cwd, ...a) {
  return execFileSync('git', a, { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
}

function headOf(repo, ref) {
  const out = git(ROOT, 'ls-remote', repo, ref);
  const sha = out.split(/\s+/)[0];
  if (!/^[0-9a-f]{40}$/.test(sha)) throw new Error(`cannot resolve ${ref} of ${repo}`);
  return sha;
}

function checkout(repo, sha, dir) {
  mkdirSync(dir, { recursive: true });
  git(dir, 'init', '-q');
  git(dir, 'fetch', '-q', '--depth', '1', repo, sha);
  git(dir, 'checkout', '-q', 'FETCH_HEAD');
}

function notice(src, entry) {
  const short = src.sha.slice(0, 7);
  return `# Происхождение этого навыка / Origin of this skill

Эта папка — **неизменённая копия** \`${entry.from}\` из ${src.repo} (коммит \`${short}\`, полный хеш ${src.sha}).
В копию добавлены только два файла: \`LICENSE\` и этот \`NOTICE.md\`.

This directory is an **unmodified copy** of \`${entry.from}\` from ${src.repo} (commit \`${short}\`, full hash ${src.sha}).
Only two files were added to the copy: \`LICENSE\` and this \`NOTICE.md\`.

- Автор / Author: ${src.author}
- Лицензия / License: ${src.license} (см. \`LICENSE\` / see \`LICENSE\`)
- Первоисточник / Upstream: ${src.repo}

Копия лежит в репозиторий [antislop-writing](https://github.com/apgruzdev/antislop-writing), чтобы одна установка ставила все зависимости.
Замечания по содержанию отправляйте автору оригинала. / Send content feedback to the upstream author.
`;
}

function copyTree(from, to) {
  rmSync(to, { recursive: true, force: true });
  cpSync(from, to, {
    recursive: true,
    filter: (p) => !SKIP.has(p.split('/').pop()),
  });
}

function materialize(src, outRoot, workDir) {
  const co = join(workDir, src.id);
  checkout(src.repo, src.sha, co);
  const license = readFileSync(join(co, src.licenseFile), 'utf8');
  for (const entry of src.copy) {
    const dest = join(outRoot, entry.to);
    copyTree(join(co, entry.from), dest);
    writeFileSync(join(dest, 'LICENSE'), license);
    writeFileSync(join(dest, 'NOTICE.md'), notice(src, entry));
  }
}

function listFiles(dir, base = dir) {
  const out = [];
  for (const name of readdirSync(dir).sort()) {
    if (SKIP.has(name)) continue;
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out.push(...listFiles(p, base));
    else out.push(relative(base, p));
  }
  return out;
}

const config = JSON.parse(readFileSync(CONFIG, 'utf8'));

if (mode === 'update') {
  for (const src of config.sources) {
    const head = headOf(src.repo, src.ref);
    if (head !== src.sha) console.log(`${src.id}: ${src.sha.slice(0, 7)} -> ${head.slice(0, 7)}`);
    else console.log(`${src.id}: already at ${head.slice(0, 7)}`);
    src.sha = head;
  }
  writeFileSync(CONFIG, JSON.stringify(config, null, 2) + '\n');
}

const work = mkdtempSync(join(tmpdir(), 'antislop-sync-'));
try {
  if (mode === 'check') {
    const staging = join(work, 'stage');
    for (const src of config.sources) materialize(src, staging, work);
    let drift = 0;
    for (const src of config.sources) {
      for (const entry of src.copy) {
        const want = join(staging, entry.to);
        const have = join(ROOT, entry.to);
        if (!existsSync(have)) { console.error(`missing: ${entry.to}`); drift++; continue; }
        const a = listFiles(want);
        const b = listFiles(have);
        const all = new Set([...a, ...b]);
        for (const f of all) {
          const pa = join(want, f);
          const pb = join(have, f);
          if (!existsSync(pa)) { console.error(`extra file: ${entry.to}/${f}`); drift++; }
          else if (!existsSync(pb)) { console.error(`missing file: ${entry.to}/${f}`); drift++; }
          else if (!readFileSync(pa).equals(readFileSync(pb))) { console.error(`changed: ${entry.to}/${f}`); drift++; }
        }
      }
    }
    if (drift) { console.error(`\n${drift} difference(s) from the pinned upstream commits.`); process.exit(1); }
    console.log('vendored skills match the pinned upstream commits');
  } else {
    for (const src of config.sources) {
      materialize(src, ROOT, work);
      console.log(`${src.id} @ ${src.sha.slice(0, 7)}: ${src.copy.map((c) => c.to).join(', ')}`);
    }
  }
} finally {
  rmSync(work, { recursive: true, force: true });
}
