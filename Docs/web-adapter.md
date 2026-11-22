# Project Bonneville Web Adapter

## Purpose

The web adapter provides an HTTP and HTML interface to Project Bonneville without moving game rules into the web layer.

Dependency direction:

`Browser -> Flask/Jinja -> CampaignApplication -> management.py -> game engine`

Flask does not import or depend on the Tkinter UI.

## Runtime

The 0.7c development environment uses:

- Python 3.14.10 running natively as arm64 on Grand-Slam;
- a project-local `.venv`;
- Flask 3.1.3, pinned in `requirements.txt`;
- Jinja templates supplied through Flask.

## Components

### `web.py`

The Flask application entry point. Routes delegate campaign operations to `CampaignApplication`.

### `templates/dashboard.html`

Initial campaign dashboard showing year, season, turn, team and cash, with an End Turn action.

### `templates/new_campaign.html`

Protected New Campaign confirmation page. Viewing the page is read-only; creating a fresh campaign requires a POST request.

## Routes

- `GET /health` - application health check.
- `GET /` - render the current campaign dashboard.
- `POST /turn` - advance and persist the campaign, then return to the dashboard.
- `GET /new` - display the read-only New Campaign confirmation page.
- `POST /new` - create and persist a fresh campaign, then return to the dashboard.

## Persistence

Existing state is loaded when `CampaignApplication` is created.

Turn advancement is persisted through `CampaignApplication.advance_turn()`.

The New Campaign workflow resets the campaign through `CampaignApplication.new_campaign()` and explicitly saves the fresh state.

Persistence across creation of a new `CampaignApplication` instance is covered by automated tests.

## Testing

Web tests are contained in `test_web.py`.

State-changing tests replace the normal web application campaign with a `CampaignApplication` using temporary storage. Automated tests therefore cannot advance, reset or overwrite the user's normal campaign.

At the end of the functional 0.7c work, the complete Project Bonneville regression suite contains 207 passing tests.

## Local Development

From the repository on Grand-Slam:

1. Activate the environment: `source .venv/bin/activate`
2. Start Flask: `python -m flask --app web run`
3. Browse to: `http://127.0.0.1:5000/`
4. Health check: `http://127.0.0.1:5000/health`

Stop Flask with Ctrl+C.

The Flask development server is for local development only. Production serving for `octopi03` will be defined during the deployment phase.

## 0.7c Boundary

0.7c proves that Bonneville can be driven through HTTP and server-rendered HTML while retaining the existing application and engine boundaries.

Visual design and broader browser gameplay belong to 0.7d.

Deployment to `octopi03` and exposure beneath `/bonneville/` belong to later roadmap phases.
