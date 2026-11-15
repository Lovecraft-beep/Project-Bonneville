# Project Bonneville 0.7 Roadmap

## Goal

Project Bonneville 0.7 moves the existing Python game from a Tkinter-only desktop application towards a UI-independent architecture that can ultimately run as a browser-accessible application on the OctoPi cluster.

The intended deployment target is `octopi03`, exposed through Caddy at:

`/bonneville/`

The existing Tkinter application should remain usable while the engine and application layers are separated.

---

## 0.7a - Development Environment and Headless Engine Proof

**Status: Complete**

Objective: establish Grand-Slam as a safe development environment and prove that the existing campaign engine can operate without starting the Tkinter UI.

### Development environment

- [x] Install Visual Studio Code on Grand-Slam.
- [x] Open the existing Project Bonneville repository.
- [x] Connect VS Code/Git to GitHub.
- [x] Verify push access to the GitHub repository.
- [x] Connect and verify GitHub Copilot against the Bonneville workspace.

### Git hygiene

- [x] Diagnose Windows/macOS line-ending differences.
- [x] Configure Grand-Slam Git with `core.autocrlf=input`.
- [x] Create a pre-normalisation safety branch.
- [x] Add `.gitattributes`.
- [x] Standardise Python, Markdown and JSON files on LF.
- [x] Ignore generated test output and macOS metadata.
- [x] Commit and push the clean baseline.

Baseline commit:

`fa26e23 - Add cross-platform Git line-ending policy`

### Headless engine proof

- [x] Identify `main.py` as the desktop UI launcher.
- [x] Identify `management.py` as the primary campaign-management layer.
- [x] Identify `campaign_world.py` as the world-progression layer.
- [x] Create a campaign without importing the UI.
- [x] Save campaign state to a temporary file.
- [x] Reload campaign state.
- [x] Advance campaign from turn 1 to turn 2.
- [x] Confirm Tkinter is not imported by the headless engine path.
- [x] Confirm `ui.app` is not imported by the headless engine path.

Result:

**The existing campaign engine can operate independently of the Tkinter application.**

---

## 0.7b - Application Boundary

**Status: In progress**

Objective: establish a small, tested application-facing interface between the core game engine and user-interface implementations.

Development branch:

`develop/0.7b`

### Regression safety

- [x] Create permanent `test_headless_campaign.py`.
- [x] Run the headless test in an isolated Python process.
- [x] Verify create, save, load and advance-turn operations.
- [x] Verify the isolated engine process does not import Tkinter or `ui.app`.
- [x] Run the complete regression suite.
- [x] Confirm the regression suite passes.

### Application interface

- [x] Define the minimum application-level campaign operations.
- [x] Introduce `CampaignApplication` without moving game rules out of the engine.
- [x] Provide create/new campaign operation.
- [x] Provide load campaign operation.
- [x] Provide save campaign operation.
- [x] Provide advance-turn operation.
- [x] Automatically persist campaign state after application-level turn advancement.
- [x] Preserve the return value from `management.advance_turn()`.
- [x] Provide a JSON-serialisable campaign summary suitable for non-Tkinter clients.
- [x] Reuse existing world-record resolution rather than duplicating game rules.
- [x] Add focused tests for the application interface.
- [x] Run the complete regression suite after introducing the application boundary.
- [x] Document the application boundary.
- [ ] Verify compatibility with the existing Tkinter desktop application.

### Current verification

- [x] `CampaignApplication` operates without importing Tkinter or `ui.app`.
- [x] Application summaries successfully serialise to JSON.
- [x] Turn advancement through `CampaignApplication` automatically persists campaign state.
- [x] Application-specific test suite passes: 7 tests.
- [x] Complete Project Bonneville regression suite passes: 199 tests.
- [x] Application boundary committed and pushed to `develop/0.7b` at `f69765f`.

### 0.7b exit criteria

- [x] A client can operate the basic campaign lifecycle without knowing about Tkinter.
- [x] UI-independent operations have a stable application-facing interface.
- [ ] Existing Tkinter gameplay remains functional.
- [x] Full regression suite passes.
- [x] Headless regression test passes.
- [x] Application-interface tests pass.
- [x] Application-boundary implementation committed and pushed to `develop/0.7b`.
- [ ] Documentation update committed and pushed to `develop/0.7b`.

---

## 0.7c - First Web Adapter

**Status: Planned**

Objective: prove that the application layer can be driven over HTTP without coupling web behaviour to the game engine.

### Web foundation

- [ ] Select the minimal Python web framework suitable for Bonneville.
- [ ] Keep web-framework imports outside the core engine.
- [ ] Create a web application entry point.
- [ ] Add a health/status endpoint.
- [ ] Add a read-only campaign-status endpoint or page.
- [ ] Add new/load campaign capability.
- [ ] Add an advance-turn action.
- [ ] Persist campaign state through `CampaignApplication`.
- [ ] Add automated tests for web-to-application interaction.

### Architecture

- [ ] Web code depends on `CampaignApplication`, not directly on presentation-specific Tkinter behaviour.
- [ ] HTTP-specific behaviour remains outside the core game engine.
- [ ] No web-framework dependency is introduced into `management.py` or other core engine modules.
- [ ] Headless engine and application regressions remain green.

### 0.7c exit criteria

- [ ] Bonneville can be started locally as a web application.
- [ ] A browser can display campaign status.
- [ ] A browser interaction can create/load a campaign.
- [ ] A browser interaction can advance a campaign turn.
- [ ] State survives application restart.
- [ ] Tkinter remains independent and functional.
- [ ] Full regression suite remains green.

