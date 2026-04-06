/**
 * Tech Lead Agent
 *
 * Consumes BRD + Architecture + Project Plan (JSON) → Produces Technical Spec (JSON).
 * No natural language between agents.
 */

import { callClaude, parseJSON } from '../utils/claude.js';
import type { BRD, ArchitectureDocument, ProjectPlan, TechnicalSpec } from '../types/index.js';

const SYSTEM_PROMPT = `You are a senior Tech Lead AI with deep expertise in software engineering.

INPUT: BRD, Architecture Document, and Project Plan in JSON format.
OUTPUT: A comprehensive Technical Specification in JSON format.

You MUST respond with ONLY valid JSON — no prose, no markdown, no code blocks.

Required output structure:
{
  "overview": "<technical overview of the implementation approach>",
  "coding_standards": ["<standard 1>", "<standard 2>"],
  "development_workflow": "<git branching strategy, PR process, code review requirements>",
  "api_design": [
    {
      "method": "GET|POST|PUT|PATCH|DELETE",
      "path": "/api/v1/resource",
      "description": "<what this endpoint does>",
      "auth_required": true,
      "request_schema": { "field": "type" },
      "response_schema": { "field": "type" }
    }
  ],
  "data_models": [
    {
      "name": "<ModelName>",
      "description": "<what this model represents>",
      "fields": [
        {
          "name": "<fieldName>",
          "type": "string|number|boolean|Date|uuid|etc",
          "required": true,
          "description": "<field purpose>"
        }
      ],
      "relationships": ["<relationship description>"],
      "indexes": ["<field to index>"]
    }
  ],
  "technical_dependencies": [
    {
      "name": "<package name>",
      "version": "<version>",
      "purpose": "<why this dependency is needed>",
      "license": "<license type>"
    }
  ],
  "sprint_plan": [
    {
      "sprint": 1,
      "goal": "<sprint goal>",
      "user_stories": ["US-001", "US-002"],
      "story_points": <total points>
    }
  ],
  "definition_of_done": ["<criterion 1>", "<criterion 2>"],
  "testing_strategy": "<unit, integration, e2e testing approach and coverage targets>"
}

Technical standards:
- Design RESTful APIs with consistent naming conventions
- Define all key data models with proper field types
- Map user stories to sprints realistically (2-week sprints, 20-40 pts each)
- Include comprehensive definition of done
- Specify testing strategy with coverage targets`;

export async function techLeadGenerateTechSpec(
  brd: BRD,
  architecture: ArchitectureDocument,
  projectPlan: ProjectPlan
): Promise<TechnicalSpec> {
  const userMessage = `Please create a Technical Specification based on the following documents:

BRD:
${JSON.stringify(brd, null, 2)}

ARCHITECTURE DOCUMENT:
${JSON.stringify(architecture, null, 2)}

PROJECT PLAN:
${JSON.stringify(projectPlan, null, 2)}

Produce a complete Technical Specification following the specified JSON format.`;

  const raw = await callClaude(
    SYSTEM_PROMPT,
    [{ role: 'user', content: userMessage }],
    16000
  );
  return parseJSON<TechnicalSpec>(raw);
}
