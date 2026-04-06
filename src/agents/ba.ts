/**
 * Business Analyst Agent
 *
 * Conducts a multi-round clarification loop with the user via structured JSON.
 * Outputs a formal BRD when requirements are sufficiently clear.
 *
 * Inter-agent I/O: JSON only (no natural language between agents).
 */

import { callClaude, parseJSON } from '../utils/claude.js';
import type { BAResponse, BRD, ProjectSession } from '../types/index.js';

const MAX_CLARIFICATION_ROUNDS = 4;

const SYSTEM_PROMPT = `You are a senior Business Analyst AI. Your mission is to gather software requirements and produce a formal Business Requirements Document (BRD).

BEHAVIOR:
- Analyze requirements carefully. If critical information is missing, ask targeted clarifying questions.
- Be specific and efficient — ask only the most important questions (max 5 at a time).
- After sufficient clarification (usually 1-3 rounds), produce a complete BRD.
- After ${MAX_CLARIFICATION_ROUNDS} rounds, produce the BRD with reasonable assumptions.

OUTPUT FORMAT:
You MUST respond with ONLY valid JSON — no prose, no markdown, no code blocks.

When more clarification is needed:
{
  "status": "NEEDS_CLARIFICATION",
  "analysis": "<brief summary of what you understand so far>",
  "questions": ["<specific question 1>", "<specific question 2>"],
  "context": "<why these questions are critical>",
  "iteration": <round number>
}

When requirements are sufficiently clear (produce the BRD):
{
  "status": "REQUIREMENTS_COMPLETE",
  "brd": {
    "title": "<project title>",
    "overview": "<2-3 sentence project overview>",
    "problem_statement": "<the core problem being solved>",
    "goals": ["<goal 1>", "<goal 2>"],
    "functional_requirements": [
      {
        "id": "FR-001",
        "title": "<feature name>",
        "description": "<detailed description>",
        "priority": "MUST|SHOULD|COULD|WONT"
      }
    ],
    "non_functional_requirements": [
      { "category": "Performance|Security|Scalability|etc", "requirement": "<requirement>" }
    ],
    "user_stories": [
      {
        "id": "US-001",
        "as_a": "<role>",
        "i_want": "<capability>",
        "so_that": "<benefit>",
        "acceptance_criteria": ["<criterion 1>", "<criterion 2>"]
      }
    ],
    "stakeholders": ["<stakeholder 1>", "<stakeholder 2>"],
    "out_of_scope": ["<item 1>"],
    "assumptions": ["<assumption 1>"],
    "constraints": ["<constraint 1>"]
  }
}`;

/**
 * Process the first message: analyze initial requirement and decide
 * whether clarification is needed or requirements are already clear.
 */
export async function baProcessInitial(session: ProjectSession): Promise<BAResponse> {
  const userMessage = `Please analyze this software requirement and determine if you need clarification to produce a complete BRD:

REQUIREMENT:
${session.original_requirement}

Round: 1 of ${MAX_CLARIFICATION_ROUNDS}`;

  // Start BA conversation history
  session.ba_messages = [{ role: 'user', content: userMessage }];

  const raw = await callClaude(SYSTEM_PROMPT, session.ba_messages);
  const response = parseJSON<BAResponse>(raw);

  // Store assistant response in conversation history for next round
  session.ba_messages.push({ role: 'assistant', content: raw });

  return response;
}

/**
 * Process user's clarification answers and decide next step.
 * Continues the multi-turn Claude conversation.
 */
export async function baProcessClarification(
  session: ProjectSession,
  userAnswers: string
): Promise<BAResponse> {
  const round = session.clarification_rounds.length + 1;

  const userMessage = `User's answers to your questions:

${userAnswers}

Round: ${round} of ${MAX_CLARIFICATION_ROUNDS}${round >= MAX_CLARIFICATION_ROUNDS
    ? '\n\nThis is the final round. You MUST produce the complete BRD now based on all information gathered, using reasonable assumptions for anything still unclear.'
    : ''
  }`;

  session.ba_messages.push({ role: 'user', content: userMessage });

  const raw = await callClaude(SYSTEM_PROMPT, session.ba_messages);
  const response = parseJSON<BAResponse>(raw);

  session.ba_messages.push({ role: 'assistant', content: raw });

  return response;
}

/**
 * Force BRD generation if maximum rounds exceeded.
 * Instructs Claude to make reasonable assumptions.
 */
export async function baForceComplete(session: ProjectSession): Promise<BRD> {
  const userMessage = `You have reached the maximum clarification rounds.
Please produce the final BRD now, making reasonable assumptions for any unclear points.
Document your assumptions in the "assumptions" field.
Respond with ONLY the REQUIREMENTS_COMPLETE JSON.`;

  session.ba_messages.push({ role: 'user', content: userMessage });

  const raw = await callClaude(SYSTEM_PROMPT, session.ba_messages);
  const response = parseJSON<BAResponse>(raw);

  if (response.status !== 'REQUIREMENTS_COMPLETE') {
    throw new Error('BA failed to produce BRD after maximum rounds');
  }

  return response.brd;
}
