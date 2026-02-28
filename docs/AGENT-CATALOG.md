# BMAD v6 Agent Catalog

BMAD v6 includes 34 specialist agents organized across 4 modules. Each agent has a persona with a unique name, communication style, domain expertise, and activation protocol. This catalog documents every agent, when to use them, and how to invoke them.

---

## Orchestration

### Oracle / Athena

- **Module**: BMM
- **Domain**: Project orchestration, lifecycle enforcement, sprint state management
- **When to use**: Every session. The Oracle is mandatory -- it activates first, reads sprint state, presents a project brief, and enforces the full implementation lifecycle (create-story, dev-story, code-review, ship). It translates high-level directives into workflow sequences and executes them directly. Routes to specialist agents for domain expertise.
- **Slash command**: `/bmad:bmm:agents:oracle`

### Navigator / Navi

- **Module**: BMM
- **Domain**: Project intelligence, sprint state tracking, agent routing, risk scanning
- **When to use**: When you need a quick project status briefing, next-action recommendation, risk scan, or session handoff summary. Navi reads sprint-status.yaml as the single source of truth, tracks all stories, and recommends next actions. Lighter weight than the full Oracle when you just need intelligence without workflow execution.
- **Slash command**: `/bmad:bmm:agents:navigator`

---

## Core Planning Team

### Analyst / Mary

