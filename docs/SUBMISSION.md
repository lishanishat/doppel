# Submission text (copy-paste)

## Project name
Doppel

## Tagline
Verify AI-written code by rebuilding it independently from the spec and making the versions argue.

## Short description
Doppel rebuilds an AI-written function twice from the spec alone, runs the PR and both rebuilds on the same generated inputs, and lets fixed code (never an LLM) return VERIFIED, BLOCKED, QUESTION or UNPROVEN. You use it from an ASI:One chat, and it posts a GitHub review with the counterexample.

## Long description (~150 words)
You give Doppel a pull request in ASI:One chat. It reads the PR and the linked issue (the spec) from GitHub, then asks a separate Twin builder agent for two independent rebuilds from the spec text only: Twin A (muse-spark-1.3) and Twin B (muse-wonder-1.0, deliberately naive). The PR and both twins run as separate processes on the same Hypothesis-generated inputs; disagreements are shrunk and re-run twice to rule out flakiness. Fixed code decides the verdict and a GitHub review is posted.

Measured: on 15 held-out, automatically generated mutants, Doppel caught 15/15, the PR's own tests 13/15, and LLM-written blind tests 15/15. We match blind tests, we do not beat them. No false alarm on the correct reference.

Honest limits: both twins are Meta models, so shared mistakes are possible; one function with a written spec; "VERIFIED on N inputs" is evidence, not proof; the QUESTION path is built and tested but has no natural demo trigger; the Orchestrator runs on a laptop behind an Agentverse mailbox.

## Built with
- Fetch.ai uAgents, Agentverse (mailbox), ASI:One chat protocol
- Meta Model API: muse-spark-1.3 and muse-wonder-1.0
- Hypothesis (property-based testing)
- GitHub API
- Python

## Tracks
- Trust but Verify
- Best Use of Fetch.ai
- Best Use of Meta Model API

## Team
Lisha Nishat, Manank Maheshwari

## Links
- Repo: https://github.com/lishanishat/doppel
- Demo repo: https://github.com/lishanishat/doppel-demo
- PR #2 (correct, VERIFIED): https://github.com/lishanishat/doppel-demo/pull/2
- PR #3 (one auto-injected bug, BLOCKED): https://github.com/lishanishat/doppel-demo/pull/3

## Agentverse addresses
- Orchestrator: `agent1qw3l50t8rpzg9dfhpfnyrkpcceuxrmpxd6qtue2rfr86ddh5yg6jkvuue9m`
- Twin builder: `agent1q0kqwvkmemtmpxeu2l56yt9qgc9p07q4legc98t9rlqxrcd9hxgawqlnk8c`
- Coder agent: `agent1q079huz7les8x0gvgxejagvdavlqzn0d0rqf5q97kerxx6433uxm6afu27c`

## Submission checklist
- [ ] Both repos are public (doppel, doppel-demo)
- [ ] Teammate (Manank Maheshwari) added on the Cerebral Valley form
- [ ] Video link opens without login (test in a private window)
- [ ] Orchestrator and Twin builder running; mailbox connected
- [ ] Register the project via the ASI:One Submission Agent
