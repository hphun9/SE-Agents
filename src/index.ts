import 'dotenv/config';
import { createBot } from './telegram/bot.js';

function assertEnv(key: string): string {
  const val = process.env[key];
  if (!val) throw new Error(`Missing required environment variable: ${key}`);
  return val;
}

async function main(): Promise<void> {
  const telegramToken = assertEnv('TELEGRAM_BOT_TOKEN');
  assertEnv('ANTHROPIC_API_KEY');

  console.log('🚀 SE-Agents starting...');
  console.log('   Model: claude-opus-4-6');
  console.log('   Pipeline: BA → SA → PM → Tech Lead');

  const bot = createBot(telegramToken);

  console.log('✅ Bot is running. Send a message on Telegram to start.');

  process.on('SIGINT', () => {
    console.log('\nShutting down...');
    bot.stopPolling();
    process.exit(0);
  });
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