- **Module**: BMM
- **Domain**: Business analysis, market research, competitive analysis, requirements elicitation
- **When to use**: When you need to create a product brief, analyze market dynamics, perform competitive research, or translate vague business needs into actionable specifications. Mary brings strategic business frameworks (Porter's Five Forces, SWOT, root cause analysis) and treats every analysis session like a treasure hunt for insights.
- **Slash command**: `/bmad:bmm:agents:analyst`

### Product Manager / John

- **Module**: BMM
- **Domain**: Product management, PRD creation, user interviews, requirement discovery, stakeholder alignment
- **When to use**: When creating or editing a PRD, conducting user research, defining product requirements, or making prioritization decisions. John asks "WHY?" relentlessly, applies Jobs-to-be-Done framework, and focuses on shipping the smallest thing that validates an assumption.
- **Slash command**: `/bmad:bmm:agents:pm`

### Architect / Winston

- **Module**: BMM
- **Domain**: System architecture, distributed systems, cloud infrastructure, API design, technology selection
- **When to use**: When designing system architecture, making technology selection decisions, reviewing scalability patterns, or creating architecture documents. Winston speaks in calm, pragmatic tones, balancing "what could be" with "what should be," and embraces boring technology for stability.
- **Slash command**: `/bmad:bmm:agents:architect`

### UX Designer / Sally

- **Module**: BMM
- **Domain**: User experience design, interaction design, user research, UI patterns
- **When to use**: When creating UX design documents, defining user journeys, planning interaction patterns, or reviewing UI decisions. Sally paints pictures with words, tells user stories that make you feel the problem, and advocates empathetically for genuine user needs.
- **Slash command**: `/bmad:bmm:agents:ux-designer`

### Scrum Master / Bob

- **Module**: BMM
- **Domain**: Agile ceremonies, story preparation, sprint planning, requirement clarity
- **When to use**: When preparing stories for development, ensuring alignment between PRD and implementation, managing sprint ceremonies, or resolving ambiguity in requirements. Bob is crisp and checklist-driven, with zero tolerance for ambiguity and strict boundaries between story preparation and implementation.
- **Slash command**: `/bmad:bmm:agents:sm`

---

## Implementation

### Developer / Amelia

- **Module**: BMM
- **Domain**: Full-stack software engineering, story implementation, test-driven development
- **When to use**: When implementing stories outside of the Oracle's dev-story workflow, or when you need a dedicated coding agent. Amelia follows strict adherence to acceptance criteria, uses the story file as single source of truth, and follows red-green-refactor cycles. Ultra-succinct -- speaks in file paths and AC IDs.
- **Slash command**: `/bmad:bmm:agents:dev`

### Tech Writer / Paige

- **Module**: BMM
- **Domain**: Technical documentation, CommonMark, DITA, OpenAPI, knowledge curation
- **When to use**: When creating or reviewing technical documentation, generating API docs, or curating knowledge bases. Paige transforms complex concepts into accessible, structured documentation with the patience of an educator explaining to a friend.
- **Slash command**: `/bmad:bmm:agents:tech-writer`

### Quick Flow Solo Dev / Barry

- **Module**: BMM
- **Domain**: Rapid development, tech spec creation, prototyping, lean implementation
- **When to use**: When you need quick implementation with minimum ceremony -- small features, prototypes, bug fixes, or spikes that do not warrant full story lifecycle overhead. Barry handles everything from tech spec creation through implementation with ruthless efficiency. "Code that ships is better than perfect code that doesn't."
- **Slash command**: `/bmad:bmm:agents:quick-flow-solo-dev`

---

## Quality and Testing

### Test Architect / Murat

- **Module**: BMM
- **Domain**: Test strategy, API testing, UI automation, CI/CD pipelines, quality gates, risk-based testing
- **When to use**: When designing test strategy, setting up test frameworks, reviewing test quality, creating CI/CD quality pipelines, or assessing non-functional requirements. Murat blends data with gut instinct, calculates risk vs. value for every testing decision, and treats flakiness as critical technical debt.
- **Slash command**: `/bmad:bmm:agents:tea`

### Custodian / Sentinel

- **Module**: BMM
- **Domain**: Code quality, pattern enforcement, repository health, dead code detection, migration auditing
- **When to use**: When you need a repo health check, pattern audit, dead code scan, migration review, PR review, or quality gate assessment. Sentinel knows every pattern in project-context.md, treats violations like incidents, and serves as the immune system of your repository. Never judgmental, always constructive.
- **Slash command**: `/bmad:bmm:agents:custodian`

---

## Infrastructure

### DevOps / Forge

- **Module**: BMM
- **Domain**: Docker, CI/CD pipelines, deployment, environment configuration, infrastructure
- **When to use**: When setting up or reviewing Docker configurations, designing CI/CD pipelines, managing environment variables, or troubleshooting deployment issues. Forge thinks in layers, caches, and pipelines, with a pragmatic infrastructure-as-code mindset.
- **Slash command**: `/bmad:bmm:agents:devops`

### API Contract / Pact

- **Module**: BMM
- **Domain**: OpenAPI specifications, frontend/backend API alignment, contract drift detection, schema comparison
- **When to use**: When you need to detect drift between backend routers and frontend API services, validate schema consistency, compare API contracts, or identify gaps in API coverage. Pact speaks in terms of contracts, schemas, and compatibility with precise endpoint paths and schema diffs.
- **Slash command**: `/bmad:bmm:agents:api-contract`

---

## Security and Compliance

### Security Auditor / Shield

- **Module**: BMM
- **Domain**: Application security, HIPAA compliance, multi-tenant data isolation, vulnerability scanning, RLS review
- **When to use**: When performing security audits, reviewing Row Level Security policies, checking HIPAA compliance, or scanning for vulnerabilities. Shield treats every tenant boundary as a potential breach vector. Methodical and evidence-based, categorizing findings by OWASP/HIPAA reference. Never alarmist, always actionable.
- **Slash command**: `/bmad:bmm:agents:security-auditor`

### NIST RMF Expert / Atlas

- **Module**: BMM
- **Domain**: NIST AI Risk Management Framework, compliance checking, risk assessment, trustworthiness analysis
- **When to use**: When you need guidance on NIST AI RMF compliance, risk classification, or assessment methodology. Atlas knows all 4 functions, 19 categories, and 72 subcategories of the framework. Cites specific subcategory IDs. Purely advisory -- never writes code.
- **Slash command**: `/bmad:bmm:agents:nist-rmf-expert`

---

## Domain Specialists

### Data Architect / Oracle

- **Module**: BMM
- **Domain**: SQL, PostgreSQL, KQL, Redis caching, data modeling, query optimization, analytics
- **When to use**: When reviewing data models, optimizing queries, designing caching strategies, planning database migrations, or analyzing query performance. Thinks in indexes, partitions, and cache invalidation strategies. Shows EXPLAIN ANALYZE output.
- **Slash command**: `/bmad:bmm:agents:data-architect`

### Agentic Expert / Nexus

- **Module**: BMM
- **Domain**: AI agent architecture, MCP, multi-agent orchestration, Claude SDK, OpenAI Assistants, LangChain/LangGraph
- **When to use**: When designing agentic AI workflows, evaluating AI frameworks, reviewing MCP tool configurations, or making build-vs-buy decisions for AI features. Nexus takes a pragmatic right-tool-for-the-job philosophy and always addresses cost, latency, and reliability trade-offs.
- **Slash command**: `/bmad:bmm:agents:agentic-expert`

### ML Expert / Neuron

- **Module**: BMM
- **Domain**: Machine learning, neural networks, model training, evaluation methodology, bias detection, MLOps
- **When to use**: When evaluating ML approaches, designing training pipelines, assessing model bias, reviewing evaluation methodology, or planning MLOps infrastructure. Neuron connects ML concepts to business outcomes with academic precision and practical grounding.
- **Slash command**: `/bmad:bmm:agents:ml-expert`

---

## Industry Advisors

### Healthcare Expert / Dr. Vita

- **Module**: BMM
- **Domain**: HIPAA, FDA SaMD, CDS requirements, clinical AI safety, healthcare AI governance
- **When to use**: When building healthcare applications and needing guidance on HIPAA compliance, FDA Software as Medical Device (SaMD) classification, Clinical Decision Support requirements, or clinical AI safety considerations. Cites specific CFR sections. Purely advisory -- never writes code.
- **Slash command**: `/bmad:bmm:agents:healthcare-expert`

### Government Expert / Senator

- **Module**: BMM
- **Domain**: Executive Order 14110, OMB M-24-10, FedRAMP, FISMA, AI use case inventories, federal AI policy
- **When to use**: When building government-facing AI applications and needing guidance on federal AI policy, executive orders, OMB memoranda, FedRAMP authorization, or AI use case inventory requirements. Translates policy into actionable requirements. Purely advisory.
- **Slash command**: `/bmad:bmm:agents:government-expert`

### Financial Expert / Sterling

- **Module**: BMM
- **Domain**: SOX, SEC AI guidance, BSA/AML, SR 11-7, fair lending, model risk management
- **When to use**: When building financial services applications and needing guidance on model risk management (SR 11-7), SEC AI disclosure requirements, fair lending testing, or regulatory expectations for AI in financial services. Risk-quantitative. Purely advisory.
- **Slash command**: `/bmad:bmm:agents:financial-expert`

---

## Creative Innovation Suite (CIS)

### Brainstorming Coach / Carson

- **Module**: CIS
- **Domain**: Brainstorming facilitation, creative techniques, ideation methods, group dynamics
- **When to use**: When you need structured brainstorming for new features, product ideas, or creative solutions. Carson facilitates sessions using diverse techniques (SCAMPER, mind mapping, reverse brainstorming, etc.) with high energy and "YES AND" improvisation style. Note: brainstorming outputs must flow through the pipeline (update epics/PRD, create stories) before implementation.
- **Slash command**: `/bmad:cis:agents:brainstorming-coach`

### Design Thinking Coach / Maya

- **Module**: CIS
- **Domain**: Human-centered design, empathy mapping, prototyping, user insights, design thinking methodology
- **When to use**: When you want to apply design thinking methodology (Empathize, Define, Ideate, Prototype, Test) to a product challenge. Maya has 15+ years of experience at Fortune 500s and startups, talks like a jazz musician improvising around themes, and challenges assumptions playfully.
- **Slash command**: `/bmad:cis:agents:design-thinking-coach`

### Creative Problem Solver / Dr. Quinn

- **Module**: CIS
- **Domain**: TRIZ, Theory of Constraints, Systems Thinking, root cause analysis, systematic problem solving
- **When to use**: When facing a complex or seemingly impossible challenge that needs systematic decomposition. Dr. Quinn applies structured problem-solving methodologies to crack challenges, hunting for root causes relentlessly. Speaks like Sherlock Holmes mixed with a playful scientist.
- **Slash command**: `/bmad:cis:agents:creative-problem-solver`

### Innovation Strategist / Victor

- **Module**: CIS
- **Domain**: Business model innovation, Jobs-to-be-Done, Blue Ocean Strategy, disruptive strategy
- **When to use**: When exploring market disruption opportunities, evaluating business model innovation, or developing competitive strategy. Victor architected billion-dollar pivots and speaks like a chess grandmaster with bold declarations and devastatingly simple questions.
- **Slash command**: `/bmad:cis:agents:innovation-strategist`

### Presentation Master / Caravaggio

- **Module**: CIS
- **Domain**: Visual communication, presentation design, Excalidraw frames, audience psychology, information design
- **When to use**: When creating presentations, pitch decks, visual explanations, or any visual communication that needs to be compelling. Caravaggio knows when to be bold and casual vs. polished and professional, and treats every project like a creative challenge.
- **Slash command**: `/bmad:cis:agents:presentation-master`

### Storyteller / Sophia

- **Module**: CIS
- **Domain**: Narrative strategy, emotional psychology, audience engagement, story frameworks, brand narratives
- **When to use**: When crafting compelling narratives for products, presentations, documentation, or marketing. Sophia has 50+ years across journalism, screenwriting, and brand narratives. Speaks like a bard weaving an epic tale -- every sentence draws you deeper.
- **Slash command**: `/bmad:cis:agents:storyteller`

---

## Builders (BMB)

### Agent Builder / Bond

- **Module**: BMB
- **Domain**: Agent design, persona development, BMAD compliance, agent architecture
- **When to use**: When creating new custom agents for your project. Bond guides you through an 8-step process: brainstorm, discovery, type/metadata, persona, commands/menu, activation, build, and celebration. Can create simple agents, expert agents, or module agents, all BMAD-compliant.
- **Slash command**: `/bmad:bmb:agents:agent-builder`

### Workflow Builder / Wendy

- **Module**: BMB
- **Domain**: Workflow architecture, process design, state management, workflow optimization
- **When to use**: When creating new custom workflows for your project. Wendy designs efficient, scalable workflows with clear entry/exit points, comprehensive error handling, and seamless BMAD integration.
- **Slash command**: `/bmad:bmb:agents:workflow-builder`

### Module Builder / Morgan

- **Module**: BMB
- **Domain**: Module architecture, integration patterns, end-to-end module development
- **When to use**: When creating entirely new BMAD modules (collections of agents and workflows that serve a specific domain). Morgan guides the full module lifecycle from brief through creation, handling structure, configuration, installers, agents, workflows, and documentation.
- **Slash command**: `/bmad:bmb:agents:module-builder`

---

## Core Platform

### BMad Master

- **Module**: Core
- **Domain**: BMAD platform operations, task execution, resource management, workflow orchestration
- **When to use**: When you need direct access to BMAD core operations like document indexing, document sharding, or runtime resource management. The Master is the primary execution engine for BMAD platform operations. Refers to himself in the 3rd person.
- **Slash command**: `/bmad:core:agents:bmad-master`

---

## Agent Count Summary

| Module | Agents |
|--------|--------|
| Core | 1 |
| BMM | 22 |
| BMB | 3 |
| CIS | 6 |
| **Total** | **32** |

Note: The total of 32 distinct agent files exists in the repository. Including the Oracle's routing capabilities and the 2 additional agents accessible through team configurations, the system provides access to 34 agent-level capabilities.
