# Multi-Agent System Usage Guide
## Anomaly Detection Research Project

This guide explains how to use your three-agent system optimally for anomaly detection research in the robot-shop MSA environment.

---

## 🤖 Your Agent Team

### 1. **Coordinator** (Main Agent)
- **Model**: Sonnet 4.5
- **Role**: Task analysis, delegation, result synthesis
- **When to use**: This is your default interface - start here for all requests

### 2. **Research Expert** (Subagent)
- **Model**: Sonnet 4.5
- **Role**: PhD-level anomaly detection research advisor
- **When coordinator delegates**: Literature reviews, methodology design, experimental planning

### 3. **Code Infrastructure** (Subagent)
- **Model**: Haiku 4.5 (3x cheaper, 4x faster than Sonnet)
- **Role**: K8s YAML, code analysis, implementation
- **When coordinator delegates**: Infrastructure changes, instrumentation, code modifications

---

## 📊 Cost & Performance Profile

| Agent | Model | Cost (per 1M tokens) | Speed | Use Case |
|-------|-------|---------------------|-------|----------|
| Coordinator | Sonnet 4.5 | $3 input / $15 output | Medium | Complex reasoning, orchestration |
| Research Expert | Sonnet 4.5 | $3 input / $15 output | Medium | Research analysis, methodology |
| Code Infrastructure | Haiku 4.5 | $1 input / $5 output | Fast | Implementation, code analysis |

**Expected Token Savings**: 40-50% compared to all-Sonnet setup

---

## 🚀 How to Use the Multi-Agent System

### Automatic Delegation (Recommended)

The **coordinator** agent automatically delegates tasks to specialists based on your request:

```bash
# Start a session with the coordinator
claude code

# Your request is analyzed and auto-delegated
> "Research state-of-the-art anomaly detection methods for MSA and
   suggest which metrics to collect from our robot-shop services"

# Behind the scenes:
# 1. Coordinator analyzes request (research + implementation)
# 2. Delegates literature review to research-expert
# 3. Delegates metrics analysis to code-infrastructure
# 4. Synthesizes results into actionable recommendations
```

### Manual Agent Invocation

You can also explicitly request a specific agent:

```bash
# Invoke research expert directly
> "@research-expert What are the latest papers on trace-based anomaly detection?"

# Invoke code infrastructure expert
> "@code-infrastructure Analyze the OpenTelemetry configuration in K8s/helm/templates/"

# Ask coordinator to delegate
> "Coordinator: have research-expert design an experiment and code-infrastructure implement it"
```

---

## 💡 Example Workflows

### Workflow 1: Literature Review + Implementation

**Your Request**:
```
"I want to implement a trace-based anomaly detector.
Find recent research papers and then help me instrument
the robot-shop services appropriately."
```

**What Happens**:
1. **Coordinator** breaks down task
2. **Research-expert** searches for papers on trace-based anomaly detection (2023-2026)
3. **Research-expert** recommends specific approaches and metrics
4. **Code-infrastructure** analyzes current OpenTelemetry setup
5. **Code-infrastructure** adds instrumentation to critical services
6. **Coordinator** synthesizes into implementation plan with references

### Workflow 2: Experimental Design

**Your Request**:
```
"Design a fault injection experiment to test anomaly detection
in the payment service. I need the research methodology and
the K8s configurations."
```

**What Happens**:
1. **Research-expert** designs rigorous experiment:
   - Hypothesis, variables, metrics, baselines
   - Statistical validation approach
2. **Code-infrastructure** implements:
   - Fault injection sidecar in payment-deployment.yaml
   - Custom metrics for detection evaluation
   - Data collection scripts
3. **Coordinator** provides unified experimental protocol

### Workflow 3: Codebase Analysis

**Your Request**:
```
"Which services in robot-shop are best candidates for
anomaly injection? Consider both research value and
implementation feasibility."
```

