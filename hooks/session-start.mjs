#!/usr/bin/env node
// Claude Code SessionStart hook: print the always-on rules. Claude Code adds
// plain stdout of a SessionStart hook to the context (capped at 10,000 characters).
// Level: env ANTISLOP_LEVEL, then ~/.config/antislop-writing/level, then 80.
// Never fails: on any error the session starts without the rules.

import { configuredLevel, renderKernel, ROOT } from '../lib/kernel.mjs';

try {
  const root = process.env.CLAUDE_PLUGIN_ROOT || process.env.PLUGIN_ROOT || ROOT;
  process.stdout.write(renderKernel(configuredLevel(), root) + '\n');
} catch (err) {
  process.stderr.write(`antislop-writing hook: ${err.message}\n`);
}
process.exit(0);
