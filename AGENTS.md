# MinToon

- Product: 민툰 / MinToon; intended GitHub repository: andongmin94/min-toon, public, main.
- Target stock UE 5.8. Never modify installed Engine source, Engine/Shaders, manifests or BuildId.
- This first slice is an editor authoring plugin. Native Unreal materials render the result.
- Keep authoring and runtime concerns separate. Add runtime modules only when a verified feature needs them.
- Reuse documented engine APIs. No compatibility layers, fallback renderers or speculative framework.
- Do not copy MooaToon source, shaders, assets or brand elements.
- A distribution license has not been chosen. Do not choose one without the owner's instruction.
- Keep current status in README.md; use Git for history, not duplicate reports.
- Scope validation to changed code. Do not call Python unit tests or syntax checks UE integration tests.
- Engine startup, native API calls, shader compilation, visual quality and packaged execution must be verified in UE before claiming support.
- The UE 5.8 smoke/visual/cook gate passed on Win64; the immediate next task is under "다음 단계" in README.md.
