#!/usr/bin/env node

import { runCLI } from './cli/CLI';

runCLI().catch((error) => {
  console.error('CLI execution failed:', error);
  process.exit(1);
});