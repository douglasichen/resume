
## Things I did
- Login enumeration vulnerability fix
- AI PR Review Context Harness
- AI PR Review Coding Sins
- Added workflow for modifying saved test container
- Auto Triage
    - Built Gemini Integration Wrapper
        - Found that the client was throttling us due to a default config. AI found a way around the default config with some giant function that found a loophole. I thought it was too complicated and there must have been a better way. I realized the SDK version was out of date. After updating, the concurrency config was exposed and modifiable.
    - Built stable regression tests LLM powered features for auto triage
    - worked on bug fixes for auto triage
    - Implemented vector search across embeddings using pgvector


## Points
- Patched a login-enumeration vulnerability by enforcing byte-identical API response for wrong-password/wrong-email, protecting 11M user accounts
- Built the context harness for an AI code review agent processing **280+ PRs/wk**, flagging blockers pre-merge in CI
- Built Spring Boot services and AI Agent to automatically categorize and triage customer tickets in under **150 seconds**






- Resolved a QA bottleneck by writing Python scripts to automate manual work, speeding up a testing process by **20x**