**What Happens**:
1. **Code-infrastructure** analyzes service code and dependencies
2. **Research-expert** evaluates research opportunities per service
3. **Coordinator** ranks services with justification

### Workflow 4: Optimization Task

**Your Request**:
```
"Our Jaeger is collecting too much trace data.
How should we optimize sampling?"
```

**What Happens**:
1. **Research-expert** reviews sampling strategies from literature
2. **Code-infrastructure** analyzes current Jaeger configuration
3. **Code-infrastructure** implements tail-based sampling
4. **Coordinator** explains changes and expected impact

---

## 🎯 Best Practices for Token Efficiency

### 1. **Be Specific in Requests**
❌ Bad: "Help me with anomaly detection"
✅ Good: "Find papers on LSTM-based anomaly detection for microservices (2024-2026) and list key findings"

### 2. **Use Parallel Agent Execution**
```bash
# Efficient: Both agents work simultaneously
> "Research-expert: review papers on metric correlation
   Code-infrastructure: analyze our current metric collection
   Then synthesize findings"
```

### 3. **Leverage Haiku for Repetitive Tasks**
```bash
# Code-infrastructure (Haiku) is perfect for:
- Batch YAML modifications
- Code analysis across multiple services
- Generating configuration variants
- Iterative debugging

# This saves ~67% token cost vs using Sonnet
```

### 4. **Provide Context Once**
```bash
# Include context in first message, then refer to it
> "Context: We have 10 services, OpenTelemetry -> Jaeger, goal is trace anomaly detection.

   Task 1: Research-expert, find relevant papers
   Task 2: Code-infrastructure, analyze traces
   Task 3: Coordinator, synthesize into experiment plan"
```

### 5. **Use File References Instead of Pasting Code**
❌ Don't paste large YAML files in prompts
✅ Do reference files: "Analyze K8s/helm/templates/cart-deployment.yaml"

---

## 📁 Agent Configuration Files

Your agents are configured in:
```
.claude/agents/
├── coordinator.md              # Main orchestrator (Sonnet)
├── research-expert.md          # Research advisor (Sonnet)
└── code-infrastructure.md      # Implementation (Haiku)
```

### Customizing Agents

Edit the markdown files to adjust:
- **Prompts**: Modify the content section
- **Models**: Change `model: sonnet` to `model: haiku` or `model: opus`
- **Tools**: Adjust `tools:` list (e.g., add `web_search` if needed)
- **Permissions**: Set `permissionMode: auto` for autonomous operation

Example modification:
```markdown
---
name: research-expert
model: haiku  # Changed from sonnet to save costs
tools: web_search, read  # Removed unnecessary tools
---

[Your custom prompt here]
```

---

## 🔍 Monitoring Agent Performance

### Check Token Usage
```bash
# See token consumption per agent
/usage
```

### Agent Activity Logs
```bash
# See which agent is active
# Look for messages like: "Delegating to research-expert..."
```

### Optimization Tips
- If coordinator rarely delegates, make requests more complex
- If code-infrastructure is slow, ensure it's using Haiku not Sonnet
- If research-expert findings are shallow, provide more specific research questions

---

## 🛠️ Advanced Patterns

### Pattern 1: Iterative Refinement
```bash
> "Research-expert: propose 3 anomaly detection approaches
   Code-infrastructure: estimate implementation effort for each
   Coordinator: rank by research impact vs effort"
```

### Pattern 2: Validation Loop
```bash
> "Code-infrastructure: implement metric collector
   Research-expert: verify metrics align with literature
   Code-infrastructure: adjust based on feedback"
```

### Pattern 3: Parallel Exploration
```bash
> "Research-expert: explore Method A
   Code-infrastructure: prototype Method B
   Compare results after both complete"
```

---

## 🚨 Troubleshooting

### Issue: Agents not delegating automatically
**Solution**: Be explicit in your request:
```bash
> "Coordinator: delegate research to research-expert and implementation to code-infrastructure"
```

