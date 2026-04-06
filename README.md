# 🏗️ The Dev Agency: AI Software Development Team

> **A complete software development agency at your fingertips** — From business analysts who interrogate requirements to DevOps engineers who automate everything. Each agent is a battle-tested specialist with deep domain expertise, proven workflows, and measurable deliverables.

---

## 🚀 What Is This?

**The Dev Agency** is a collection of meticulously crafted AI agent personalities covering the **full software development lifecycle (SDLC)**. Each agent embodies a real-world role with:

- **🎯 Deep Specialization**: Not generic prompts — real domain expertise with workflows
- **🧠 Personality & Voice**: Unique communication style matching the role
- **📋 Concrete Deliverables**: Templates, code examples, and measurable outputs
- **✅ Process-Driven**: Step-by-step workflows from real-world methodologies
- **🔄 Collaborative**: Agents reference each other's outputs as inputs

---

## ⚡ Quick Start

### Use with Claude Code
```bash
cp -r dev-agency/* ~/.claude/agents/
# "Activate the Business Analyst agent and help me gather requirements for a new e-commerce platform"
```

### Use with Cursor
```bash
cp dev-agency/**/*.md .cursor/rules/
```

### Use as Reference
Browse each agent file — copy/adapt the workflows and deliverables you need.

---

## 🎨 The Dev Agency Roster

### 📊 Business Analysis Division
Turning chaos into clarity — understanding the "what" and "why" before anyone writes code.

| Agent | Specialty | When to Use |
|-------|-----------|-------------|
| 📋 [Business Analyst](business-analysis/ba-business-analyst.md) | Requirements engineering, stakeholder management, process modeling | Requirements gathering, user stories, BRD/SRS documents |
| 🔍 [Product Owner](business-analysis/ba-product-owner.md) | Backlog ownership, acceptance criteria, value prioritization | Sprint planning, backlog grooming, feature prioritization |

### 🏛️ Solution Architecture Division
Designing systems that scale, survive, and evolve.

| Agent | Specialty | When to Use |
|-------|-----------|-------------|
| 🏗️ [Solution Architect](solution-architecture/sa-solution-architect.md) | System design, technology selection, NFRs, integration patterns | Architecture decisions, tech stack selection, system design docs |
| 🔐 [Security Architect](solution-architecture/sa-security-architect.md) | Threat modeling, auth design, compliance, OWASP | Security reviews, auth flows, compliance requirements |
| 📐 [Data Architect](solution-architecture/sa-data-architect.md) | Data modeling, database design, migration strategy, ETL | Schema design, data flow, database selection, migration planning |

### 🎬 Project Management Division
Delivering on time, on scope, on budget.

| Agent | Specialty | When to Use |
|-------|-----------|-------------|
| 📅 [Project Manager](project-management/pm-project-manager.md) | Planning, risk management, stakeholder communication, budgets | Project kickoff, status reporting, risk mitigation, resource planning |
| 🏃 [Scrum Master](project-management/pm-scrum-master.md) | Agile ceremonies, impediment removal, team health, velocity | Sprint ceremonies, retrospectives, process improvement |
| 🗺️ [Technical Program Manager](project-management/pm-technical-program-manager.md) | Cross-team coordination, dependency management, release planning | Multi-team programs, release trains, dependency tracking |

### 💻 Development Division
Building the thing right — clean, tested, documented code.

| Agent | Specialty | When to Use |
|-------|-----------|-------------|
| 🎨 [Frontend Developer](development/dev-frontend.md) | React/Vue/Angular, state management, responsive design, a11y | UI implementation, SPA development, component libraries |
| 🏗️ [Backend Developer](development/dev-backend.md) | API design, microservices, databases, message queues, caching | REST/GraphQL APIs, server-side logic, data processing |
| 📱 [Fullstack Developer](development/dev-fullstack.md) | End-to-end features, rapid prototyping, vertical slices | Full feature delivery, MVPs, startup-speed development |
| ⚡ [Tech Lead](development/dev-tech-lead.md) | Code reviews, mentoring, technical decisions, standards | Architecture enforcement, PR reviews, team standards |

### 🧪 Quality Assurance Division
Breaking things before users do — systematically.

| Agent | Specialty | When to Use |
|-------|-----------|-------------|
| 🔍 [QA Engineer](quality-assurance/qa-engineer.md) | Test planning, manual/exploratory testing, bug reporting | Test case design, regression testing, UAT coordination |
| 🤖 [Automation Engineer](quality-assurance/qa-automation-engineer.md) | Selenium/Playwright/Cypress, CI integration, test frameworks | E2E test automation, API testing, test pipeline setup |
| ⚡ [Performance Tester](quality-assurance/qa-performance-tester.md) | Load testing, stress testing, profiling, bottleneck analysis | JMeter/k6/Gatling, performance benchmarks, capacity planning |

### 🚀 DevOps & Infrastructure Division
Automate everything, monitor everything, recover from everything.

| Agent | Specialty | When to Use |
|-------|-----------|-------------|
| 🔧 [DevOps Engineer](devops/devops-engineer.md) | CI/CD, Docker, Kubernetes, IaC, monitoring | Pipeline setup, containerization, deployment automation |
| ☁️ [Cloud Architect](devops/devops-cloud-architect.md) | AWS/Azure/GCP, cost optimization, multi-cloud | Cloud migration, infrastructure design, cost analysis |
| 🛡️ [SRE](devops/devops-sre.md) | SLOs/SLIs, incident response, chaos engineering, observability | Production reliability, on-call processes, postmortems |

---

## 🔄 SDLC Workflow: How Agents Collaborate

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│  Business    │────▶│  Solution    │────▶│  Project       │
│  Analyst     │     │  Architect   │     │  Manager       │
│  + Product   │     │  + Security  │     │  + Scrum       │
│    Owner     │     │  + Data      │     │    Master      │
└─────────────┘     └──────────────┘     └────────────────┘
                                                  │
                         ┌────────────────────────┘
                         ▼
              ┌─────────────────────┐
              │  Development        │
              │  Frontend + Backend │
              │  + Tech Lead        │
              └─────────┬───────────┘
                        │
              ┌─────────▼───────────┐
              │  Quality Assurance  │
              │  QA + Automation    │
              │  + Performance      │
              └─────────┬───────────┘
                        │
              ┌─────────▼───────────┐
              │  DevOps / SRE       │
              │  CI/CD + Cloud      │
              │  + Monitoring       │
              └─────────────────────┘
```

### Scenario: Building an E-Commerce Platform

1. **Business Analyst** → Gathers requirements, creates user stories & BRD
2. **Product Owner** → Prioritizes backlog, defines acceptance criteria
3. **Solution Architect** → Designs system architecture, selects tech stack
4. **Security Architect** → Threat models auth, payment, data flows
5. **Data Architect** → Designs DB schema, data migration plan
6. **Project Manager** → Creates WBS, timeline, resource plan
7. **Scrum Master** → Sets up sprints, ceremonies, team agreements
8. **Tech Lead** → Defines coding standards, PR process, branching strategy
9. **Frontend Developer** → Builds UI components, pages, state management
10. **Backend Developer** → Builds APIs, business logic, integrations
11. **QA Engineer** → Writes test cases, executes regression & UAT
12. **Automation Engineer** → Automates E2E tests, integrates into CI
13. **Performance Tester** → Load tests checkout flow, identifies bottlenecks
14. **DevOps Engineer** → Sets up CI/CD, containers, monitoring
15. **SRE** → Defines SLOs, sets up alerting, runs game days

---

## 📜 License

MIT License — Use freely. Attribution appreciated.
