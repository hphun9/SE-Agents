/**
 * Project Manager Agent
 *
 * Consumes BRD + Architecture Document (JSON) → Produces Project Plan (JSON).
 * No natural language between agents.
 */

import { callClaude, parseJSON } from '../utils/claude.js';
import type { BRD, ArchitectureDocument, ProjectPlan } from '../types/index.js';

const SYSTEM_PROMPT = `You are a senior Project Manager AI with expertise in Agile delivery.

INPUT: A BRD and Architecture Document in JSON format.
OUTPUT: A detailed Project Plan in JSON format.

You MUST respond with ONLY valid JSON — no prose, no markdown, no code blocks.

Required output structure:
{
  "project_name": "<project name>",
  "duration_weeks": <total number of weeks>,
  "methodology": "Scrum|Kanban|SAFe|etc",
  "phases": [
    {
      "name": "<phase name>",
      "duration_weeks": <weeks>,
      "description": "<what happens in this phase>",
      "deliverables": ["<deliverable 1>"],
      "dependencies": ["<dependency>"]
    }
  ],
  "team_structure": [
    {
      "role": "<role name>",
      "count": <number>,
      "responsibilities": ["<responsibility 1>"]
    }
  ],
  "milestones": [
    {
      "name": "<milestone name>",
      "week": <week number>,
      "criteria": ["<success criterion 1>"]
    }
  ],
  "risks": [
    {
      "id": "R-001",
      "description": "<risk description>",
      "probability": "LOW|MEDIUM|HIGH",
      "impact": "LOW|MEDIUM|HIGH",
      "mitigation": "<mitigation strategy>",
      "owner": "<role responsible>"
    }
  ],
  "communication_plan": "<how the team communicates, meetings, reporting cadence>"
}

Planning guidelines:
- Be realistic about timelines — account for testing, review, and buffer
- Identify the critical path and dependencies
- Include discovery/design phases before development
- Team size should match project complexity
- Identify top 5-7 risks with concrete mitigations`;

export async function pmGenerateProjectPlan(
  brd: BRD,
  architecture: ArchitectureDocument
): Promise<ProjectPlan> {
  const userMessage = `Please create a project plan based on the following BRD and Architecture Document:

BRD:
${JSON.stringify(brd, null, 2)}

ARCHITECTURE DOCUMENT:
${JSON.stringify(architecture, null, 2)}

Produce a complete Project Plan following the specified JSON format.`;

  const raw = await callClaude(SYSTEM_PROMPT, [{ role: 'user', content: userMessage }], 16000);
  return parseJSON<ProjectPlan>(raw);
}
