/**
 * Solution Architect Agent
 *
 * Consumes BRD (JSON) → Produces Architecture Document (JSON).
 * No natural language between agents.
 */

import { callClaude, parseJSON } from '../utils/claude.js';
import type { BRD, ArchitectureDocument } from '../types/index.js';

const SYSTEM_PROMPT = `You are a senior Solution Architect AI. You design robust, scalable software architectures.

INPUT: A Business Requirements Document (BRD) in JSON format.
OUTPUT: A detailed Architecture Document in JSON format.

You MUST respond with ONLY valid JSON — no prose, no markdown, no code blocks.

Required output structure:
{
  "system_overview": "<comprehensive system overview>",
  "architecture_pattern": "<e.g., Microservices, Monolith, Event-Driven, etc.>",
  "tech_stack": [
    {
      "layer": "Frontend|Backend|Database|Cache|Queue|Infrastructure|etc",
      "technology": "<technology name>",
      "version": "<recommended version>",
      "rationale": "<why this technology was chosen>"
    }
  ],
  "components": [
    {
      "name": "<component name>",
      "type": "Service|Module|Library|Gateway|etc",
      "responsibility": "<what this component does>",
      "interfaces": ["<API or interface exposed>"],
      "dependencies": ["<other component names it depends on>"]
    }
  ],
  "data_flow": "<description of how data flows through the system>",
  "infrastructure": ["<infrastructure requirement 1>", "<infrastructure requirement 2>"],
  "security_considerations": ["<security measure 1>", "<security measure 2>"],
  "scalability_notes": "<how the system scales under load>",
  "adrs": [
    {
      "id": "ADR-001",
      "title": "<decision title>",
      "status": "PROPOSED|ACCEPTED|DEPRECATED",
      "context": "<why this decision was needed>",
      "decision": "<what was decided>",
      "consequences": ["<consequence 1>", "<consequence 2>"]
    }
  ]
}

Design principles to follow:
- Choose technologies appropriate to the project scale and requirements
- Consider security, scalability, and maintainability
- Document key architectural decisions as ADRs
- Ensure the architecture satisfies all functional and non-functional requirements`;

export async function saGenerateArchitecture(brd: BRD): Promise<ArchitectureDocument> {
  const userMessage = `Please design the architecture for this project based on the following BRD:

${JSON.stringify(brd, null, 2)}

Produce a complete Architecture Document following the specified JSON format.`;

  const raw = await callClaude(SYSTEM_PROMPT, [{ role: 'user', content: userMessage }], 16000);
  return parseJSON<ArchitectureDocument>(raw);
}
