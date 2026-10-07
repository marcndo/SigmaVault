# SigmaVault

## Problem

Small software businesses often hold cash that must simultaneously serve two competing purposes:

1. remain available to meet future business obligations; and
2. avoid remaining unnecessarily idle when a portion could potentially be deployed productively.

The difficulty is not simply finding a yield opportunity. The business must determine **how much liquidity can safely be deployed, when it can be deployed, for how long, and when it must remain available for upcoming obligations**.

This requires reasoning across:

* current available liquidity;
* confirmed and forecast future obligations;
* obligation timing;
* required working capital;
* safety buffers;
* existing treasury positions;
* available treasury opportunities;
* liquidity and redemption constraints; and
* the uncertainty and freshness of the underlying financial data.

A treasury system that simply follows an AI recommendation is not sufficient for this problem. A recommendation may be reasonable while still violating a business's liquidity requirements or operating policy.

SigmaVault therefore treats treasury management as a controlled decision process:

```text
Financial Evidence
       ↓
Financial State
       ↓
Treasury Intelligence
       ↓
Decision Proposal
       ↓
Deterministic Policy Validation
       ↓
Authorization
       ↓
Execution
       ↓
Independent Verification
       ↓
Reconciliation
       ↓
Audit
```

The central problem SigmaVault addresses is:

> **Given a business's financial state, obligations, policies, and available treasury opportunities, determine whether liquidity can be safely deployed, how much can be deployed, when it should be deployed, and under what conditions the action is permitted.**

## Product Goal

SigmaVault is designed to help small software businesses manage treasury liquidity as a controlled decision process.

Its primary goal is to **maintain sufficient liquidity for business obligations while identifying and, when permitted, safely deploying genuinely available surplus liquidity into eligible treasury opportunities.**

The system should be able to:

1. understand the business's current financial state;
2. identify confirmed and forecast future obligations;
3. determine the liquidity that must remain available;
4. calculate the amount of liquidity that may potentially be deployed;
5. evaluate whether an available treasury opportunity is eligible and economically sensible;
6. propose a treasury action with supporting evidence and explicit assumptions;
7. subject the proposal to deterministic business and safety policies;
8. execute only an authorized action;
9. independently verify the resulting external financial state;
10. reconcile the observed outcome against the expected outcome; and
11. preserve an auditable record of the decision and its outcome.

The product therefore prioritizes **liquidity safety and correctness before yield optimization**.

The system is not intended to give an AI model unrestricted control over business funds. Instead, SigmaVault separates:

```text
AI reasoning
     ↓
Decision proposal
     ↓
Deterministic authorization
     ↓
Controlled execution
     ↓
Independent verification
```

This separation allows the system to use AI for tasks that benefit from reasoning and interpretation while keeping consequential financial constraints deterministic and enforceable.

## Target Business

The initial target user is a **small software or SaaS business** that:

* holds USD-denominated liquidity, including USDC where applicable;
* has recurring operating expenses such as cloud infrastructure, software subscriptions, payroll, and other business obligations;
* has obligations with known or forecast due dates;
* needs to maintain sufficient working capital for upcoming expenses;
* may have periods where available liquidity exceeds near-term operating requirements; and
* has a founder, operator, or finance responsible person who defines the business's treasury policies.

The initial product is intentionally focused on a narrow operating environment rather than attempting to manage every type of business treasury.

A representative business might have:

```text
Current liquidity
        │
        ├── Near-term obligations
        │
        ├── Safety buffer
        │
        └── Potential surplus
                 │
                 ↓
          Eligible treasury
             opportunity
```

The treasury problem for this business is therefore not simply:

> "Where can we earn yield?"

It is:

> **"After accounting for what the business may need, what liquidity is genuinely available for deployment, and is deploying it permitted and economically sensible?"**

The business remains the authority over its treasury policy. SigmaVault is responsible for analyzing the available financial evidence, proposing decisions, enforcing deterministic constraints, and verifying the resulting financial state.

### Initial Scope

The initial system focuses on:

* short-duration treasury decisions;
* recurring business obligations;
* liquidity protection;
* surplus-liquidity identification;
* eligible treasury opportunities;
* controlled deployment and redemption;
* deterministic safety policies;
* execution verification;
* reconciliation; and
* auditable decision records.

The system does **not** initially attempt to replace a company's complete accounting, banking, payroll, procurement, or enterprise resource planning system.

Those systems may provide financial evidence to SigmaVault, while SigmaVault focuses on the treasury decision and execution lifecycle.

## Core Concept

SigmaVault separates **financial reasoning** from **financial authority**.

The AI agent is responsible for interpreting financial information, reasoning about future obligations and liquidity, evaluating available opportunities, and proposing a treasury action.

The agent does **not** have unrestricted authority to execute that action.

Instead, every consequential treasury action passes through deterministic controls before execution:

```text
Financial Evidence
       ↓
Financial State
       ↓
AI Treasury Reasoning
       ↓
Decision Proposal
       ↓
Deterministic Policy Validation
       ↓
Authorization
       ↓
Controlled Execution
       ↓
Independent Verification
       ↓
Reconciliation
       ↓
Audit
```

The fundamental rule is:

> **The agent proposes. Deterministic software authorizes. External systems execute. Independent evidence verifies.**

This creates a separation between four different responsibilities:

### 1. Reasoning

The AI may:

* interpret financial evidence;
* identify relevant obligations;
* reason about liquidity requirements;
* evaluate timing;
* compare eligible opportunities;
* identify uncertainty;
* propose an action; and
* explain the reasoning and evidence supporting the proposal.

### 2. Authorization

Deterministic software evaluates whether the proposed action satisfies the business's configured policies and system safety constraints.

Examples include:

* required liquidity;
* safety buffers;
* maximum allocation;
* transaction limits;
* data freshness;
* strategy eligibility;
* available balance; and
* authorization requirements.

The AI cannot bypass these controls by changing its recommendation.

### 3. Execution

Only an authorized action may reach the execution layer.

The execution layer interacts with external financial infrastructure and is responsible for safely submitting the authorized operation.

The agent is not given unrestricted access to arbitrary financial primitives simply because those primitives exist in the underlying infrastructure.

### 4. Verification

A successful execution request is not treated as proof that the intended financial outcome occurred.

SigmaVault independently verifies the resulting external state before treating the action as completed.

Accounting and downstream state changes are based on verified outcomes rather than on the agent's claim that an action succeeded.

This distinction is fundamental to the system:

> **Internal system state is not proof of external financial state.**

The result is a treasury system in which AI can provide sophisticated reasoning without becoming the final authority over consequential financial actions.