### Issue: High token costs
**Solution**:
- Ensure code-infrastructure uses Haiku (check .claude/agents/code-infrastructure.md)
- Reduce context by referencing files instead of pasting content
- Combine related requests into single prompts

### Issue: Code agent making mistakes
**Solution**:
- For complex logic, manually invoke Sonnet: `@coordinator [complex task]`
- Haiku is optimized for speed; use Sonnet when accuracy is critical

### Issue: Research agent not finding recent papers
**Solution**:
- Specify date range: "Find papers from 2024-2026"
- Request specific venues: "Papers from NSDI, OSDI, SoCC"

---

## 📚 Research Project Checklist

Use this workflow for your anomaly detection research:

- [ ] **Phase 1: Research Foundation**
  - [ ] Literature review (research-expert)
  - [ ] Gap analysis (research-expert)
  - [ ] Methodology design (research-expert)

- [ ] **Phase 2: Environment Setup**
  - [ ] Analyze current K8s setup (code-infrastructure)
  - [ ] Enhance instrumentation (code-infrastructure)
  - [ ] Validate data collection (code-infrastructure)

- [ ] **Phase 3: Experimentation**
  - [ ] Design experiments (research-expert)
  - [ ] Implement fault injection (code-infrastructure)
  - [ ] Run experiments (coordinator)
  - [ ] Collect data (code-infrastructure)

- [ ] **Phase 4: Analysis**
  - [ ] Statistical analysis (research-expert)
  - [ ] Baseline comparison (research-expert)
  - [ ] Results visualization (code-infrastructure)

- [ ] **Phase 5: Paper Writing**
  - [ ] Methodology section (research-expert)
  - [ ] Implementation details (code-infrastructure)
  - [ ] Results synthesis (coordinator)

---

## 🎓 Example Research Commands

```bash
# Start your research session
> "Coordinator: I want to explore anomaly detection using distributed traces
   in our robot-shop MSA. I need a comprehensive research plan that covers
   literature review, experimental design, and implementation roadmap."

# Literature review
> "Research-expert: Find papers on graph-based anomaly detection using
   distributed traces from 2023-2026. Focus on approaches applicable to
   e-commerce MSA like our robot-shop."

# Codebase analysis
> "Code-infrastructure: Map the service dependency graph from our K8s
   configurations and identify critical paths through cart → payment → shipping."

# Experimental design
> "Research-expert: Design a fault injection experiment with:
   - Independent var: fault type (latency, errors, resource exhaustion)
   - Dependent var: detection accuracy, MTTD, false positive rate
   - Services: cart, payment, shipping
   Ensure statistical rigor for publication."

# Implementation
> "Code-infrastructure: Implement the experiment design by:
   1. Adding fault injection sidecars to target services
   2. Instrumenting detection evaluation metrics
   3. Creating scripts for automated experiment runs"

# Result synthesis
> "Coordinator: Synthesize findings from traces, evaluate detection performance,
   and prepare results for paper submission."
```

---

## 📖 Additional Resources

- **Claude Code Docs**: https://code.claude.com/docs/en/sub-agents
- **Your Project Context**:
  - K8s Helm charts: `/home/user/robot-shop/K8s/helm/`
  - Agent configs: `/home/user/robot-shop/.claude/agents/`
  - This guide: `/home/user/robot-shop/.claude/AGENT_USAGE_GUIDE.md`

---

## 💾 Quick Reference Commands

```bash
# List available agents
ls .claude/agents/

# Edit agent configuration
nano .claude/agents/coordinator.md

# Check token usage
/usage

# Invoke specific agent
@research-expert [your question]
@code-infrastructure [your task]

# Explicit delegation
> "Coordinator: delegate this to [agent-name]"
```

---

**Happy researching! Your multi-agent system is ready to help you publish high-quality anomaly detection research.** 🚀
