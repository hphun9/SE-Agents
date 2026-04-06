import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

export const MODEL = 'claude-opus-4-6';

/**
 * Call Claude with a system prompt and messages, returning the full text response.
 * Uses streaming internally to handle large outputs without timeout.
 */
export async function callClaude(
  systemPrompt: string,
  messages: Array<{ role: 'user' | 'assistant'; content: string }>,
  maxTokens = 16000
): Promise<string> {
  const stream = client.messages.stream({
    model: MODEL,
    max_tokens: maxTokens,
    thinking: { type: 'adaptive' },
    system: systemPrompt,
    messages,
  });

  const response = await stream.finalMessage();

  // Extract text from response content blocks
  const textBlocks = response.content.filter((b) => b.type === 'text');
  if (textBlocks.length === 0) {
    throw new Error('Claude returned no text content');
  }
  return textBlocks.map((b) => (b as { type: 'text'; text: string }).text).join('');
}

/**
 * Parse JSON from a Claude response string.
 * Claude sometimes wraps JSON in markdown code blocks — this strips them.
 */
export function parseJSON<T>(raw: string): T {
  // Strip markdown code blocks: ```json ... ``` or ``` ... ```
  let cleaned = raw.trim();
  cleaned = cleaned.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/i, '');

  // Extract the outermost JSON object or array
  const firstBrace = cleaned.indexOf('{');
  const firstBracket = cleaned.indexOf('[');
  let start = -1;

  if (firstBrace !== -1 && (firstBracket === -1 || firstBrace < firstBracket)) {
    start = firstBrace;
  } else if (firstBracket !== -1) {
    start = firstBracket;
  }

  if (start > 0) {
    cleaned = cleaned.slice(start);
  }

  // Find matching closing brace/bracket
  const openChar = cleaned[0];
  const closeChar = openChar === '{' ? '}' : ']';
  let depth = 0;
  let end = -1;
  for (let i = 0; i < cleaned.length; i++) {
    if (cleaned[i] === openChar) depth++;
    else if (cleaned[i] === closeChar) {
      depth--;
      if (depth === 0) {
        end = i;
        break;
      }
    }
  }

  if (end !== -1) {
    cleaned = cleaned.slice(0, end + 1);
  }

  return JSON.parse(cleaned) as T;
}
