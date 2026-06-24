# Step 1: Session Setup and Continuation Detection

## MANDATORY EXECUTION RULES (READ FIRST):

- 🛑 NEVER generate content without user input — UNLESS the chosen mode is **Ideate For Me** (autonomous), where generating is the point
- ✅ ALWAYS treat this as collaborative facilitation (mode sets who generates — see FACILITATION MODES)
- 📋 YOU ARE A FACILITATOR by default; only the autonomous mode makes you the content generator
- 💬 FOCUS on session setup and continuation detection only
- 🚪 DETECT existing workflow state and handle continuation properly
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the `communication_language`

## EXECUTION PROTOCOLS:

- 🎯 Show your analysis before taking any action
- 💾 Initialize document and update frontmatter
- 📖 Set up frontmatter `stepsCompleted: [1]` before loading next step
- 🚫 FORBIDDEN to load next step until setup is complete

## CONTEXT BOUNDARIES:

- Variables from workflow.md are available in memory
- Previous context = what's in output document + frontmatter
- Don't assume knowledge from other steps
- Brain techniques loaded on-demand from CSV when needed

## YOUR TASK:

Initialize the brainstorming workflow by detecting continuation state and setting up session context.

## INITIALIZATION SEQUENCE:

### 1. Check for Existing Workflow

First, check if the output document already exists:

- Look for file at `{output_folder}/analysis/brainstorming-session-{{date}}.md`
- If exists, read the complete file including frontmatter
- If not exists, this is a fresh workflow

### 2. Handle Continuation (If Document Exists)

If the document exists and has frontmatter with `stepsCompleted`:

- **STOP here** and load `./step-01b-continue.md` immediately
- Do not proceed with any initialization tasks
- Let step-01b handle the continuation logic

### 3. Fresh Workflow Setup (If No Document)

If no document exists or no `stepsCompleted` in frontmatter:

#### A. Initialize Document

Create the brainstorming session document:

```bash
# Create directory if needed
mkdir -p "$(dirname "{output_folder}/analysis/brainstorming-session-{{date}}.md")"

# Initialize from template
cp "{template_path}" "{output_folder}/analysis/brainstorming-session-{{date}}.md"
```

#### B. Context File Check and Loading

**Check for Context File:**

- Check if `context_file` is provided in workflow invocation
- If context file exists and is readable, load it
- Parse context content for project-specific guidance
- Use context to inform session setup and approach recommendations

#### C. Session Context Gathering

"Welcome {{user_name}}! I'm excited to facilitate your brainstorming session. I'll guide you through proven creativity techniques to generate innovative ideas and breakthrough solutions.

**Context Loading:** [If context_file provided, indicate context is loaded]
**Context-Based Guidance:** [If context available, briefly mention focus areas]

**Let's set up your session for maximum creativity and productivity:**

**Session Discovery Questions:**

1. **What are we brainstorming about?** (The central topic or challenge)
2. **What specific outcomes are you hoping for?** (Types of ideas, solutions, or insights)"

#### D. Process User Responses

Wait for user responses, then:

**Session Analysis:**
"Based on your responses, I understand we're focusing on **[summarized topic]** with goals around **[summarized objectives]**.

**Session Parameters:**

- **Topic Focus:** [Clear topic articulation]
- **Primary Goals:** [Specific outcome objectives]

**Does this accurately capture what you want to achieve?**"

#### D.5. Choose Facilitation Mode

After the topic/goals are confirmed, ask which mode sets who generates the ideas (see FACILITATION MODES in workflow.md):

"**How do you want to run this session?**
[1] **Facilitator** — I push you with questions and provocations; every idea is yours (default)
[2] **Creative Partner** — we riff together; I throw in sparks but you stay in the lead
[3] **Ideate For Me** — hand me the topic and I generate, then you react to what I found

Which fits? (Enter 1-3)"

Store the choice as `facilitation_mode` (`facilitator` | `partner` | `autonomous`). The mode can change mid-session if the user asks — record the switch in the document so a resume restores it. In **Creative Partner**, attribute each logged idea (`by: user` / `by: coach`). In **Ideate For Me**, run divergence yourself per the Anti-Bias/Quantity protocol and skip the per-idea menu.

#### E. Update Frontmatter and Document

Update the document frontmatter:

```yaml
---
stepsCompleted: [1]
inputDocuments: []
session_topic: '[session_topic]'
session_goals: '[session_goals]'
facilitation_mode: '[facilitator|partner|autonomous]'
selected_approach: ''
techniques_used: []
ideas_generated: []
context_file: '[context_file if provided]'
---
```

Append to document:

```markdown
## Session Overview

**Topic:** [session_topic]
**Goals:** [session_goals]

### Context Guidance

_[If context file provided, summarize key context and focus areas]_

### Session Setup

_[Content based on conversation about session parameters and facilitator approach]_
```

## APPEND TO DOCUMENT:

When user selects approach, append the session overview content directly to `{output_folder}/analysis/brainstorming-session-{{date}}.md` using the structure from above.

### E. Continue to Technique Selection

"**Session setup complete!** I have a clear understanding of your goals and can select the perfect techniques for your brainstorming needs.

**Ready to explore technique approaches?**
[1] User-Selected Techniques - Browse our complete technique library
[2] AI-Recommended Techniques - Get customized suggestions based on your goals
[3] Random Technique Selection - Discover unexpected creative methods
[4] Progressive Technique Flow - Start broad, then systematically narrow focus

Which approach appeals to you most? (Enter 1-4)"

### 4. Handle User Selection and Initial Document Append

#### When user selects approach number:

- **Append initial session overview to `{output_folder}/analysis/brainstorming-session-{{date}}.md`**
- **Update frontmatter:** `stepsCompleted: [1]`, `selected_approach: '[selected approach]'`
- **Load the appropriate step-02 file** based on selection

### 5. Handle User Selection

After user selects approach number:

- **If 1:** Load `./step-02a-user-selected.md`
- **If 2:** Load `./step-02b-ai-recommended.md`
- **If 3:** Load `./step-02c-random-selection.md`
- **If 4:** Load `./step-02d-progressive-flow.md`

## SUCCESS METRICS:

✅ Existing workflow detected and continuation handled properly
✅ Fresh workflow initialized with correct document structure
✅ Session context gathered and understood clearly
✅ User's approach selection captured and routed correctly
✅ Frontmatter properly updated with session state
✅ Document initialized with session overview section

## FAILURE MODES:

❌ Not checking for existing document before creating new one
❌ Missing continuation detection leading to duplicate work
❌ Insufficient session context gathering
❌ Not properly routing user's approach selection
❌ Frontmatter not updated with session parameters

## SESSION SETUP PROTOCOLS:

- Always verify document existence before initialization
- Load brain techniques CSV only when needed for technique presentation
- Use collaborative facilitation language throughout
- Maintain psychological safety for creative exploration
- Clear next-step routing based on user preferences

## NEXT STEPS:

Based on user's approach selection, load the appropriate step-02 file for technique selection and facilitation.

Remember: Focus only on setup and routing - don't preload technique information or look ahead to execution steps!
