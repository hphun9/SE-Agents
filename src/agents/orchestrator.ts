/**
 * Orchestrator
 *
 * Manages the full project pipeline:
 *   USER → BA (clarification loop) → SA → PM → Tech Lead → USER
 *
 * All inter-agent communication is structured JSON (AgentMessage envelopes).
 * Natural language is only produced for Telegram-facing output.
 */

import { v4 as uuidv4 } from 'uuid';
import type { AgentMessage, ProjectSession, BAResponse } from '../types/index.js';
import { baProcessInitial, baProcessClarification, baForceComplete } from './ba.js';
import { saGenerateArchitecture } from './sa.js';
import { pmGenerateProjectPlan } from './pm.js';
import { techLeadGenerateTechSpec } from './tech-lead.js';

// In-memory session store — keyed by Telegram chat_id
const sessions = new Map<number, ProjectSession>();

const MAX_BA_ROUNDS = 4;

// ─── Session Management ──────────────────────────────────────────────────────

export function getSession(chatId: number): ProjectSession | undefined {
  return sessions.get(chatId);
}

export function createSession(chatId: number, requirement: string): ProjectSession {
  const session: ProjectSession = {
    project_id: uuidv4(),
    session_id: uuidv4(),
    chat_id: chatId,
    state: 'BA_CLARIFYING',
    original_requirement: requirement,
    ba_messages: [],
    clarification_rounds: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  sessions.set(chatId, session);
  return session;
}

export function clearSession(chatId: number): void {
  sessions.delete(chatId);
}

// ─── Message Envelope Builder ─────────────────────────────────────────────────
// All inter-agent messages use this structured envelope.

function buildMessage<T>(
  type: AgentMessage['type'],
  from: AgentMessage['from'],
  to: AgentMessage['to'],
  payload: T,
  session: ProjectSession
): AgentMessage<T> {
  return {
    type,
    from,
    to,
    payload,
    metadata: {
      timestamp: new Date().toISOString(),
      project_id: session.project_id,
      session_id: session.session_id,
      version: '1.0',
    },
  };
}

// ─── Pipeline Steps ──────────────────────────────────────────────────────────

/**
 * Step 1: Start new project — send initial requirement to BA.
 * Returns either a clarification request (more questions) or triggers the pipeline.
 */
export async function startProject(
  chatId: number,
  requirement: string,
  onProgress: (msg: string) => Promise<void>,
  onClarify: (questions: string[], analysis: string, iteration: number) => Promise<void>,
  onDocument: (type: string, chunks: string[]) => Promise<void>,
  onComplete: () => Promise<void>,
  onError: (err: string) => Promise<void>
): Promise<void> {
  const session = createSession(chatId, requirement);

  await onProgress('🤔 *BA is analyzing your requirement\\.\\.\\.*');

  try {
    // Build REQUIREMENT_INPUT message
    const inputMsg = buildMessage(
      'REQUIREMENT_INPUT',
      'USER',
      'BA',
      { raw_requirement: requirement },
      session
    );
    console.log('[Orchestrator→BA]', JSON.stringify(inputMsg, null, 2));

    const baResponse = await baProcessInitial(session);
    await handleBAResponse(
      baResponse, session, onProgress, onClarify, onDocument, onComplete, onError
    );
  } catch (err) {
    session.state = 'COMPLETE';
    await onError(`BA agent error: ${String(err)}`);
  }
}

/**
 * Step 1b: User replied with clarification answers.
 */
export async function handleClarificationAnswer(
  chatId: number,
  answers: string,
  onProgress: (msg: string) => Promise<void>,
  onClarify: (questions: string[], analysis: string, iteration: number) => Promise<void>,
  onDocument: (type: string, chunks: string[]) => Promise<void>,
  onComplete: () => Promise<void>,
  onError: (err: string) => Promise<void>
): Promise<void> {
  const session = sessions.get(chatId);
  if (!session || session.state !== 'BA_CLARIFYING') {
    await onError('No active BA session. Start a new project with your requirement.');
    return;
  }

  // Record answers in current clarification round
  const lastRound = session.clarification_rounds[session.clarification_rounds.length - 1];
  if (lastRound) {
    lastRound.answers = answers;
  }

  session.updated_at = new Date().toISOString();

  // Build CLARIFICATION_RESPONSE message
  const responseMsg = buildMessage(
    'CLARIFICATION_RESPONSE',
    'USER',
    'BA',
    { answers },
    session
  );
  console.log('[USER→BA]', JSON.stringify(responseMsg, null, 2));

  await onProgress('🤔 *BA is reviewing your answers\\.\\.\\.*');

  try {
    const baResponse = await baProcessClarification(session, answers);
    await handleBAResponse(
      baResponse, session, onProgress, onClarify, onDocument, onComplete, onError
    );
  } catch (err) {
    session.state = 'COMPLETE';
    await onError(`BA agent error: ${String(err)}`);
  }
}

// ─── Internal Handlers ───────────────────────────────────────────────────────

async function handleBAResponse(
  response: BAResponse,
  session: ProjectSession,
  onProgress: (msg: string) => Promise<void>,
  onClarify: (questions: string[], analysis: string, iteration: number) => Promise<void>,
  onDocument: (type: string, chunks: string[]) => Promise<void>,
  onComplete: () => Promise<void>,
  onError: (err: string) => Promise<void>
): Promise<void> {
  if (response.status === 'NEEDS_CLARIFICATION') {
    // Record the clarification round
    session.clarification_rounds.push({
      iteration: response.iteration,
      questions: response.questions,
    });
    session.state = 'BA_CLARIFYING';
    session.updated_at = new Date().toISOString();

    // Build CLARIFICATION_REQUEST message
    const clarifyMsg = buildMessage(
      'CLARIFICATION_REQUEST',
      'BA',
      'USER',
      response,
      session
    );
    console.log('[BA→USER]', JSON.stringify(clarifyMsg, null, 2));

    await onClarify(response.questions, response.analysis, response.iteration);
    return;
  }

  // Requirements confirmed — record BRD
  session.brd = response.brd;
  session.updated_at = new Date().toISOString();

  const confirmedMsg = buildMessage(
    'REQUIREMENTS_CONFIRMED',
    'BA',
    'ORCHESTRATOR',
    { brd: response.brd },
    session
  );
  console.log('[BA→ORCHESTRATOR]', JSON.stringify(confirmedMsg.metadata, null, 2));

  // Run the downstream pipeline
  await runPipeline(session, onProgress, onDocument, onComplete, onError);
}

async function runPipeline(
  session: ProjectSession,
  onProgress: (msg: string) => Promise<void>,
  onDocument: (type: string, chunks: string[]) => Promise<void>,
  onComplete: () => Promise<void>,
  onError: (err: string) => Promise<void>
): Promise<void> {
  const { brd } = session;
  if (!brd) {
    await onError('BRD is missing — cannot start pipeline.');
    return;
  }

  // ── SA ────────────────────────────────────────────────────────────────────
  try {
    session.state = 'SA_PROCESSING';
    await onProgress('🏗️ *Solution Architect is designing the architecture\\.\\.\\.*');

    const architecture = await saGenerateArchitecture(brd);
    session.architecture = architecture;
    session.updated_at = new Date().toISOString();

    const archMsg = buildMessage('ARCHITECTURE_DOCUMENT', 'SA', 'ORCHESTRATOR', architecture, session);
    console.log('[SA→ORCHESTRATOR]', JSON.stringify(archMsg.metadata, null, 2));

    const { formatArchitectureSummary } = await import('../utils/formatter.js');
    await onDocument('Architecture Document', formatArchitectureSummary(architecture));
  } catch (err) {
    await onError(`SA agent error: ${String(err)}`);
    return;
  }

  // ── PM ────────────────────────────────────────────────────────────────────
  try {
    session.state = 'PM_PROCESSING';
    await onProgress('📅 *Project Manager is creating the project plan\\.\\.\\.*');

    const projectPlan = await pmGenerateProjectPlan(brd, session.architecture!);
    session.project_plan = projectPlan;
    session.updated_at = new Date().toISOString();

    const planMsg = buildMessage('PROJECT_PLAN', 'PM', 'ORCHESTRATOR', projectPlan, session);
    console.log('[PM→ORCHESTRATOR]', JSON.stringify(planMsg.metadata, null, 2));

    const { formatProjectPlanSummary } = await import('../utils/formatter.js');
    await onDocument('Project Plan', formatProjectPlanSummary(projectPlan));
  } catch (err) {
    await onError(`PM agent error: ${String(err)}`);
    return;
  }

  // ── Tech Lead ─────────────────────────────────────────────────────────────
  try {
    session.state = 'TECH_LEAD_PROCESSING';
    await onProgress('⚙️ *Tech Lead is writing the technical specification\\.\\.\\.*');

    const techSpec = await techLeadGenerateTechSpec(brd, session.architecture!, session.project_plan!);
    session.tech_spec = techSpec;
    session.updated_at = new Date().toISOString();

    const specMsg = buildMessage('TECHNICAL_SPEC', 'TECH_LEAD', 'ORCHESTRATOR', techSpec, session);
    console.log('[TECH_LEAD→ORCHESTRATOR]', JSON.stringify(specMsg.metadata, null, 2));

    const { formatTechSpecSummary } = await import('../utils/formatter.js');
    await onDocument('Technical Specification', formatTechSpecSummary(techSpec));
  } catch (err) {
    await onError(`Tech Lead agent error: ${String(err)}`);
    return;
  }

  // ── Complete ──────────────────────────────────────────────────────────────
  session.state = 'COMPLETE';
  session.updated_at = new Date().toISOString();

  const completeMsg = buildMessage('PIPELINE_COMPLETE', 'ORCHESTRATOR', 'USER', {}, session);
  console.log('[ORCHESTRATOR→USER]', JSON.stringify(completeMsg.metadata, null, 2));

  await onComplete();
}
