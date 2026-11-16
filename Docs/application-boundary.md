# Project Bonneville Application Boundary

## Purpose

Project Bonneville separates campaign game logic from user-interface and delivery technology.

The `CampaignApplication` class in `application.py` provides the initial application-facing boundary between the core game engine and clients such as:

- the existing Tkinter desktop application;
- the planned browser interface;
- automated tests;
- future service or API adapters.

The application layer does not implement game rules. Those remain in the existing engine modules, principally `management.py` and `campaign_world.py`.

This boundary allows Project Bonneville to evolve beyond Tkinter without requiring the underlying simulation and campaign systems to be rewritten.

---

## Architecture

The intended dependency direction is:

    User Interface / Web Adapter
                |
                v
        CampaignApplication
                |
                v
          management.py
                |
                v
       Campaign engine modules

The application layer may depend on the engine.

The engine must not depend on the application layer, Tkinter, HTTP frameworks, Caddy, or OctoPi-specific infrastructure.

---

## CampaignApplication

`CampaignApplication` owns the currently active `CampaignState` and its configured save path.

Construction:

    CampaignApplication(save_path)

If the configured save exists, the campaign is loaded using the existing management-layer persistence code.

If no save exists, the existing `load_campaign()` behaviour supplies a fresh `CampaignState`.

The save location is configurable so the same application boundary can be used by the desktop application, automated tests, and future server deployment.

---

## Operations

### new_campaign()

Creates a fresh campaign using the existing management-layer reset behaviour.

The previous save at the configured path is removed.

The fresh campaign becomes the application's current campaign.

Returns the new `CampaignState`.

### load()

Loads campaign state from the configured save path using `management.load_campaign()`.

The loaded campaign becomes the application's current campaign.

Returns the loaded `CampaignState`.

### save()

Persists the application's current campaign to the configured save path using `management.save_campaign()`.

Serialization remains a management-layer responsibility.

### advance_turn(days=None)

Advances the current campaign through `management.advance_turn()`.

The application layer does not reproduce or reinterpret any turn-processing rules.

After the engine completes the turn, the application automatically persists the resulting campaign state.

The value returned by `management.advance_turn()` is returned unchanged. At present this is the tuple of completed research technology IDs.

### summary()

Returns a JSON-serialisable snapshot intended for presentation-layer clients.

The summary currently includes:

#### Campaign

- campaign ID;
- turn number;
- current year;
- current day of year;
- current season;
- current historical era.

#### Team

- name;
- cash;
- reputation;
- engineers;
- mechanics;
- workshop level.

#### World record

- standing record speed;
- record holder;
- record year.

World-record resolution uses the existing `management.standing_world_record()` function rather than duplicating record-selection rules in the application layer.

#### World information

- headlines;
- reactions.

The returned structures contain ordinary Python dictionary, list, string, numeric, Boolean or null-compatible values and can therefore be serialised to JSON.

---

## Responsibilities

### Core engine

The core engine remains responsible for:

- campaign and team state;
- game rules;
- turn progression;
- historical progression;
- rivals;
- research;
- engineering projects;
- vehicle construction;
- workshop activity;
- sponsorship;
- finances;
- records;
- simulation;
- campaign persistence.

### Application layer

`CampaignApplication` is responsible for:

- owning the active campaign;
- defining the persistence location;
- coordinating load, save and reset operations;
- invoking engine operations;
- persisting application-level state changes where appropriate;
- exposing stable presentation-friendly summaries.

### Presentation layer

User interfaces are responsible for:

- displaying campaign information;
- collecting player input;
- confirmations;
- navigation;
- presentation formatting;
- translating application results into user-facing feedback.

Game rules must not be implemented in a presentation layer.

---

## Tkinter

The existing Tkinter application remains supported.

During the initial 0.7b work, the Tkinter UI continues to call existing management functions directly. Migrating every UI call to `CampaignApplication` is deliberately not part of the first application-boundary change.

This keeps the refactor incremental and protects the existing desktop application while the new boundary is proven.

The application layer itself does not import `tkinter` or `ui.app`.

A dedicated isolated-process regression test verifies that the engine/application path can operate without loading the desktop UI.

---

## Future Web Adapter

A future web adapter should depend on `CampaignApplication` rather than directly implementing campaign rules.

The initial web layer is expected to use operations equivalent to:

    application.load()
    application.new_campaign()
    application.save()
    application.advance_turn()
    application.summary()

HTTP routing, templates, request handling and response generation belong outside both the application layer and the core game engine.

This separation is intended to allow the same engine to support both desktop and browser clients.

---

## Deployment Boundary

The planned deployment target is `octopi03`.

The eventual browser application is intended to be exposed through the OctoPi Caddy service beneath:

    /bonneville/

Cluster-specific concerns such as:

- service management;
- reverse proxy configuration;
- URL prefixes;
- logging;
- monitoring;
- backups;
- deployment automation;

must remain outside the core Bonneville engine.

The game engine must remain runnable independently of the OctoPi cluster.

---

## Testing

The application boundary is currently protected by `test_application.py`.

Coverage includes:

- loading an existing campaign;
- creating a fresh campaign when no save exists;
- creating/resetting a campaign;
- explicit persistence;
- automatic persistence after turn advancement;
- preserving the return value from `management.advance_turn()`;
- summary structure;
- JSON serialisation;
- operation without importing Tkinter or `ui.app`.

The existing `test_headless_campaign.py` provides an additional regression boundary around direct headless engine use.

At the establishment of the initial application boundary, the complete Project Bonneville test suite contains 199 passing tests.

---

## Design Rules

1. Game rules belong in the engine, not `CampaignApplication`.
2. `CampaignApplication` coordinates engine operations rather than reproducing them.
3. Presentation-specific behaviour stays outside the application and engine layers.
4. Web-framework dependencies must not enter the core engine.
5. OctoPi-specific dependencies must not enter the core engine.
6. Application summaries must remain serialisable and presentation-friendly.
7. Existing Tkinter behaviour should be preserved during incremental migration.
8. Architectural changes must leave the regression suite green.

---

## Current 0.7b Status

Completed:

- headless campaign boundary proved;
- permanent headless regression test added;
- `CampaignApplication` introduced;
- configurable campaign persistence provided;
- new/load/save/advance operations provided;
- presentation-friendly campaign summary provided;
- application-level tests added;
- full regression suite passes with 199 tests.

Remaining before the 0.7b exit criteria are complete:

- verify the existing Tkinter desktop application still operates correctly;
- decide whether any initial Tkinter operations should migrate to `CampaignApplication`;
- update the 0.7 roadmap to reflect completed work;
- complete the 0.7b Git checkpoint.