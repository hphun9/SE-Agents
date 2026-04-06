import type {
  BRD,
  ArchitectureDocument,
  ProjectPlan,
  TechnicalSpec,
  ClarificationRequestPayload,
} from '../types/index.js';

const MAX_MSG = 4000; // Telegram limit is 4096, leave buffer

/** Split a long string into Telegram-safe chunks */
export function splitMessage(text: string): string[] {
  if (text.length <= MAX_MSG) return [text];

  const chunks: string[] = [];
  let current = '';

  for (const line of text.split('\n')) {
    const addition = (current ? '\n' : '') + line;
    if (current.length + addition.length > MAX_MSG) {
      chunks.push(current);
      current = line;
    } else {
      current += addition;
    }
  }
  if (current) chunks.push(current);
  return chunks;
}

/** Format clarification questions for Telegram */
export function formatClarificationRequest(payload: ClarificationRequestPayload): string {
  const lines: string[] = [
    `🔍 *Requirements Analysis — Round ${payload.iteration}*`,
    '',
    `📋 *What I understand:*`,
    payload.analysis,
    '',
    `❓ *I need some clarification:*`,
  ];

  payload.questions.forEach((q, i) => {
    lines.push(`${i + 1}\\. ${escapeMarkdown(q)}`);
  });

  lines.push('', '_Please answer all questions in one message\\._');
  return lines.join('\n');
}

/** Format BRD summary for Telegram */
export function formatBRDSummary(brd: BRD): string[] {
  const lines: string[] = [
    `✅ *Business Requirements Document*`,
    `📌 *${escapeMarkdown(brd.title)}*`,
    '',
    `*Overview*`,
    escapeMarkdown(brd.overview),
    '',
    `*Goals*`,
    ...brd.goals.map((g) => `• ${escapeMarkdown(g)}`),
    '',
    `*Functional Requirements \\(${brd.functional_requirements.length}\\)*`,
    ...brd.functional_requirements.slice(0, 5).map(
      (r) => `• \\[${r.priority}\\] ${escapeMarkdown(r.title)}`
    ),
    brd.functional_requirements.length > 5
      ? `_\\.\\.\\. and ${brd.functional_requirements.length - 5} more_`
      : '',
    '',
    `*User Stories \\(${brd.user_stories.length}\\)*`,
    ...brd.user_stories.slice(0, 3).map(
      (s) => `• As a ${escapeMarkdown(s.as_a)}, I want ${escapeMarkdown(s.i_want)}`
    ),
  ].filter((l) => l !== '');

  return splitMessage(lines.join('\n'));
}

/** Format Architecture Document summary for Telegram */
export function formatArchitectureSummary(doc: ArchitectureDocument): string[] {
  const lines: string[] = [
    `🏗️ *Architecture Document*`,
    '',
    `*Pattern:* ${escapeMarkdown(doc.architecture_pattern)}`,
    '',
    `*Overview*`,
    escapeMarkdown(doc.system_overview),
    '',
    `*Tech Stack*`,
    ...doc.tech_stack.map(
      (t) => `• *${escapeMarkdown(t.layer)}*: ${escapeMarkdown(t.technology)} — ${escapeMarkdown(t.rationale)}`
    ),
    '',
    `*Components \\(${doc.components.length}\\)*`,
    ...doc.components.map(
      (c) => `• *${escapeMarkdown(c.name)}* \\(${escapeMarkdown(c.type)}\\): ${escapeMarkdown(c.responsibility)}`
    ),
    '',
    `*Security Considerations*`,
    ...doc.security_considerations.map((s) => `• ${escapeMarkdown(s)}`),
    '',
    `*Architecture Decisions \\(${doc.adrs.length} ADRs\\)*`,
    ...doc.adrs.map(
      (a) => `• \\[${a.status}\\] ${escapeMarkdown(a.title)}`
    ),
  ];

  return splitMessage(lines.join('\n'));
}

/** Format Project Plan summary for Telegram */
export function formatProjectPlanSummary(plan: ProjectPlan): string[] {
  const lines: string[] = [
    `📅 *Project Plan*`,
    `📌 *${escapeMarkdown(plan.project_name)}*`,
    '',
    `*Methodology:* ${escapeMarkdown(plan.methodology)}`,
    `*Duration:* ${plan.duration_weeks} weeks`,
    '',
    `*Phases*`,
    ...plan.phases.map(
      (p) => `• *${escapeMarkdown(p.name)}* \\(${p.duration_weeks}w\\): ${escapeMarkdown(p.description)}`
    ),
    '',
    `*Team Structure*`,
    ...plan.team_structure.map(
      (t) => `• ${t.count}x *${escapeMarkdown(t.role)}*`
    ),
    '',
    `*Key Milestones*`,
    ...plan.milestones.map(
      (m) => `• Week ${m.week}: ${escapeMarkdown(m.name)}`
    ),
    '',
    `*Top Risks \\(${plan.risks.length}\\)*`,
    ...plan.risks.slice(0, 3).map(
      (r) => `• \\[${r.probability}/${r.impact}\\] ${escapeMarkdown(r.description)}`
    ),
  ];

  return splitMessage(lines.join('\n'));
}

/** Format Technical Spec summary for Telegram */
export function formatTechSpecSummary(spec: TechnicalSpec): string[] {
  const lines: string[] = [
    `⚙️ *Technical Specification*`,
    '',
    escapeMarkdown(spec.overview),
    '',
    `*Development Workflow*`,
    escapeMarkdown(spec.development_workflow),
    '',
    `*API Endpoints \\(${spec.api_design.length}\\)*`,
    ...spec.api_design.slice(0, 5).map(
      (e) => `• \`${e.method} ${escapeMarkdown(e.path)}\` — ${escapeMarkdown(e.description)}`
    ),
    spec.api_design.length > 5
      ? `_\\.\\.\\. and ${spec.api_design.length - 5} more_`
      : '',
    '',
    `*Data Models \\(${spec.data_models.length}\\)*`,
    ...spec.data_models.map(
      (m) => `• *${escapeMarkdown(m.name)}*: ${m.fields.length} fields`
    ),
    '',
    `*Sprint Plan \\(${spec.sprint_plan.length} sprints\\)*`,
    ...spec.sprint_plan.map(
      (s) => `• Sprint ${s.sprint} \\(${s.story_points}pts\\): ${escapeMarkdown(s.goal)}`
    ),
    '',
    `*Testing Strategy*`,
    escapeMarkdown(spec.testing_strategy),
    '',
    `*Definition of Done*`,
    ...spec.definition_of_done.map((d) => `• ${escapeMarkdown(d)}`),
  ].filter((l) => l !== '');

  return splitMessage(lines.join('\n'));
}

/** Escape special MarkdownV2 characters */
function escapeMarkdown(text: string): string {
  return text.replace(/[_*[\]()~`>#+\-=|{}.!\\]/g, '\\$&');
}
