// ─── Agent Roles ────────────────────────────────────────────────────────────

export type AgentRole = 'ORCHESTRATOR' | 'BA' | 'SA' | 'PM' | 'TECH_LEAD';

// ─── Inter-Agent Message Types ───────────────────────────────────────────────

export type MessageType =
  | 'REQUIREMENT_INPUT'       // USER → BA
  | 'CLARIFICATION_REQUEST'   // BA → USER
  | 'CLARIFICATION_RESPONSE'  // USER → BA
  | 'REQUIREMENTS_CONFIRMED'  // BA → ORCHESTRATOR
  | 'ARCHITECTURE_DOCUMENT'   // SA → ORCHESTRATOR
  | 'PROJECT_PLAN'            // PM → ORCHESTRATOR
  | 'TECHNICAL_SPEC'          // TECH_LEAD → ORCHESTRATOR
  | 'PIPELINE_COMPLETE';      // ORCHESTRATOR → USER

// ─── Structured Agent Message Envelope ──────────────────────────────────────
// All inter-agent communication uses this envelope — no natural language
// between agents. Natural language only appears in Telegram-facing output.

export interface AgentMessage<T = unknown> {
  type: MessageType;
  from: AgentRole | 'USER';
  to: AgentRole | 'USER';
  payload: T;
  metadata: {
    timestamp: string;
    project_id: string;
    session_id: string;
    version: '1.0';
  };
}

// ─── BA Agent Payloads ───────────────────────────────────────────────────────

export interface ClarificationRequestPayload {
  status: 'NEEDS_CLARIFICATION';
  analysis: string;            // What the BA understood so far
  questions: string[];         // Targeted questions for the user
  context: string;             // Why these questions are needed
  iteration: number;
}

export interface RequirementsConfirmedPayload {
  status: 'REQUIREMENTS_COMPLETE';
  brd: BRD;
}

export type BAResponse = ClarificationRequestPayload | RequirementsConfirmedPayload;

// ─── BRD (Business Requirements Document) ───────────────────────────────────

export interface BRD {
  title: string;
  overview: string;
  problem_statement: string;
  goals: string[];
  functional_requirements: FunctionalRequirement[];
  non_functional_requirements: NonFunctionalRequirement[];
  user_stories: UserStory[];
  stakeholders: string[];
  out_of_scope: string[];
  assumptions: string[];
  constraints: string[];
}

export interface FunctionalRequirement {
  id: string;
  title: string;
  description: string;
  priority: 'MUST' | 'SHOULD' | 'COULD' | 'WONT';
}

export interface NonFunctionalRequirement {
  category: string;
  requirement: string;
}

export interface UserStory {
  id: string;
  as_a: string;
  i_want: string;
  so_that: string;
  acceptance_criteria: string[];
}

// ─── Architecture Document ───────────────────────────────────────────────────

export interface ArchitectureDocument {
  system_overview: string;
  architecture_pattern: string;
  tech_stack: TechStackItem[];
  components: Component[];
  data_flow: string;
  infrastructure: string[];
  security_considerations: string[];
  scalability_notes: string;
  adrs: ADR[];
}

export interface TechStackItem {
  layer: string;
  technology: string;
  version?: string;
  rationale: string;
}

export interface Component {
  name: string;
  type: string;
  responsibility: string;
  interfaces: string[];
  dependencies: string[];
}

export interface ADR {
  id: string;
  title: string;
  status: 'PROPOSED' | 'ACCEPTED' | 'DEPRECATED';
  context: string;
  decision: string;
  consequences: string[];
}

// ─── Project Plan ────────────────────────────────────────────────────────────

export interface ProjectPlan {
  project_name: string;
  duration_weeks: number;
  methodology: string;
  phases: Phase[];
  team_structure: TeamMember[];
  milestones: Milestone[];
  risks: Risk[];
  communication_plan: string;
}

export interface Phase {
  name: string;
  duration_weeks: number;
  description: string;
  deliverables: string[];
  dependencies: string[];
}

export interface TeamMember {
  role: string;
  count: number;
  responsibilities: string[];
}

export interface Milestone {
  name: string;
  week: number;
  criteria: string[];
}

export interface Risk {
  id: string;
  description: string;
  probability: 'LOW' | 'MEDIUM' | 'HIGH';
  impact: 'LOW' | 'MEDIUM' | 'HIGH';
  mitigation: string;
  owner: string;
}

// ─── Technical Specification ─────────────────────────────────────────────────

export interface TechnicalSpec {
  overview: string;
  coding_standards: string[];
  development_workflow: string;
  api_design: APIEndpoint[];
  data_models: DataModel[];
  technical_dependencies: TechDependency[];
  sprint_plan: SprintEstimate[];
  definition_of_done: string[];
  testing_strategy: string;
}

export interface APIEndpoint {
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  path: string;
  description: string;
  auth_required: boolean;
  request_schema?: Record<string, unknown>;
  response_schema?: Record<string, unknown>;
}

export interface DataModel {
  name: string;
  description: string;
  fields: ModelField[];
  relationships: string[];
  indexes: string[];
}

export interface ModelField {
  name: string;
  type: string;
  required: boolean;
  description: string;
}

export interface TechDependency {
  name: string;
  version: string;
  purpose: string;
  license?: string;
}

export interface SprintEstimate {
  sprint: number;
  goal: string;
  user_stories: string[];
  story_points: number;
}

// ─── Session State ───────────────────────────────────────────────────────────

export type SessionState =
  | 'IDLE'
  | 'BA_CLARIFYING'    // BA is asking questions, waiting for user answers
  | 'SA_PROCESSING'
  | 'PM_PROCESSING'
  | 'TECH_LEAD_PROCESSING'
  | 'COMPLETE';

export interface ClarificationRound {
  iteration: number;
  questions: string[];
  answers?: string;
}

export interface ProjectSession {
  project_id: string;
  session_id: string;
  chat_id: number;
  state: SessionState;
  original_requirement: string;
  // BA conversation history — multi-turn Claude context
  ba_messages: Array<{ role: 'user' | 'assistant'; content: string }>;
  clarification_rounds: ClarificationRound[];
  // Documents produced by each agent
  brd?: BRD;
  architecture?: ArchitectureDocument;
  project_plan?: ProjectPlan;
  tech_spec?: TechnicalSpec;
  created_at: string;
  updated_at: string;
}