---

## 0.7d - Browser Gameplay Prototype

**Status: Planned**

Objective: provide enough browser UI to exercise the early campaign loop without attempting a complete replacement for the desktop interface.

### Initial browser experience

- [ ] Create a Bonneville landing/dashboard page.
- [ ] Display campaign date, season and turn.
- [ ] Display team finances and staffing.
- [ ] Display current world record and rival information.
- [ ] Display world headlines and reactions.
- [ ] Display active engineering work.
- [ ] Provide an End Turn control.
- [ ] Present completed-project and world-event feedback after advancing.
- [ ] Ensure URLs and static assets work beneath a configurable path prefix.

### Architecture

- [ ] Keep presentation logic out of `management.py`.
- [ ] Keep HTTP-specific behaviour out of the core engine.
- [ ] Use the application boundary for campaign lifecycle operations.
- [ ] Ensure the web application can operate beneath `/bonneville/`.
- [ ] Introduce no dependency on OctoPi-specific infrastructure into the core game.

### 0.7d exit criteria

- [ ] The basic management loop is usable in a browser.
- [ ] Campaign state remains persistent.
- [ ] Browser and desktop interfaces use the same underlying game rules.
- [ ] Automated tests cover the browser-facing campaign lifecycle.
- [ ] Existing headless and application tests remain green.

---

## 0.7e - OctoPi Deployment

**Status: Planned**

Objective: deploy the browser prototype onto the OctoPi cluster without making the cluster or home network depend on Bonneville.

Target application host:

`octopi03`

Intended public cluster path:

`/bonneville/`

### Deployment

- [ ] Define the Python runtime and dependencies.
- [ ] Create an isolated application environment on `octopi03`.
- [ ] Deploy the Bonneville repository/application.
- [ ] Run Bonneville as a managed service.
- [ ] Configure restart behaviour and service logging.
- [ ] Keep persistent campaign data outside disposable application code where appropriate.
- [ ] Verify application health directly on `octopi03`.

### Caddy integration

- [ ] Configure the existing cluster edge to proxy `/bonneville/`.
- [ ] Preserve the `/bonneville/` path correctly.
- [ ] Verify styles, scripts and navigation through the proxy.
- [ ] Verify campaign operations through Caddy.
- [ ] Ensure existing Caddy-hosted services remain unaffected.

### Automation

- [ ] Add deployment/configuration to the OctoPi Ansible workflow where appropriate.
- [ ] Make deployment idempotent.
- [ ] Document deployment and rollback.
- [ ] Store infrastructure changes in the OctoPi Git repository.

### 0.7e exit criteria

- [ ] Bonneville runs continuously on `octopi03`.
- [ ] Bonneville is reachable from the local network through `/bonneville/`.
- [ ] Campaign create/load/save/advance works through the deployed application.
- [ ] Rebooting `octopi03` restores the service.
- [ ] Existing cluster services remain healthy.
- [ ] The home network has no dependency on Bonneville.

---

## 0.7f - Observability and Operational Hardening

**Status: Planned**

Objective: make Bonneville a well-behaved OctoPi workload rather than merely an application that happens to run on a Pi.

### Observability

- [ ] Provide useful application health information.
- [ ] Integrate service health with existing cluster monitoring where appropriate.
- [ ] Make Bonneville logs available through the existing logging platform where appropriate.
- [ ] Define useful application metrics.
- [ ] Add a small Grafana view/dashboard if the metrics justify it.
- [ ] Consider service-down alerting.

### Operations

- [ ] Include persistent Bonneville data in the appropriate backup strategy.
- [ ] Test restoration of campaign state.
- [ ] Document update procedure.
- [ ] Document rollback procedure.
- [ ] Verify Bonneville behaves correctly during cluster shutdown and restart.
- [ ] Verify failure of Bonneville cannot affect critical home-network services.

### 0.7f exit criteria

- [ ] Service health is observable.
- [ ] Persistent state is backed up and recoverable.
- [ ] Deployment is reproducible.
- [ ] Failure is contained to the Bonneville application.
- [ ] Operational documentation is in Git.

---

## 0.7 Release Candidate

Before declaring Project Bonneville 0.7 complete:

- [ ] Full Python regression suite passes.
- [ ] Headless architecture regression passes.
- [ ] Application-interface tests pass.
- [ ] Web tests pass.
- [ ] Tkinter desktop application still functions.
- [ ] Browser campaign lifecycle functions.
- [ ] `octopi03` deployment is reproducible.
- [ ] `/bonneville/` proxy path is verified.
- [ ] Monitoring and backup behaviour are verified.
- [ ] Documentation matches the deployed architecture.
- [ ] Git working trees are clean.
- [ ] Development changes are merged through the normal Git workflow.

---

## Guiding Principles

1. **Protect the engine.** Game rules remain independent of UI and deployment technology.
2. **Refactor incrementally.** Each architectural change must leave the test suite green.
3. **Keep Tkinter working.** The browser interface is initially an additional client, not a destructive rewrite.
4. **Test the boundary.** Headless operation must remain an explicit regression guarantee.
5. **Use the application boundary.** New presentation layers should consume `CampaignApplication` rather than duplicate campaign lifecycle logic.
6. **Automate the cluster.** Stateful OctoPi configuration belongs in Ansible and Git wherever practical.
7. **Do not make the home network depend on Bonneville.** Bonneville is an application workload, not critical infrastructure.
8. **Checkpoint frequently.** Each meaningful milestone should end in a clean, tested Git state.