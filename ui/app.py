"""Button-driven desktop interface for Project Bonneville."""

from copy import deepcopy
from dataclasses import replace
import tkinter as tk
from tkinter import messagebox

from brakes import BRAKE_CATALOG, available_brakes
from cars import AVAILABLE_CARS
from chassis import available_chassis
from diagnostics import (
    append_run_log,
    create_engineering_report,
    suggest_gear_ratio_adjustment,
    clear_diagnostic_log,
)
from engines import AVAILABLE_ENGINES, ENGINE_TUNE_STAGES, available_engines
from engines import (
    AVAILABLE_ENGINES,
    ENGINE_TUNE_STAGES,
    available_engines,
    next_engine_tune_stage,
)
from gearbox import (
    DIRECT_DRIVE,
    PREBUILT_GEARBOXES,
    TRANSMISSION_CATALOG,
    adjust_gearbox_ratio,
    optimize_gearbox_for_engine,
    recommended_transmission,
)
from historical_challenges import CHALLENGES, simulate_challenge
from historical_records import (
    HISTORICAL_TARGETS,
    average_record_speed,
    current_world_record,
    next_historical_target,
    required_record_runs,
    target_completed,
)
from management import (
    CampaignRecordAttempt,
    advance_turn,
    adjust_vehicle_ratio_trackside,
    apply_gear_ratios_trackside,
    build_vehicle,
    calculate_run_cost,
    calculate_session_run_cost,
    calculate_workshop_upgrade_cost,
    complete_failed_run,
    complete_run,
    fit_trackside_tyres,
    fit_trackside_brakes,
    hire_engineer,
    hire_mechanic,
    lapse_record_attempt_if_out_of_runs,
    load_campaign,
    MAX_RECORD_RUNS_PER_SESSION,
    MAX_TESTS_PER_SESSION,
    mark_session_venue_paid,
    next_vehicle_name,
    reset_campaign,
    register_record_run,
    register_test_run,
    retire_vehicle,
    save_campaign,
    session_runs_remaining,
    sign_sponsor,
    standing_world_record,
    describe_sponsor_objective,
    start_engineering_project,
    TRACKSIDE_ADJUSTMENT_COST_GBP,
    upgrade_workshop,
)
from records import create_record, load_records, save_record
from reliability import resolve_run_failure
from research import (
    AERODYNAMICS_TECHNOLOGY_TREE,
    BRAKE_TECHNOLOGY_TREE,
    CHASSIS_TECHNOLOGY_TREE,
    ENGINE_TECHNOLOGY_TREE,
    GEARBOX_TECHNOLOGY_TREE,
    TYRE_TECHNOLOGY_TREE,
    TECHNOLOGY_NAME_BY_ID,
    aerodynamics_effects,
)
from simulation import run_simulation
from sponsors import RUNS_OBJECTIVE, SPONSOR_BY_ID, SPONSOR_CATALOG, SPONSOR_OBJECTIVE_DEADLINE_TURNS, available_sponsors
from tracks import AVAILABLE_TRACKS, available_tracks
from vehicle import Vehicle
from vehicle_designer import build_vehicle_from_garage_entry


INK = "#202522"
PANEL = "#2b312d"
PANEL_LIGHT = "#343b36"
PAPER = "#e9e8df"
MUTED = "#aab2a9"
ACCENT = "#d36b49"
LIME = "#c6d87a"
LINE = "#49514b"
FONT = "Segoe UI"
DISPLAY_FONT = "Georgia"


def record_gap_headline(target, best_speed_mph):
    """Summarise how far the team's best is from the next historical target."""
    if target is None:
        return "All records beaten"
    gap = target.speed_mph - best_speed_mph
    if gap > 0:
        return f"{gap:.1f} mph short"
    return f"{-gap:.1f} mph clear / attempt it"


class BonnevilleApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Project Bonneville | Racing Department")
        self.geometry("1420x900")
        self.minsize(1080, 720)
        self.configure(bg=INK)
        self.campaign = load_campaign()
        self.page = "Dashboard"
        self.research_branch = "Engine"
        self.selected_vehicle = None
        self.builder = {}
        self.last_result = None
        self.last_vehicle = None
        self.last_vehicle_entry = None
        self.last_trackside_ratio_adjusted = False
        self.last_track = None
        self.last_run_note = "No test run recorded this session."
        self.last_record_message = None
        self.last_report = None
        self.last_run_is_sandbox = False
        self.last_run_outcome = None
        self.last_run_repaired = False
        self.last_run_was_record_attempt = False
        self.garage_return_required = False
        self.last_run_was_record_attempt = False

        self.sidebar = tk.Frame(self, bg=INK, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self.main = tk.Frame(self, bg=INK)
        self.main.pack(side="left", fill="both", expand=True)
        self._build_sidebar()
        self._build_header()
        self.body = tk.Frame(self.main, bg=INK)
        self.body.pack(fill="both", expand=True, padx=24, pady=(16, 22))
        self.show_page(
            "Test Runs" if self.campaign.record_attempt is not None else "Dashboard"
        )

    def _build_sidebar(self):
        tk.Label(
            self.sidebar,
            text="BONNEVILLE\nRACING DEPT.",
            bg=INK,
            fg=PAPER,
            font=(DISPLAY_FONT, 18, "bold"),
            justify="left",
            padx=22,
            pady=28,
        ).pack(anchor="w")
        tk.Frame(self.sidebar, bg=ACCENT, height=3).pack(fill="x", padx=22, pady=(0, 20))
        for name in ("Dashboard", "Research", "Garage", "Test Runs", "Test Facility", "Team Debrief", "Telemetry", "Team", "Records", "Challenges", "Encyclopedia"):
            self.nav_button(name)
        tk.Label(
            self.sidebar,
            text="PROJECT\nBONNEVILLE  /  0.5",
            bg=INK,
            fg=MUTED,
            font=(FONT, 9, "bold"),
            justify="left",
            padx=22,
            pady=18,
        ).pack(side="bottom", anchor="w")

    def nav_button(self, name):
        active = self.page == name
        tk.Button(
            self.sidebar,
            text=name.upper(),
            command=lambda: self.show_page(name),
            anchor="w",
            padx=22,
            pady=8,
            bg=PANEL if active else INK,
            fg=LIME if active else MUTED,
            activebackground=PANEL_LIGHT,
            activeforeground=PAPER,
            relief="flat",
            borderwidth=0,
            font=(FONT, 10, "bold"),
            cursor="hand2",
        ).pack(fill="x", padx=(10, 0), pady=2)

    def _build_header(self):
        bar = tk.Frame(self.main, bg=INK, height=68)
        bar.pack(fill="x", padx=26, pady=(16, 0))
        bar.pack_propagate(False)
        self.header_title = tk.Label(
            bar,
            text="CAMPAIGN CONTROL",
            bg=INK,
            fg=PAPER,
            font=(FONT, 11, "bold"),
        )
        self.header_title.pack(side="left", anchor="center")
        tk.Button(
            bar,
            text="END TURN",
            command=self.end_turn,
            bg=ACCENT,
            fg=INK,
            activebackground=LIME,
            activeforeground=INK,
            relief="flat",
            borderwidth=0,
            font=(FONT, 10, "bold"),
            padx=16,
            pady=8,
            cursor="hand2",
        ).pack(side="right", anchor="center", padx=(16, 0))
        self.header_status = tk.Label(
            bar, text="", bg=INK, fg=LIME, font=(FONT, 10, "bold")
        )
        self.header_status.pack(side="right", anchor="center")

    def _refresh_header(self):
        target = next_historical_target(
            self.campaign.current_year, self.campaign.completed_historical_record_ids
        )
        gap = record_gap_headline(target, self.campaign.best_measured_mile_speed_mph)
        self.header_status.configure(
            text=f"{self.campaign.current_year}  /  TURN {self.campaign.turn_number}     GBP {self.campaign.team.cash:,.0f}     {gap.upper()}"
        )

    def show_page(self, name):
        if (
            self.campaign.record_attempt is not None
            and name
            not in {
                "Garage",
                "Team Debrief",
                "Telemetry",
                "Test Runs",
                "Trackside Modifications",
            }
        ):
            messagebox.showerror(
                "Record attempt in progress",
                "Only the locked vehicle, trackside service, and required return run are available until the attempt is complete.",
                parent=self,
            )
            return
        if name == "Garage":
            self.garage_return_required = False
        self.page = name
        self._refresh_header()
        for child in self.sidebar.winfo_children():
            if isinstance(child, tk.Button):
                child.configure(
                    bg=PANEL if child.cget("text").title() == name else INK,
                    fg=LIME if child.cget("text").title() == name else MUTED,
                )
        self.header_title.configure(text=name.upper())
        for child in self.body.winfo_children():
            child.destroy()
        renderers = {
            "Dashboard": self.render_dashboard,
            "Research": self.render_research,
            "Garage": self.render_garage,
            "Test Runs": self.render_test_runs,
            "Trackside Modifications": self.render_trackside_modifications,
            "Test Facility": self.render_test_facility,
            "Team Debrief": self.render_team_debrief,
            "Telemetry": self.render_telemetry,
            "Team": self.render_team,
            "Records": self.render_records,
            "Challenges": self.render_challenges,
            "Encyclopedia": self.render_encyclopedia,
        }
        renderers[name]()

    def scroll_area(self):
        canvas = tk.Canvas(self.body, bg=INK, highlightthickness=0)
        scrollbar = tk.Scrollbar(self.body, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, bg=INK)
        frame.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        window_id = canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(window_id, width=event.width),
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return frame

    def page_title(self, parent, eyebrow, heading, detail=""):
        tk.Label(
            parent,
            text=eyebrow.upper(),
            bg=INK,
            fg=ACCENT,
            font=(FONT, 9, "bold"),
        ).pack(anchor="w", pady=(4, 6))
        tk.Label(
            parent,
            text=heading,
            bg=INK,
            fg=PAPER,
            font=(DISPLAY_FONT, 28, "bold"),
            wraplength=1050,
            justify="left",
        ).pack(anchor="w")
        if detail:
            tk.Label(
                parent,
                text=detail,
                bg=INK,
                fg=MUTED,
                font=(FONT, 10),
                wraplength=1000,
                justify="left",
            ).pack(anchor="w", pady=(6, 18))

    def section(self, parent, text):
        tk.Label(
            parent,
            text=text.upper(),
            bg=INK,
            fg=MUTED,
            font=(FONT, 9, "bold"),
        ).pack(anchor="w", pady=(18, 8))

    def action_button(self, parent, text, command, primary=False, width=None):
        button = tk.Button(
            parent,
            text=text,
            command=command,
            width=width,
            anchor="w",
            padx=14,
            pady=11,
            bg=ACCENT if primary else PANEL,
            fg=INK if primary else PAPER,
            activebackground=LIME if primary else PANEL_LIGHT,
            activeforeground=INK if primary else PAPER,
            relief="flat",
            borderwidth=0,
            font=(FONT, 10, "bold"),
            cursor="hand2",
            wraplength=460,
            justify="left",
        )
        button.pack(fill="x", pady=4)
        return button

    def card(self, parent, title, value, subtext=""):
        frame = tk.Frame(parent, bg=PANEL, padx=18, pady=16)
        tk.Label(frame, text=title.upper(), bg=PANEL, fg=MUTED, font=(FONT, 9, "bold")).pack(anchor="w")
        tk.Label(frame, text=value, bg=PANEL, fg=PAPER, font=(DISPLAY_FONT, 22, "bold")).pack(anchor="w", pady=(7, 2))
        if subtext:
            tk.Label(frame, text=subtext, bg=PANEL, fg=LIME, font=(FONT, 9)).pack(anchor="w")
        return frame

    def render_dashboard(self):
        page = self.scroll_area()
        target = next_historical_target(
            self.campaign.current_year, self.campaign.completed_historical_record_ids
        )
        self.page_title(
            page,
            "Operations / Season",
            f"{self.campaign.team.name}",
            f"Turn {self.campaign.turn_number}  |  Day {self.campaign.current_day_of_year}, {self.campaign.current_year}  |  {self.campaign.completed_runs} completed runs  |  {self.campaign.failed_runs} failed",
        )
        metrics = tk.Frame(page, bg=INK)
        metrics.pack(fill="x", pady=(4, 14))
        world_record = standing_world_record(self.campaign)
        best = self.campaign.best_measured_mile_speed_mph
        chase = (
            (
                f"World record / {self.campaign.current_year}",
                f"{world_record[0]:.1f} mph" if world_record else "None set",
                f"{world_record[1]}, {world_record[2]}" if world_record else "The record books are still open",
            ),
            ("Your personal best", f"{best:.1f} mph", "Best measured mile"),
            (
                "Gap to target",
                record_gap_headline(target, best),
                f"{target.year} {target.vehicle} / {target.speed_mph:.1f} mph" if target else "All records beaten",
            ),
        )
        chase_row = tk.Frame(page, bg=INK)
        chase_row.pack(fill="x", pady=(4, 10))
        for label, value, sub in chase:
            self.card(chase_row, label, value, sub).pack(side="left", fill="both", expand=True, padx=(0, 10))
        chase_row.winfo_children()[-1].pack_configure(padx=0)
        values = (
            ("Available funds", f"GBP {self.campaign.team.cash:,.0f}", f"{self.campaign.team.reputation:.1f} reputation"),
            ("Engineering team", f"{self.campaign.available_engineers} available", f"{self.campaign.allocated_engineers} allocated / {self.campaign.team.engineers} engineers"),
            ("Workshop", f"LEVEL {self.campaign.team.workshop_level}", f"{len(self.campaign.garage.vehicles)} vehicles in garage"),
        )
        for label, value, sub in values:
            self.card(metrics, label, value, sub).pack(side="left", fill="both", expand=True, padx=(0, 10))
        metrics.winfo_children()[-1].pack_configure(padx=0)

        columns = tk.Frame(page, bg=INK)
        columns.pack(fill="x", pady=(10, 0))
        left = tk.Frame(columns, bg=INK)
        right = tk.Frame(columns, bg=INK)
        left.pack(side="left", fill="both", expand=True, padx=(0, 28))
        right.pack(side="left", fill="both", expand=True)
        self.section(left, "Next actions")
        self.action_button(left, "Prepare a test run", lambda: self.show_page("Test Runs"), True)
        self.action_button(left, "Design a vehicle", self.start_vehicle_builder)
        self.action_button(left, "Open research tree", lambda: self.show_page("Research"))
        self.action_button(left, "End turn", self.end_turn)
        if self.campaign.engineering_projects:
            self.section(page, "Engineering projects in progress")
            for project in self.campaign.engineering_projects:
                progress = project.turns_total - project.turns_remaining
                tk.Label(
                    page,
                    text=f"{TECHNOLOGY_NAME_BY_ID[project.technology_id]}  /  {progress} of {project.turns_total} turns  /  {project.engineers_required} engineer(s)",
                    bg=INK,
                    fg=LIME,
                    font=(FONT, 10, "bold"),
                ).pack(anchor="w", pady=3)
        self.section(right, "Campaign objective")
        if target:
            gap = max(0.0, target.speed_mph - self.campaign.best_measured_mile_speed_mph)
            tk.Label(right, text=f"{target.year}  /  {target.vehicle}", bg=INK, fg=PAPER, font=(DISPLAY_FONT, 17, "bold"), wraplength=470, justify="left").pack(anchor="w")
            tk.Label(right, text=f"{target.speed_mph:.1f} mph target  |  {gap:.1f} mph to go\n{target.milestone}", bg=INK, fg=MUTED, font=(FONT, 10), justify="left").pack(anchor="w", pady=8)
            self.action_button(right, "Attempt historical record", self.start_record_attempt, True)
        else:
            tk.Label(right, text="All campaign records achieved.", bg=INK, fg=LIME, font=(FONT, 13, "bold")).pack(anchor="w")
        self.section(page, "Sponsor demands")
        self._render_sponsor_objectives(page)
        self.section(page, "Latest headlines")
        for headline in self.campaign.world.headlines[-3:]:
            tk.Label(page, text=f"-  {headline}", bg=INK, fg=PAPER, font=(FONT, 10), wraplength=1050, justify="left").pack(anchor="w", pady=3)
        if self.campaign.world.reactions:
            tk.Label(page, text=self.campaign.world.reactions[-1], bg=INK, fg=LIME, font=(FONT, 10, "italic"), wraplength=1050, justify="left").pack(anchor="w", pady=(10, 0))

    def render_research(self):
        page = self.scroll_area()
        self.page_title(page, "Research & development", "Engineering projects", "Fund a project to reserve its engineers. It advances whenever the campaign moves to its next turn and unlocks only when its schedule is complete.")
        tk.Label(
            page,
            text=f"Engineers available: {self.campaign.available_engineers} of {self.campaign.team.engineers}  /  GBP {self.campaign.team.cash:,.0f} available",
            bg=INK,
            fg=LIME,
            font=(FONT, 10, "bold"),
        ).pack(anchor="w", pady=(0, 12))
        if self.campaign.engineering_projects:
            self.section(page, "Active projects")
            for project in self.campaign.engineering_projects:
                progress = project.turns_total - project.turns_remaining
                remaining = project.turns_remaining
                technology_name = TECHNOLOGY_NAME_BY_ID[project.technology_id]
                frame = tk.Frame(page, bg=PANEL, padx=14, pady=10)
                frame.pack(fill="x", pady=3)
                tk.Label(frame, text=technology_name, bg=PANEL, fg=PAPER, font=(DISPLAY_FONT, 14, "bold")).pack(side="left")
                tk.Label(frame, text=f"{progress}/{project.turns_total} turns  /  {remaining} remaining  /  {project.engineers_required} engineer(s)", bg=PANEL, fg=LIME, font=(FONT, 9, "bold")).pack(side="right")
        tabs = tk.Frame(page, bg=INK)
        tabs.pack(fill="x", pady=(0, 10))
        for branch in ("Engine", "Chassis", "Aerodynamics", "Gearbox", "Tyres", "Brakes"):
            available = self._research_branch_available(branch)
            tk.Button(
                tabs, text=branch.upper(), command=lambda value=branch: self.set_research_branch(value),
                bg=PANEL_LIGHT if self.research_branch == branch else PANEL if available else INK,
                fg=(LIME if self.research_branch == branch else PAPER) if available else MUTED,
                activebackground=ACCENT if available else PANEL_LIGHT,
                activeforeground=INK if available else MUTED, relief="flat", borderwidth=0,
                font=(FONT, 9, "bold"), padx=13, pady=10, cursor="hand2",
            ).pack(side="left", padx=(0, 5))
        self._render_research_nodes(page)

    def set_research_branch(self, branch):
        self.research_branch = branch
        self.show_page("Research")

    def _research_data(self, branch=None):
        branches = {
            "Engine": (ENGINE_TECHNOLOGY_TREE, self.campaign.research.engine_technology, (*self.campaign.research.chassis_technology, *self.campaign.research.aerodynamics_technology)),
            "Chassis": (CHASSIS_TECHNOLOGY_TREE, self.campaign.research.chassis_technology, self.campaign.research.aerodynamics_technology),
            "Aerodynamics": (AERODYNAMICS_TECHNOLOGY_TREE, self.campaign.research.aerodynamics_technology, self.campaign.research.chassis_technology),
            "Gearbox": (GEARBOX_TECHNOLOGY_TREE, self.campaign.research.gearbox_technology, self.campaign.research.chassis_technology),
            "Tyres": (TYRE_TECHNOLOGY_TREE, self.campaign.research.tyre_technology, self.campaign.research.chassis_technology),
            "Brakes": (BRAKE_TECHNOLOGY_TREE, self.campaign.research.brake_technology, self.campaign.research.chassis_technology),
        }
        return branches[branch if branch is not None else self.research_branch]

    def _research_branch_available(self, branch):
        tree, researched, shared_researched = self._research_data(branch)
        researched_set = set(researched)
        combined = researched_set | set(shared_researched)
        return any(
            node.technology_id not in researched_set
            and set(node.prerequisites).issubset(combined)
            for node in tree
        )

    def _render_research_nodes(self, parent):
        tree, researched, shared_researched = self._research_data()
        researched_set = set(researched)
        combined = researched_set | set(shared_researched)
        active_ids = {
            project.technology_id
            for project in self.campaign.engineering_projects
        }
        ready = [node for node in tree if node.technology_id not in researched_set and node.technology_id not in active_ids and set(node.prerequisites).issubset(combined)]
        for node in tree:
            is_done = node.technology_id in researched_set
            project = next((item for item in self.campaign.engineering_projects if item.technology_id == node.technology_id), None)
            is_ready = node in ready
            status = "COMPLETE" if is_done else "IN PROGRESS" if project else "AVAILABLE" if is_ready else "LOCKED"
            card = tk.Frame(parent, bg=PANEL, padx=16, pady=13)
            card.pack(fill="x", pady=4)
            row = tk.Frame(card, bg=PANEL)
            row.pack(fill="x")
            info = tk.Frame(row, bg=PANEL)
            info.pack(side="left", fill="both", expand=True)
            tk.Label(info, text=f"{node.era.upper()}  /  {status}", bg=PANEL, fg=LIME if is_done else ACCENT if is_ready else MUTED, font=(FONT, 8, "bold")).pack(anchor="w")
            tk.Label(info, text=node.name, bg=PANEL, fg=PAPER, font=(DISPLAY_FONT, 16, "bold")).pack(anchor="w", pady=(4, 2))
            tk.Label(info, text=f"Cost: GBP {node.cost_gbp:,.0f}    /    Engineers: {node.engineers_required}    /    Time: {node.turns_required} turns\n{node.description or 'Prerequisites: ' + (', '.join(node.prerequisites) or 'None')}", bg=PANEL, fg=MUTED, font=(FONT, 9), wraplength=690, justify="left").pack(anchor="w")
            if is_ready:
                tk.Button(row, text="START PROJECT", command=lambda tech=node: self.research(tech), bg=ACCENT, fg=INK, activebackground=LIME, relief="flat", borderwidth=0, font=(FONT, 9, "bold"), padx=14, pady=10, cursor="hand2").pack(side="right", padx=(12, 0))
            elif project:
                tk.Label(row, text=f"{project.turns_remaining} TURNS LEFT", bg=PANEL, fg=LIME, font=(FONT, 9, "bold")).pack(side="right", padx=12)
            elif not is_done:
                tk.Label(row, text="LOCKED", bg=PANEL, fg=MUTED, font=(FONT, 9, "bold")).pack(side="right", padx=12)

    def research(self, technology):
        try:
            start_engineering_project(
                self.campaign,
                {"Tyres": "tyre", "Brakes": "brake"}.get(
                    self.research_branch,
                    self.research_branch.lower(),
                ),
                technology.technology_id,
            )
            save_campaign(self.campaign)
        except ValueError as exc:
            messagebox.showerror("Project unavailable", str(exc), parent=self)
        self.show_page("Research")

    def advance_campaign_turn(self, days=365):
        if self.campaign.record_attempt is not None:
            messagebox.showerror(
                "Record attempt in progress",
                "Complete or abandon the official return-run process before advancing campaign time.",
                parent=self,
            )
            return ()
        completed = advance_turn(self.campaign, days=days)
        if completed:
            names = ", ".join(TECHNOLOGY_NAME_BY_ID[item] for item in completed)
            messagebox.showinfo("Engineering project complete", f"Research completed: {names}", parent=self)
        if self.campaign.sponsorship.recent_departures:
            names = ", ".join(self.campaign.sponsorship.recent_departures)
            messagebox.showwarning(
                "Sponsor withdrawn",
                f"{names} withdrew after the team missed its target. Their income and reliability support are gone.",
                parent=self,
            )
        return completed

    def end_turn(self):
        if self.campaign.record_attempt is not None:
            self.advance_campaign_turn()
            return
        if not messagebox.askyesno(
            "End turn",
            f"End turn {self.campaign.turn_number}? Sponsor income is paid, engineering projects progress, and the test session closes.",
            parent=self,
        ):
            return
        self.advance_campaign_turn()
        save_campaign(self.campaign)
        self.show_page(self.page if self.page != "Trackside Modifications" else "Dashboard")

    def render_garage(self):
        page = self.scroll_area()
        self.page_title(page, "Vehicle department", "Garage", "Built vehicles retain their installed components between tests. Select a vehicle to inspect, tune, or replace components.")
        if self.campaign.record_attempt is None:
            self.action_button(page, "+  DESIGN NEW VEHICLE", self.start_vehicle_builder, True)
        else:
            tk.Label(page, text="An official record attempt is active. New designs are unavailable until its return run is complete.", bg=INK, fg=MUTED, font=(FONT, 11)).pack(anchor="w", pady=(0, 10))
        if not self.campaign.garage.vehicles:
            self.section(page, "Empty garage")
            tk.Label(page, text="Build your first car to unlock campaign test runs.", bg=INK, fg=MUTED, font=(FONT, 11)).pack(anchor="w")
        else:
            self.section(page, f"{len(self.campaign.garage.vehicles)} vehicles")
            for entry in self.campaign.garage.vehicles:
                vehicle = build_vehicle_from_garage_entry(entry)
                frame = tk.Frame(page, bg=PANEL, padx=16, pady=14)
                frame.pack(fill="x", pady=4)
                tk.Label(frame, text=vehicle.name, bg=PANEL, fg=PAPER, font=(DISPLAY_FONT, 17, "bold")).pack(anchor="w")
                tk.Label(frame, text=f"{vehicle.engine.name}  /  {vehicle.engine.power_hp:,.0f} hp     {vehicle.gearbox.name}     {vehicle.mass:,.0f} kg", bg=PANEL, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=(4, 10))
                self.action_button(frame, "OPEN VEHICLE", lambda item=entry: self.open_garage_vehicle(item))
        if self.campaign.garage.museum:
            self.section(page, f"Museum  /  {len(self.campaign.garage.museum)} retired designs")
            for entry in self.campaign.garage.museum:
                vehicle = build_vehicle_from_garage_entry(entry)
                row = tk.Frame(page, bg=PANEL, padx=16, pady=12)
                row.pack(fill="x", pady=3)
                tk.Label(row, text=vehicle.name, bg=PANEL, fg=PAPER, font=(DISPLAY_FONT, 15, "bold")).pack(anchor="w")
                tk.Label(row, text=f"{vehicle.engine.name}  /  {vehicle.engine.power_hp:,.0f} hp     {vehicle.gearbox.name}     {vehicle.mass:,.0f} kg", bg=PANEL, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=(4, 0))

    def open_garage_vehicle(self, entry):
        self.selected_vehicle = entry
        self.show_page("Garage")
        page = self.body.winfo_children()[0].winfo_children()[0]
        vehicle = build_vehicle_from_garage_entry(entry)
        self.page_title(page, "Vehicle specification", vehicle.name, f"{vehicle.engine.name}  /  {vehicle.engine.power_hp:,.0f} hp  /  {vehicle.gearbox.name}  /  {vehicle.brakes.name}")
        columns = tk.Frame(page, bg=INK)
        columns.pack(fill="x")
        for label, value in (("Mass", f"{vehicle.mass:,.0f} kg"), ("Drag coefficient", f"{vehicle.cd:.3f}"), ("Frontal area", f"{vehicle.area:.2f} m2"), ("Tyre grip", f"{vehicle.tyre_grip_factor:.2f}")):
            self.card(columns, label, value).pack(side="left", fill="both", expand=True, padx=(0, 8))
        if self.campaign.record_attempt is not None:
            self.section(page, "Official attempt service only")
            tk.Label(page, text="Engine, chassis, and aerodynamic changes are locked until the attempt is complete.", bg=INK, fg=MUTED, font=(FONT, 11)).pack(anchor="w", pady=(0, 10))
            self.action_button(page, "OPEN TRACKSIDE SERVICE", lambda: self.show_page("Trackside Modifications"), True)
            self.action_button(page, "RETURN TO RECORD ATTEMPT", lambda: self.show_page("Team Debrief"))
            return
        self.section(page, "Workshop controls")
        self.action_button(page, "TEST THIS VEHICLE", lambda: self.choose_track_for_vehicle(entry), True)
        self.action_button(page, "Replace engine", lambda: self.choose_component(entry, "engine"))
        self.action_button(page, "Replace gearbox", lambda: self.choose_component(entry, "gearbox"))
        self.action_button(page, "Replace brakes", lambda: self.choose_component(entry, "brakes"))
        if entry.engine_name in AVAILABLE_ENGINES:
            stages = ENGINE_TUNE_STAGES
            current = min(entry.engine_tune_stage, len(stages) - 1)
            next_stage = next_engine_tune_stage(current)
            if next_stage is not None:
                self.action_button(page, f"Tune engine: advance to stage {next_stage}", lambda: self.set_engine_tune(entry, next_stage))
        self.action_button(page, "Tune gearbox ratios", lambda: self.tune_vehicle_gearbox(entry))
        if self.campaign.research.has_gearbox_technology("computer_optimised_gear_ratios"):
            self.action_button(page, "Optimise gear ratios", lambda: self.optimise_vehicle(entry))
        if set(self.campaign.research.aerodynamics_technology) - set(entry.aerodynamics_technology):
            self.action_button(page, "Fit latest aerodynamics package", lambda: self.fit_aero(entry))
        self.action_button(page, "RETIRE TO MUSEUM", lambda: self.retire_garage_vehicle(entry))
        self.action_button(page, "BACK TO GARAGE", lambda: self.show_page("Garage"))

    def retire_garage_vehicle(self, entry):
        if not messagebox.askyesno(
            "Retire vehicle",
            f"Move {entry.vehicle_name} to the museum? It will no longer be available for campaign test runs.",
            parent=self,
        ):
            return
        try:
            retire_vehicle(self.campaign, entry)
        except ValueError as exc:
            messagebox.showerror("Unable to retire vehicle", str(exc), parent=self)
            return
        save_campaign(self.campaign)
        self.show_page("Garage")

    def choose_component(self, entry, component):
        if component == "engine":
            choices = available_engines(self.campaign.research.engine_technology)
        elif component == "gearbox":
            choices = (DIRECT_DRIVE,) if entry.engine_name in AVAILABLE_ENGINES and AVAILABLE_ENGINES[entry.engine_name].torque_curve_type in ("turbojet", "rocket") else TRANSMISSION_CATALOG
        else:
            choices = available_brakes(self.campaign.current_year)
        window = tk.Toplevel(self)
        window.title(f"Replace {component}")
        window.configure(bg=INK)
        window.geometry("620x560")
        tk.Label(window, text=f"SELECT {component.upper()}", bg=INK, fg=PAPER, font=(DISPLAY_FONT, 20, "bold"), padx=22, pady=18).pack(anchor="w")
        container = tk.Frame(window, bg=INK)
        container.pack(fill="both", expand=True, padx=22, pady=(0, 20))
        for choice in choices:
            if component == "engine":
                label = f"{choice.name}  /  {choice.power_hp:,.0f} hp  /  GBP {choice.purchase_cost_gbp:,.0f}"
            elif component == "gearbox":
                label = f"{choice.name}  /  {choice.gear_count} gears  /  GBP {choice.cost_gbp:,.0f}"
            else:
                label = f"{choice.name}  /  {choice.max_braking_g:.2f} g  /  GBP {choice.cost_gbp:,.0f}"
            self.action_button(container, label, lambda selected=choice: self.apply_component(entry, component, selected, window))

    def apply_component(self, entry, component, choice, window):
        if component == "engine":
            entry.engine_name = choice.name
            entry.engine_tune_stage = 0
            default_box = recommended_transmission(choice)
            entry.gearbox_name = default_box.name
            entry.gearbox_ratios = tuple(default_box.gears)
            entry.gearbox_final_drive = default_box.final_drive_ratio
        elif component == "gearbox":
            gearbox = deepcopy(choice)
            entry.gearbox_name = gearbox.name
            entry.gearbox_ratios = tuple(gearbox.gears)
            entry.gearbox_final_drive = gearbox.final_drive_ratio
        else:
            entry.brakes_name = choice.name
        save_campaign(self.campaign)
        window.destroy()
        self.open_garage_vehicle(entry)

    def set_engine_tune(self, entry, stage):
        entry.engine_tune_stage = stage
        save_campaign(self.campaign)
        self.open_garage_vehicle(entry)

    def optimise_vehicle(self, entry):
        vehicle = build_vehicle_from_garage_entry(entry)
        optimize_gearbox_for_engine(vehicle)
        entry.gearbox_name = vehicle.gearbox.name
        entry.gearbox_ratios = tuple(vehicle.gearbox.gears)
        entry.gearbox_final_drive = vehicle.gearbox.final_drive_ratio
        save_campaign(self.campaign)
        self.open_garage_vehicle(entry)

    def fit_aero(self, entry):
        entry.aerodynamics_technology = tuple(self.campaign.research.aerodynamics_technology)
        save_campaign(self.campaign)
        self.open_garage_vehicle(entry)

    def tune_vehicle_gearbox(self, entry):
        self.page = "Garage"
        self._refresh_header()
        for child in self.body.winfo_children():
            child.destroy()
        page = self.scroll_area()
        vehicle = build_vehicle_from_garage_entry(entry)
        self.page_title(page, "Workshop controls", "Gearbox ratios", f"{vehicle.name}  /  Adjust in 0.1 steps. Final drive range: 0.5-6.0; gear range: 0.5-5.0.")
        self._ratio_control(page, entry, None, vehicle.gearbox.final_drive_ratio)
        for index, ratio in enumerate(vehicle.gearbox.gears):
            self._ratio_control(page, entry, index, ratio)
        self.action_button(page, "BACK TO VEHICLE", lambda: self.open_garage_vehicle(entry))

    def _ratio_control(self, parent, entry, gear_index, value):
        label = "Final drive" if gear_index is None else f"Gear {gear_index + 1}"
        row = tk.Frame(parent, bg=PANEL, padx=14, pady=10)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label, bg=PANEL, fg=PAPER, font=(FONT, 10, "bold")).pack(side="left")
        tk.Label(row, text=f"{value:.3f}", bg=PANEL, fg=LIME, font=(FONT, 11, "bold")).pack(side="right", padx=12)
        tk.Button(row, text="+0.1", command=lambda: self.adjust_gearbox_ratio(entry, gear_index, 0.1), bg=PANEL_LIGHT, fg=PAPER, relief="flat", padx=10, pady=5).pack(side="right", padx=3)
        tk.Button(row, text="-0.1", command=lambda: self.adjust_gearbox_ratio(entry, gear_index, -0.1), bg=PANEL_LIGHT, fg=PAPER, relief="flat", padx=10, pady=5).pack(side="right", padx=3)

    def adjust_gearbox_ratio(self, entry, gear_index, delta):
        vehicle = build_vehicle_from_garage_entry(entry)
        if not adjust_gearbox_ratio(vehicle.gearbox, gear_index, delta):
            return
        entry.gearbox_final_drive = vehicle.gearbox.final_drive_ratio
        entry.gearbox_ratios = tuple(vehicle.gearbox.gears)
        save_campaign(self.campaign)
        self.tune_vehicle_gearbox(entry)

    def start_vehicle_builder(self):
        if self.campaign.record_attempt is not None:
            messagebox.showerror(
                "Record attempt in progress",
                "Finish the official return run before designing another vehicle.",
                parent=self,
            )
            return
        self.builder = {"step": "chassis"}
        self.render_builder()

    def render_builder(self):
        self.page = "Garage"
        self._refresh_header()
        for child in self.body.winfo_children():
            child.destroy()
        page = self.scroll_area()
        steps = ("chassis", "engine", "gearbox", "brakes", "name")
        step = self.builder.get("step", "chassis")
        labels = {"chassis": "Select a chassis", "engine": "Select an engine", "gearbox": "Select a gearbox", "brakes": "Select a brake system", "name": "Name your vehicle"}
        self.page_title(page, "Vehicle designer", labels[step], "Choose from unlocked, historically available components. The vehicle name is assigned automatically.")
        if step == "chassis":
            choices = available_chassis(self.campaign.research.chassis_technology)
            for item in choices:
                self.action_button(page, f"{item.name}  /  {item.mass_kg:,.0f} kg  /  GBP {item.cost_gbp:,.0f}\n{item.description}", lambda value=item: self.builder_select("chassis", value))
        elif step == "engine":
            for item in available_engines(self.campaign.research.engine_technology):
                self.action_button(page, f"{item.name}  /  {item.power_hp:,.0f} hp  /  GBP {item.purchase_cost_gbp:,.0f}  /  Reliability {item.reliability:.0%}", lambda value=item: self.builder_select("engine", value))
        elif step == "gearbox":
            engine = self.builder["engine"]
            choices = (DIRECT_DRIVE,) if engine.torque_curve_type in ("turbojet", "rocket") else TRANSMISSION_CATALOG
            for item in choices:
                self.action_button(page, f"{item.name}  /  {item.gear_count} gears  /  {item.efficiency:.0%} efficiency  /  GBP {item.cost_gbp:,.0f}", lambda value=item: self.builder_select("gearbox", value))
        elif step == "brakes":
            for item in available_brakes(self.campaign.current_year):
                self.action_button(page, f"{item.name}  /  {item.max_braking_g:.2f} g  /  GBP {item.cost_gbp:,.0f}", lambda value=item: self.builder_select("brakes", value))
        else:
            default_name = self.builder.setdefault(
                "vehicle_name", next_vehicle_name(self.campaign)
            )
            tk.Label(page, text="Vehicle name", bg=INK, fg=PAPER, font=(FONT, 10, "bold")).pack(anchor="w", pady=(8, 4))
            name_input = tk.Entry(page, bg=PANEL, fg=PAPER, insertbackground=PAPER, relief="flat", font=(FONT, 12))
            name_input.insert(0, default_name)
            name_input.pack(fill="x", pady=(0, 12), ipady=8)
            self.action_button(
                page,
                "CONFIRM VEHICLE NAME",
                lambda: self.builder_select("name", name_input.get()),
                True,
            )
        self.action_button(page, "CANCEL DESIGN", lambda: self.show_page("Garage"))

    def builder_select(self, key, value):
        if key == "name":
            self.confirm_vehicle_name(value)
            return
        self.builder[key] = value
        order = ("chassis", "engine", "gearbox", "brakes", "name")
        current_index = order.index(key)
        if current_index < len(order) - 1:
            self.builder["step"] = order[current_index + 1]
            self.render_builder()
            return
        self.render_builder()

    def confirm_vehicle_name(self, vehicle_name):
        name = vehicle_name.strip()
        if not name:
            messagebox.showerror("Vehicle name required", "Enter a name for this vehicle.", parent=self)
            return
        existing_names = {
            entry.vehicle_name.casefold()
            for entry in self.campaign.garage.vehicles + self.campaign.garage.museum
        }
        if name.casefold() in existing_names:
            messagebox.showerror(
                "Vehicle name already used",
                "Choose a name that is not already in the garage or museum.",
                parent=self,
            )
            return
        self.finish_vehicle_build(name)

    def finish_vehicle_build(self, name):
        chassis = self.builder["chassis"]
        engine = self.builder["engine"]
        gearbox = deepcopy(self.builder["gearbox"])
        brakes = replace(self.builder["brakes"])
        aero = tuple(self.campaign.research.aerodynamics_technology)
        effect = aerodynamics_effects(aero)
        vehicle = Vehicle(
            name=name,
            mass=chassis.mass_kg,
            cd=chassis.drag_coefficient * (1.0 - effect["drag_reduction"]),
            area=chassis.frontal_area_m2,
            tyre_grip_factor=chassis.tyre_grip_factor,
            engine=engine,
            wheel_radius_m=chassis.wheel_radius_m,
            gearbox=gearbox,
            brakes=brakes,
            component_mass_enabled=True,
        )
        vehicle.chassis_id = chassis.chassis_id
        vehicle.aerodynamics_technology = aero
        cost = round(chassis.cost_gbp + engine.purchase_cost_gbp + gearbox.cost_gbp + brakes.cost_gbp)
        from management import GarageVehicle

        entry = GarageVehicle(
            vehicle_name=name,
            chassis_id=chassis.chassis_id,
            engine_name=engine.name,
            gearbox_name=gearbox.name,
            brakes_name=brakes.name,
            aerodynamics_technology=aero,
            gearbox_ratios=tuple(gearbox.gears),
            gearbox_final_drive=gearbox.final_drive_ratio,
        )
        if not messagebox.askyesno("Confirm construction", f"Build {name} for GBP {cost:,.0f}?\nAvailable funds: GBP {self.campaign.team.cash:,.0f}", parent=self):
            self.show_page("Garage")
            return
        try:
            build_vehicle(self.campaign, entry, cost, vehicle=vehicle)
            save_campaign(self.campaign)
        except ValueError as exc:
            messagebox.showerror("Unable to build vehicle", str(exc), parent=self)
        self.show_page("Garage")

    def render_test_runs(self):
        page = self.scroll_area()
        self.page_title(page, "Track operations", "Prepare a test run", "Select a garage vehicle, then an available circuit. The simulation, costs, reliability checks, records, and campaign turn are unchanged.")
        if self.garage_return_required:
            self.section(page, "Workshop repair required")
            tk.Label(page, text="A major failure must be inspected in the Garage before campaign testing can continue.", bg=INK, fg=MUTED, font=(FONT, 11)).pack(anchor="w")
            self.action_button(page, "RETURN TO GARAGE", lambda: self.show_page("Garage"), True)
            return
        if self.campaign.workshop_repair_pending:
            self.section(page, "Car in the workshop")
            tk.Label(page, text="The workshop is repairing major failure damage. Testing resumes next turn.", bg=INK, fg=MUTED, font=(FONT, 11)).pack(anchor="w")
            self.action_button(page, "END TURN", self.end_turn, True)
            return
        if (
            self.last_run_outcome is not None
            and self.last_run_outcome.failed
            and self.last_run_outcome.repaired
            and not self.last_run_repaired
        ):
            self.section(page, "Trackside repair required")
            tk.Label(page, text="Repair the minor issue at the track before starting another test.", bg=INK, fg=MUTED, font=(FONT, 11)).pack(anchor="w")
            self.action_button(page, "RETURN TO TEAM DEBRIEF", lambda: self.show_page("Team Debrief"), True)
            return
        if self.campaign.record_attempt is not None:
            attempt = self.campaign.record_attempt
            completed_passes = len(attempt.speeds_mph)
            self.section(
                page,
                f"Official record attempt  /  pass {completed_passes + 1} of {attempt.required_runs}",
            )
            if attempt.speeds_mph:
                self.section(
                    page,
                    f"Outbound pass {attempt.speeds_mph[0]:.1f} mph  /  return run required",
                )
            self.action_button(
                page,
                "RESUME OFFICIAL RECORD ATTEMPT",
                self.resume_record_attempt,
                True,
            )
            return
        tests_remaining = session_runs_remaining(self.campaign)
        self.section(
            page,
            f"Test session  /  {self.campaign.tests_this_session} of {MAX_TESTS_PER_SESSION} hourly tests  /  "
            f"Record session  /  {self.campaign.record_runs_this_session} of {MAX_RECORD_RUNS_PER_SESSION} runs",
        )
        if not self.campaign.garage.vehicles:
            self.section(page, "Garage vehicles")
            tk.Label(page, text="No campaign vehicles are available. Build one in the Garage first.", bg=INK, fg=MUTED, font=(FONT, 11)).pack(anchor="w")
            return
        if tests_remaining <= 0:
            tk.Label(page, text="This turn's test session is complete. End the turn to begin another.", bg=INK, fg=MUTED, font=(FONT, 11)).pack(anchor="w")
        else:
            self.section(page, "Garage vehicles")
            for entry in self.campaign.garage.vehicles:
                self.action_button(page, f"{entry.vehicle_name}  /  {entry.engine_name}  /  {entry.gearbox_name}", lambda selected=entry: self.choose_track_for_vehicle(selected))
        target = next_historical_target(self.campaign.current_year, self.campaign.completed_historical_record_ids)
        if target:
            self.section(page, "Historical record attempt")
            if session_runs_remaining(self.campaign, record=True) >= required_record_runs(self.campaign.current_year):
                self.action_button(page, f"Attempt {target.year} {target.vehicle}  /  {target.speed_mph:.1f} mph", self.start_record_attempt, True)
            else:
                tk.Label(page, text="This turn's record session is complete. End the turn to begin another.", bg=INK, fg=MUTED, font=(FONT, 11)).pack(anchor="w")

    def render_test_facility(self):
        page = self.scroll_area()
        self.page_title(page, "Engineering test facility", "Unlimited test programme", "Sandbox runs use all historical vehicles and venues. They do not charge funds, advance the campaign, or write campaign records.")
        self.section(page, "Select a test vehicle")
        for factory in AVAILABLE_CARS.values():
            vehicle = factory()
            self.action_button(page, f"{vehicle.name}  /  {vehicle.engine.name}  /  {vehicle.power:,.0f} hp", lambda create=factory: self.choose_facility_track(create()))

    def choose_facility_track(self, vehicle):
        for child in self.body.winfo_children():
            child.destroy()
        page = self.scroll_area()
        self.page_title(page, "Engineering test facility", "Select a venue", f"Sandbox vehicle: {vehicle.name}.")
        for track in AVAILABLE_TRACKS.values():
            self.action_button(page, f"{track.name}  /  {track.length_miles:g} mi  /  friction {track.friction_factor:.2f}", lambda venue=track: self.run_facility_test(vehicle, venue))
        self.action_button(page, "BACK TO TEST FACILITY", lambda: self.show_page("Test Facility"))

    def run_facility_test(self, vehicle, track):
        result = run_simulation(
            vehicle,
            track_miles=track.length_miles,
            measured_mile_start=track.measured_mile_start,
            track_friction_factor=track.friction_factor,
            air_density_kg_m3=track.air_density_kg_m3,
        )
        append_run_log(vehicle, track, result)
        self.last_report = create_engineering_report(
            vehicle, track, result, previous_report=self.last_report
        )
        self.last_run_is_sandbox = True
        self.last_result = result
        self.last_vehicle = vehicle
        self.last_vehicle_entry = None
        self.last_track = track
        self.last_run_note = "Engineering facility / sandbox result. The campaign was not changed."
        self.last_record_message = None
        self.show_page("Team Debrief")

    def choose_track_for_vehicle(self, entry, record_attempt=False):
        self.selected_vehicle = entry
        self._render_track_choices(record_attempt)

    def _render_track_choices(self, record_attempt=False, record_target=None):
        for child in self.body.winfo_children():
            child.destroy()
        page = self.scroll_area()
        entry = self.selected_vehicle
        self.page_title(page, "Track operations", "Select a venue", f"Vehicle: {entry.vehicle_name}. Available tracks follow the campaign year.")
        for track in available_tracks(self.campaign.current_year).values():
            vehicle = build_vehicle_from_garage_entry(entry)
            cost = calculate_session_run_cost(self.campaign, track)
            self.action_button(page, f"{track.name}  /  {track.length_miles:g} mi  /  friction {track.friction_factor:.2f}  /  estimated GBP {cost:,.0f}", lambda venue=track: self.execute_run(entry, venue, record_attempt, record_target=record_target))
        self.action_button(page, "BACK", lambda: self.show_page("Test Runs"))

    def start_record_attempt(self):
        if self.campaign.record_attempt is not None:
            self.resume_record_attempt()
            return
        target = next_historical_target(self.campaign.current_year, self.campaign.completed_historical_record_ids)
        if not target:
            messagebox.showinfo("Campaign records", "All historical campaign goals have been completed.", parent=self)
            return
        if not self.campaign.garage.vehicles:
            messagebox.showinfo("Garage required", "Build a garage vehicle before attempting a historical record.", parent=self)
            return
        self.selected_vehicle = self.campaign.garage.vehicles[0]
        self._render_record_vehicle_choices(target)

    def _render_record_vehicle_choices(self, target):
        for child in self.body.winfo_children():
            child.destroy()
        page = self.scroll_area()
        self.page_title(page, "Historical campaign", f"Record target / {target.year}", f"Beat {target.vehicle} at {target.speed_mph:.1f} mph. {target.milestone}")
        for entry in self.campaign.garage.vehicles:
            self.action_button(page, entry.vehicle_name, lambda selected=entry: self.choose_record_track(selected, target))

    def choose_record_track(self, entry, target):
        self.selected_vehicle = entry
        self._render_track_choices(record_attempt=True, record_target=target)

    def resume_record_attempt(self):
        attempt = self.campaign.record_attempt
        if attempt is None:
            return
        entry = next(
            (
                vehicle
                for vehicle in self.campaign.garage.vehicles
                if vehicle.vehicle_name == attempt.vehicle_name
            ),
            None,
        )
        track = next(
            (
                venue
                for venue in AVAILABLE_TRACKS.values()
                if venue.name == attempt.track_name
            ),
            None,
        )
        target = next(
            (item for item in HISTORICAL_TARGETS if item.record_id == attempt.target_id),
            None,
        )
        if entry is None or track is None or target is None:
            messagebox.showerror(
                "Record attempt unavailable",
                "The saved vehicle, venue, or target could not be found.",
                parent=self,
            )
            return
        self.execute_run(
            entry, track, record_attempt=True, record_target=target
        )

    def execute_run(
        self,
        entry,
        track,
        record_attempt=False,
        waive_venue_fee=False,
        record_target=None,
    ):
        if self.garage_return_required:
            messagebox.showerror(
                "Workshop repair required",
                "Return to the Garage before starting another campaign test.",
                parent=self,
            )
            return
        if self.campaign.workshop_repair_pending:
            messagebox.showerror(
                "Car in the workshop",
                "The workshop is repairing major failure damage. End the turn to resume testing.",
                parent=self,
            )
            return
        if (
            self.last_run_outcome is not None
            and self.last_run_outcome.failed
            and self.last_run_outcome.repaired
            and not self.last_run_repaired
        ):
            messagebox.showerror(
                "Trackside repair required",
                "Repair the minor issue before starting another campaign test.",
                parent=self,
            )
            return
        active_attempt = self.campaign.record_attempt
        if active_attempt is not None and not record_attempt:
            messagebox.showerror(
                "Official record attempt in progress",
                "Complete the required return run before starting an ordinary test.",
                parent=self,
            )
            return
        if record_attempt:
            if active_attempt is not None and (
                active_attempt.vehicle_name != entry.vehicle_name
                or active_attempt.track_name != track.name
            ):
                messagebox.showerror(
                    "Record attempt locked",
                    "The return run must use the same vehicle and venue as the first pass.",
                    parent=self,
                )
                return
            if record_target is None and active_attempt is not None:
                record_target = next(
                    (
                        target
                        for target in HISTORICAL_TARGETS
                        if target.record_id == active_attempt.target_id
                    ),
                    None,
                )
            if record_target is None:
                record_target = next_historical_target(
                    self.campaign.current_year,
                    self.campaign.completed_historical_record_ids,
                )
            if record_target is None:
                messagebox.showinfo(
                    "Campaign records",
                    "All historical campaign goals have been completed.",
                    parent=self,
                )
                return
            if active_attempt is None:
                required_slots = required_record_runs(self.campaign.current_year)
                available_slots = session_runs_remaining(self.campaign, record=True)
                if required_slots > available_slots:
                    messagebox.showerror(
                        "Not enough record runs",
                        f"This official attempt requires {required_slots} record runs; {available_slots} remain in this turn's record session. End the turn to start another.",
                        parent=self,
                    )
                    return
        else:
            record_target = next_historical_target(
                self.campaign.current_year,
                self.campaign.completed_historical_record_ids,
            )
        if session_runs_remaining(self.campaign, record=record_attempt) <= 0:
            messagebox.showerror(
                "Session full",
                "No runs remain in this turn's record session."
                if record_attempt
                else "This turn's test session is limited to eight hourly tests. End the turn to start another session.",
                parent=self,
            )
            return
        vehicle = build_vehicle_from_garage_entry(entry)
        cost = (
            0
            if waive_venue_fee
            else calculate_session_run_cost(self.campaign, track)
        )
        if cost > self.campaign.team.cash:
            messagebox.showerror("Insufficient funds", f"This run costs GBP {cost:,.0f}; the campaign has GBP {self.campaign.team.cash:,.0f}.", parent=self)
            return
        venue_note = (
            "Venue fee already paid for this session."
            if cost == 0
            else f"Venue fee: GBP {cost:,.0f}."
        )
        if record_attempt:
            session_label = f"Record run {self.campaign.record_runs_this_session + 1} of {MAX_RECORD_RUNS_PER_SESSION}"
        else:
            session_label = f"Session test {self.campaign.tests_this_session + 1} of {MAX_TESTS_PER_SESSION}"
        if not messagebox.askyesno("Confirm test run", f"{vehicle.name} at {track.name}\n{venue_note}\n{session_label}\nProceed with simulation?", parent=self):
            return
        if record_attempt:
            register_record_run(self.campaign)
        else:
            register_test_run(self.campaign)
        mark_session_venue_paid(self.campaign, track)
        if record_attempt and active_attempt is None:
            active_attempt = CampaignRecordAttempt(
                target_id=record_target.record_id,
                vehicle_name=entry.vehicle_name,
                track_name=track.name,
                started_year=self.campaign.current_year,
                required_runs=required_record_runs(self.campaign.current_year),
            )
            self.campaign.record_attempt = active_attempt
        result = run_simulation(
            vehicle,
            track_miles=track.length_miles,
            measured_mile_start=track.measured_mile_start,
            track_friction_factor=track.friction_factor,
            air_density_kg_m3=track.air_density_kg_m3,
        )
        outcome = resolve_run_failure(
            vehicle.engine,
            result.peak_speed_mph,
            self.campaign.team,
            gearbox=vehicle.gearbox,
            brake_fade=any(sample.brake_fade for sample in result.telemetry),
            sponsor_reliability_bonus=self.campaign.sponsorship.reliability_bonus,
        )
        append_run_log(vehicle, track, result, outcome=outcome)
        self.last_record_message = None
        record_attempt_completed = False
        record_average_mph = None
        if outcome.failed:
            complete_failed_run(self.campaign, cost)
            self.last_run_note = f"ABORTED: {outcome.failure_type.name}. Failure probability {outcome.failure_probability:.1%}."
            if record_attempt and not outcome.repaired:
                self.campaign.record_attempt = None
            if not outcome.repaired:
                self.campaign.workshop_repair_pending = True
        else:
            if record_attempt:
                active_attempt.speeds_mph.append(result.measured_mile_speed_mph)
                record_attempt_completed = (
                    len(active_attempt.speeds_mph) >= active_attempt.required_runs
                )
                if record_attempt_completed:
                    record_average_mph = average_record_speed(
                        active_attempt.speeds_mph
                    )
                sponsor_messages = complete_run(
                    self.campaign,
                    cost,
                    result.measured_mile_speed_mph,
                    is_record_attempt=record_attempt_completed,
                    record_attempt_average_mph=record_average_mph,
                )
                if record_attempt_completed:
                    self.campaign.record_attempt = None
                    if target_completed(record_target, record_average_mph):
                        self.last_record_message = (
                            f"Official average: {record_average_mph:.1f} mph. "
                            f"{record_target.year} {record_target.vehicle} benchmark beaten."
                        )
                    else:
                        self.last_record_message = (
                            f"Official average: {record_average_mph:.1f} mph. "
                            f"Target was {record_target.speed_mph:.1f} mph; attempt not credited."
                        )
                else:
                    self.last_record_message = (
                        f"Outbound pass recorded at {result.measured_mile_speed_mph:.1f} mph. "
                        "An opposite-direction return pass is required."
                    )
            else:
                sponsor_messages = complete_run(
                    self.campaign, cost, result.measured_mile_speed_mph
                )
            self.last_run_note = " ".join(
                [f"Completed. Measured mile {result.measured_mile_speed_mph:.1f} mph; peak {result.peak_speed_mph:.1f} mph."]
                + list(sponsor_messages or ())
            )
            save_record(create_record(vehicle, track, result, self.campaign))
        if lapse_record_attempt_if_out_of_runs(self.campaign):
            self.last_record_message = "Not enough record runs remain this turn to finish the attempt; it has lapsed."
            record_attempt = False
        save_campaign(self.campaign)
        self.last_report = create_engineering_report(
            vehicle, track, result, self.campaign, outcome,
            previous_report=self.last_report, target=record_target,
            is_record_attempt=record_attempt_completed,
            record_attempt_in_progress=(
                record_attempt and not record_attempt_completed and not outcome.failed
            ),
            record_attempt_average_mph=record_average_mph,
        )
        self.last_run_is_sandbox = False
        self.last_result = result
        self.last_vehicle = vehicle
        self.last_vehicle_entry = entry
        self.last_trackside_ratio_adjusted = False
        self.last_track = track
        self.last_run_outcome = outcome
        self.last_run_repaired = False
        self.last_run_was_record_attempt = record_attempt
        self.garage_return_required = outcome.failed and not outcome.repaired
        if self.garage_return_required and record_attempt:
            self.last_run_was_record_attempt = False
        self.show_page("Team Debrief")
        if self.garage_return_required:
            self.offer_end_turn_after_failure(outcome.failure_type.name)

    def offer_end_turn_after_failure(self, failure_name):
        if messagebox.askyesno(
            "Return to workshop",
            f"{failure_name}: the car must go back to the workshop, so testing is over for this turn.\n\nEnd the turn now?",
            parent=self,
        ):
            self.advance_campaign_turn()
            save_campaign(self.campaign)
            self.show_page("Dashboard")

    def render_team_debrief(self):
        page = self.scroll_area()
        self.page_title(page, "Racing department / team debrief", "Chief Engineer Report")
        if self.last_report is None:
            tk.Label(page, text="No run to review.", bg=INK, fg=MUTED, font=(FONT, 11)).pack(anchor="w", pady=16)
            self.action_button(page, "PREPARE A TEST RUN", lambda: self.show_page("Test Runs"), True)
            self.action_button(page, "OPEN TEST FACILITY", lambda: self.show_page("Test Facility"))
            return
        report = self.last_report

        def report_text(text, color=PAPER, font=(FONT, 11)):
            label = tk.Label(page, text=text, bg=INK, fg=color, font=font, justify="left", anchor="w", wraplength=1000)
            label.pack(fill="x", pady=(4, 8))
            label.bind("<Configure>", lambda event: label.configure(wraplength=max(1, event.width - 8)))

        report_text(f"Vehicle: {report.vehicle_name}  /  Venue: {report.track_name}", MUTED)
        report_text(report.run_status, LIME if report.completed else ACCENT, (FONT, 10, "bold"))
        report_text(self.last_run_note, MUTED)
        if not self.last_run_is_sandbox and report.completed and self.last_result is not None:
            chase_target = next_historical_target(
                self.campaign.current_year,
                self.campaign.completed_historical_record_ids,
            )
            if chase_target is not None:
                gap = chase_target.speed_mph - self.last_result.measured_mile_speed_mph
                report_text(
                    f"Target: {chase_target.speed_mph:.1f} mph ({chase_target.year} {chase_target.vehicle}). "
                    + (
                        f"This run was {gap:.1f} mph short."
                        if gap > 0
                        else f"This run cleared it by {-gap:.1f} mph. Make it official with a record attempt."
                    ),
                    ACCENT if gap > 0 else LIME,
                    (FONT, 12, "bold"),
                )
        if not self.last_run_is_sandbox:
            report_text(
                f"Test session: {self.campaign.tests_this_session} of {MAX_TESTS_PER_SESSION} hourly tests used  /  "
                f"Record session: {self.campaign.record_runs_this_session} of {MAX_RECORD_RUNS_PER_SESSION} runs used.",
                MUTED,
            )
        if self.last_record_message:
            report_text(self.last_record_message, LIME)
        self.section(page, "Primary concern")
        report_text(report.diagnosis.problem, ACCENT, (DISPLAY_FONT, 18, "bold"))
        self.section(page, "Evidence")
        report_text(report.diagnosis.evidence)
        result = self.last_result
        report_text(
            f"Peak: {result.peak_speed_mph:.1f} mph  /  Measured mile: {result.measured_mile_speed_mph:.1f} mph\n"
            f"Average acceleration: {result.average_acceleration_g:.3f} G  /  Average deceleration: {result.average_deceleration_g:.3f} G\n"
            f"Brake temperature: {result.maximum_brake_temperature_c:.0f} C  /  Wheelspin events: {result.wheelspin_event_count}",
            MUTED,
        )
        self.section(page, "Recommendations")
        for number, recommendation in enumerate(report.recommendations, start=1):
            report_text(f"{number}. {recommendation}")
        if not self.last_run_is_sandbox and self.last_vehicle_entry is not None:
            suggestion = suggest_gear_ratio_adjustment(
                self.last_vehicle,
                self.last_result,
                self.last_track.friction_factor,
            )
            if suggestion is not None:
                self.section(page, "Mechanic's ratio suggestion")
                report_text(suggestion.description, MUTED)
                if self.last_trackside_ratio_adjusted:
                    report_text(
                        "Adjustment applied. Run another test for fresh advice.",
                        MUTED,
                    )
        if (
            not self.last_run_is_sandbox
            and self.last_run_outcome is not None
            and self.last_run_outcome.failed
        ):
            if self.last_run_outcome.repaired:
                self.section(page, "Trackside repair")
                if not self.last_run_repaired:
                    report_text(
                        "A minor fault can be repaired by the track crew.", MUTED
                    )
                    self.action_button(
                        page,
                        "REPAIR MINOR ISSUE AT TRACKSIDE",
                        self.repair_failed_run_trackside,
                        True,
                    )
                else:
                    report_text("Trackside repair complete. The venue fee is waived for the rerun.", MUTED)
                    if session_runs_remaining(self.campaign, record=self.last_run_was_record_attempt) > 0:
                        self.action_button(
                            page,
                            "RERUN AT NO COST",
                            self.rerun_failed_test,
                            True,
                        )
                        if (
                            self.last_run_was_record_attempt
                            and self.campaign.record_attempt is not None
                        ):
                            self.action_button(
                                page,
                                "TRACKSIDE MODIFICATIONS",
                                lambda: self.show_page("Trackside Modifications"),
                            )
                    else:
                        report_text(
                            "No runs remain in this session. End the turn before retesting.",
                            MUTED,
                        )
                return

            self.section(page, "Workshop repair required")
            report_text(
                "This failure cannot be repaired trackside. Return to the Garage before another campaign test.",
                ACCENT,
            )
            self.action_button(
                page,
                "RETURN TO GARAGE",
                lambda: self.show_page("Garage"),
                True,
            )
            return
        if (
            not self.last_run_is_sandbox
            and self.last_run_was_record_attempt
            and self.campaign.record_attempt is not None
        ):
            attempt = self.campaign.record_attempt
            self.section(page, "Official record attempt in progress")
            average = average_record_speed(attempt.speeds_mph)
            report_text(
                f"Outbound pass: {attempt.speeds_mph[0]:.1f} mph  /  Current average: {average:.1f} mph. "
                "A return pass in the opposite direction is mandatory.",
                MUTED,
            )
            if attempt.started_year >= 1950:
                report_text(
                    "FIA turnaround: the return pass uses the next one-hour test slot.",
                    MUTED,
                )
            self.action_button(
                page,
                "TRACKSIDE MODIFICATIONS",
                lambda: self.show_page("Trackside Modifications"),
            )
            self.action_button(
                page,
                "START RETURN RUN / OPPOSITE DIRECTION",
                self.resume_record_attempt,
                True,
            )
            return
        self.section(page, "Team assessment")
        report_text(report.comparison, MUTED)
        report_text(report.target_assessment, LIME if report.completed else ACCENT)
        self.action_button(page, "VIEW TELEMETRY", lambda: self.show_page("Telemetry"))
        if self.last_run_is_sandbox:
            self.action_button(page, "RETURN TO TEST FACILITY", lambda: self.show_page("Test Facility"), True)
        else:
            self.action_button(page, f"REVIEW {report.research_branch.upper()} RESEARCH", lambda: self.set_research_branch(report.research_branch), True)
            self.action_button(page, "TRACKSIDE MODIFICATIONS", lambda: self.show_page("Trackside Modifications"))
            self.action_button(page, "PREPARE NEXT TEST", lambda: self.show_page("Test Runs"))
            if self.last_run_was_record_attempt:
                self._offer_another_record_attempt(page)
            elif report.completed and self.campaign.garage.vehicles and next_historical_target(self.campaign.current_year, self.campaign.completed_historical_record_ids):
                self.action_button(page, "PLAN RECORD ATTEMPT", self.start_record_attempt)

    def _offer_another_record_attempt(self, page):
        if next_historical_target(self.campaign.current_year, self.campaign.completed_historical_record_ids) is None:
            return
        remaining = session_runs_remaining(self.campaign, record=True)
        if remaining >= required_record_runs(self.campaign.current_year):
            self.action_button(page, f"START ANOTHER RECORD ATTEMPT  /  {remaining} RECORD RUNS REMAINING", self.start_another_record_attempt, True)
        else:
            tk.Label(page, text="This turn's record session is complete. End the turn to begin another.", bg=INK, fg=MUTED, font=(FONT, 11)).pack(anchor="w", pady=8)

    def start_another_record_attempt(self):
        self.execute_run(self.last_vehicle_entry, self.last_track, record_attempt=True)

    def repair_failed_run_trackside(self):
        if (
            self.last_run_outcome is None
            or not self.last_run_outcome.failed
            or not self.last_run_outcome.repaired
        ):
            return
        self.last_run_repaired = True
        self.last_run_note += " Minor issue repaired trackside."
        self.show_page("Team Debrief")

    def rerun_failed_test(self):
        if not self.last_run_repaired:
            return
        self.execute_run(
            self.last_vehicle_entry,
            self.last_track,
            record_attempt=self.last_run_was_record_attempt,
            waive_venue_fee=True,
        )

    def render_trackside_modifications(self):
        page = self.scroll_area()
        entry = self.last_vehicle_entry
        if self.last_run_is_sandbox or entry is None:
            self.page_title(page, "Trackside service", "No campaign vehicle", "Run a campaign vehicle test to open trackside modifications.")
            self.action_button(page, "BACK TO DEBRIEF", lambda: self.show_page("Team Debrief"))
            return

        vehicle = build_vehicle_from_garage_entry(entry)
        attempt = self.campaign.record_attempt
        tests_remaining = session_runs_remaining(self.campaign, record=attempt is not None)
        self.page_title(
            page,
            "Trackside service",
            "Trackside modifications",
            f"{vehicle.name}  /  {self.last_track.name}  /  {tests_remaining} {'record run' if attempt else 'hourly test'}(s) remaining this turn.",
        )
        suggestion = suggest_gear_ratio_adjustment(
            self.last_vehicle, self.last_result, self.last_track.friction_factor
        )
        if suggestion is not None:
            self.section(page, "Mechanic's suggestion")
            tk.Label(page, text=suggestion.description, bg=INK, fg=MUTED, font=(FONT, 11), wraplength=1000, justify="left").pack(anchor="w", pady=(0, 8))
            if suggestion.changes_needed and not self.last_trackside_ratio_adjusted:
                self.action_button(
                    page,
                    f"APPLY SUGGESTION / GBP {TRACKSIDE_ADJUSTMENT_COST_GBP:.0f}",
                    self.apply_trackside_ratio_suggestion,
                )

        self.section(page, "Gearbox ratios")
        self._trackside_ratio_control(
            page, entry, None, vehicle.gearbox.final_drive_ratio
        )
        for index, ratio in enumerate(vehicle.gearbox.gears):
            self._trackside_ratio_control(page, entry, index, ratio)

        self.section(page, "Tyres")
        if entry.tyre_grip_factor is None:
            self.action_button(
                page,
                f"FIT TRACKSIDE TYRES (+0.03 GRIP) / GBP {TRACKSIDE_ADJUSTMENT_COST_GBP:.0f}",
                self.fit_trackside_tyres,
            )
        else:
            tk.Label(page, text=f"Trackside tyre set fitted  /  Grip {vehicle.tyre_grip_factor:.2f}", bg=INK, fg=MUTED, font=(FONT, 10)).pack(anchor="w")

        self.section(page, "Brakes")
        for brakes in available_brakes(self.campaign.current_year):
            if brakes.name == entry.brakes_name:
                continue
            self.action_button(
                page,
                f"FIT {brakes.name.upper()} / GBP {TRACKSIDE_ADJUSTMENT_COST_GBP:.0f}",
                lambda item=brakes: self.fit_trackside_brake_system(item.name),
            )

        if attempt is not None:
            run_label = (
                "RUN FIRST PASS"
                if not attempt.speeds_mph
                else "RUN RETURN PASS / OPPOSITE DIRECTION"
            )
            if tests_remaining > 0:
                self.action_button(
                    page,
                    f"{run_label} / {tests_remaining} RECORD RUNS REMAINING",
                    self.resume_record_attempt,
                    True,
                )
            else:
                tk.Label(page, text="Record session complete. End the turn to open another session.", bg=INK, fg=MUTED, font=(FONT, 11)).pack(anchor="w", pady=8)
        else:
            if self.last_run_was_record_attempt:
                self._offer_another_record_attempt(page)
            if tests_remaining > 0:
                self.action_button(
                    page,
                    f"RUN ANOTHER TEST HERE / {tests_remaining} REMAINING",
                    lambda: self.execute_run(entry, self.last_track),
                    not self.last_run_was_record_attempt,
                )
            else:
                tk.Label(page, text="Test session complete. End the turn to open another session.", bg=INK, fg=MUTED, font=(FONT, 11)).pack(anchor="w", pady=8)
        self.action_button(page, "VIEW LAST TELEMETRY", lambda: self.show_page("Telemetry"))
        self.action_button(page, "BACK TO DEBRIEF", lambda: self.show_page("Team Debrief"))

    def _trackside_ratio_control(self, parent, entry, gear_index, value):
        label = "Final drive" if gear_index is None else f"Gear {gear_index + 1}"
        row = tk.Frame(parent, bg=PANEL, padx=14, pady=10)
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label, bg=PANEL, fg=PAPER, font=(FONT, 10, "bold")).pack(side="left")
        tk.Label(row, text=f"{value:.3f}", bg=PANEL, fg=LIME, font=(FONT, 11, "bold")).pack(side="right", padx=12)
        for delta in (-0.1, 0.1):
            tk.Button(
                row,
                text=f"{delta:+.1f}",
                command=lambda change=delta: self.adjust_trackside_ratio(entry, gear_index, change),
                bg=PANEL_LIGHT,
                fg=PAPER,
                relief="flat",
                padx=10,
                pady=5,
            ).pack(side="right", padx=3)

    def adjust_trackside_ratio(self, entry, gear_index, delta):
        try:
            adjust_vehicle_ratio_trackside(
                self.campaign, entry, gear_index, delta
            )
        except ValueError as exc:
            messagebox.showerror("Trackside adjustment unavailable", str(exc), parent=self)
            return
        self.last_trackside_ratio_adjusted = True
        self.last_vehicle = build_vehicle_from_garage_entry(entry)
        save_campaign(self.campaign)
        self.show_page("Trackside Modifications")

    def apply_trackside_ratio_suggestion(self):
        suggestion = suggest_gear_ratio_adjustment(
            self.last_vehicle, self.last_result, self.last_track.friction_factor
        )
        if suggestion is None or not suggestion.changes_needed:
            return
        try:
            apply_gear_ratios_trackside(
                self.campaign,
                self.last_vehicle_entry,
                suggestion.gears,
                suggestion.final_drive,
            )
        except ValueError as exc:
            messagebox.showerror("Trackside adjustment unavailable", str(exc), parent=self)
            return
        self.last_trackside_ratio_adjusted = True
        self.last_vehicle = build_vehicle_from_garage_entry(self.last_vehicle_entry)
        save_campaign(self.campaign)
        self.show_page("Trackside Modifications")

    def fit_trackside_tyres(self):
        try:
            fit_trackside_tyres(self.campaign, self.last_vehicle_entry)
        except ValueError as exc:
            messagebox.showerror("Trackside tyre change unavailable", str(exc), parent=self)
            return
        self.last_vehicle = build_vehicle_from_garage_entry(self.last_vehicle_entry)
        save_campaign(self.campaign)
        self.show_page("Trackside Modifications")

    def fit_trackside_brake_system(self, brakes_name):
        try:
            fit_trackside_brakes(
                self.campaign,
                self.last_vehicle_entry,
                brakes_name,
                self.campaign.current_year,
            )
        except ValueError as exc:
            messagebox.showerror("Trackside brake service unavailable", str(exc), parent=self)
            return
        self.last_vehicle = build_vehicle_from_garage_entry(self.last_vehicle_entry)
        save_campaign(self.campaign)
        self.show_page("Trackside Modifications")

    def render_telemetry(self):
        page = self.scroll_area()
        if self.last_result is None:
            self.page_title(page, "Run telemetry", "Telemetry", "Speed and acceleration traces appear here after a test run.")
            self.action_button(page, "PREPARE A TEST RUN", lambda: self.show_page("Test Runs"), True)
            return
        result = self.last_result
        self.page_title(page, f"{self.last_vehicle.name}  /  {self.last_track.name}", "Run telemetry", self.last_run_note)
        self.action_button(page, "OPEN TEAM DEBRIEF", lambda: self.show_page("Team Debrief"))
        if self.last_record_message:
            notice = tk.Frame(page, bg=PANEL, padx=14, pady=10)
            notice.pack(fill="x", pady=(0, 12))
            tk.Label(
                notice,
                text="RECORD BEATEN",
                bg=PANEL,
                fg=LIME,
                font=(FONT, 10, "bold"),
            ).pack(anchor="w")
            tk.Label(
                notice,
                text=self.last_record_message,
                bg=PANEL,
                fg=PAPER,
                font=(FONT, 10),
                wraplength=1000,
                justify="left",
            ).pack(anchor="w", pady=(3, 0))
        metrics = tk.Frame(page, bg=INK)
        metrics.pack(fill="x", pady=(0, 10))
        for label, value, sub in (("Measured mile", f"{result.measured_mile_speed_mph:.1f} mph", f"{result.measured_mile_time_seconds:.1f} s"), ("Peak speed", f"{result.peak_speed_mph:.1f} mph", f"{result.total_time_seconds:.1f} s total"), ("Average acceleration", f"{result.average_acceleration_g:.3f} G", f"{result.gear_change_count} gear changes"), ("Brake temperature", f"{result.maximum_brake_temperature_c:.0f} C", f"{result.wheelspin_event_count} wheelspin events")):
            self.card(metrics, label, value, sub).pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.section(page, "Speed / time")
        measured_mile_markers = []
        for distance, label in (
            (self.last_track.measured_mile_start, "MILE ENTRY"),
            (self.last_track.measured_mile_start + 1.0, "MILE EXIT"),
        ):
            for previous, sample in zip(result.telemetry, result.telemetry[1:]):
                if previous.distance_miles <= distance <= sample.distance_miles:
                    distance_span = sample.distance_miles - previous.distance_miles
                    fraction = (
                        (distance - previous.distance_miles) / distance_span
                        if distance_span
                        else 0.0
                    )
                    marker_time = previous.time_seconds + fraction * (
                        sample.time_seconds - previous.time_seconds
                    )
                    measured_mile_markers.append((marker_time, label))
                    break
        self.draw_graph(
            page,
            [(sample.time_seconds, sample.speed_mph) for sample in result.telemetry],
            "Speed (mph)",
            ACCENT,
            vertical_markers=measured_mile_markers,
        )
        self.section(page, "Acceleration / time")
        self.draw_graph(
            page,
            [(sample.time_seconds, sample.acceleration_g) for sample in result.telemetry],
            "Acceleration (G)",
            LIME,
            include_zero=True,
            secondary_values=[
                (sample.time_seconds, sample.engine_rpm)
                for sample in result.telemetry
            ],
            secondary_label="Engine RPM",
            secondary_color=ACCENT,
            vertical_markers=measured_mile_markers,
        )
        if self.last_run_is_sandbox:
            self.action_button(
                page,
                "RETURN TO TEST FACILITY",
                lambda: self.show_page("Test Facility"),
                True,
            )
        elif self.garage_return_required:
            self.action_button(
                page,
                "RETURN TO GARAGE",
                lambda: self.show_page("Garage"),
                True,
            )
        elif (
            self.last_run_outcome is not None
            and self.last_run_outcome.failed
            and not self.last_run_repaired
        ):
            self.action_button(
                page,
                "OPEN TEAM DEBRIEF",
                lambda: self.show_page("Team Debrief"),
                True,
            )
        else:
            self.action_button(
                page,
                "TRACKSIDE MAINTENANCE",
                lambda: self.show_page("Trackside Modifications"),
                True,
            )
            if not self.last_run_was_record_attempt:
                self.action_button(page, "RUN ANOTHER TEST", lambda: self.show_page("Test Runs"))

    def draw_graph(
        self,
        parent,
        values,
        label,
        color,
        include_zero=False,
        secondary_values=None,
        secondary_label="",
        secondary_color=ACCENT,
        vertical_markers=None,
    ):
        canvas = tk.Canvas(parent, bg=PANEL, height=220, highlightthickness=0)
        canvas.pack(fill="x", pady=(0, 6))
        secondary_values = secondary_values or []
        vertical_markers = vertical_markers or []

        def paint(_event=None):
            canvas.delete("all")
            width = max(canvas.winfo_width(), 500)
            height = max(canvas.winfo_height(), 200)
            left = 58
            right = width - (68 if secondary_values else 22)
            top, bottom = 20, height - 34
            xs = [point[0] for point in values]
            ys = [point[1] for point in values]
            xs.extend(point[0] for point in secondary_values)
            x_max = max(xs) if xs else 1.0
            low = min(0.0, min(ys)) if include_zero else 0.0
            high = max(ys) if ys else 1.0
            if include_zero:
                high = max(high, 0.05)
            else:
                high = max(high, 1.0)
            span = max(high - low, 1e-9)
            canvas.create_text(left, 8, text=label, fill=PAPER, anchor="w", font=(FONT, 9, "bold"))
            secondary_high = max(
                (point[1] for point in secondary_values), default=1.0
            )
            secondary_high = max(secondary_high, 1.0)
            if secondary_values:
                canvas.create_text(
                    right + 8,
                    8,
                    text=secondary_label,
                    fill=secondary_color,
                    anchor="w",
                    font=(FONT, 9, "bold"),
                )
            for index in range(5):
                fraction = index / 4
                y = top + fraction * (bottom - top)
                value = high - fraction * span
                canvas.create_line(left, y, right, y, fill=LINE)
                canvas.create_text(left - 8, y, text=f"{value:.0f}" if not include_zero else f"{value:.2f}", fill=MUTED, anchor="e", font=(FONT, 8))
                if secondary_values:
                    rpm_value = secondary_high * (1.0 - fraction)
                    canvas.create_text(
                        right + 8,
                        y,
                        text=f"{rpm_value:.0f}",
                        fill=secondary_color,
                        anchor="w",
                        font=(FONT, 8),
                    )
            if secondary_values:
                canvas.create_line(right, top, right, bottom, fill=secondary_color)
            canvas.create_line(left, bottom, right, bottom, fill=MUTED)
            for index, (marker_time, marker_label) in enumerate(vertical_markers):
                x = left + (marker_time / x_max if x_max else 0) * (right - left)
                canvas.create_line(x, top, x, bottom, fill=LIME, dash=(4, 3))
                canvas.create_text(
                    x + 4,
                    top + 3 + (index % 2) * 14,
                    text=marker_label,
                    fill=LIME,
                    anchor="nw",
                    font=(FONT, 8, "bold"),
                )
            canvas.create_text(left, height - 13, text="0 s", fill=MUTED, anchor="w", font=(FONT, 8))
            canvas.create_text(right, height - 13, text=f"{x_max:.0f} s", fill=MUTED, anchor="e", font=(FONT, 8))
            points = []
            for x_value, y_value in values:
                x = left + (x_value / x_max if x_max else 0) * (right - left)
                y = bottom - ((y_value - low) / span) * (bottom - top)
                points.extend((x, y))
            if len(points) >= 4:
                canvas.create_line(*points, fill=color, width=2, smooth=True)
            secondary_points = []
            for x_value, y_value in secondary_values:
                x = left + (x_value / x_max if x_max else 0) * (right - left)
                y = bottom - (y_value / secondary_high) * (bottom - top)
                secondary_points.extend((x, y))
            if len(secondary_points) >= 4:
                canvas.create_line(
                    *secondary_points,
                    fill=secondary_color,
                    width=2,
                    smooth=True,
                )

        canvas.bind("<Configure>", paint)
        canvas.after(50, paint)
        return canvas

    def render_team(self):
        page = self.scroll_area()
        team = self.campaign.team
        self.page_title(page, "People & facilities", "Team management", f"{self.campaign.available_engineers} of {team.engineers} engineers available  /  {self.campaign.allocated_engineers} assigned to projects  /  {team.mechanics} mechanics  /  workshop level {team.workshop_level}")
        self.section(page, "Staffing")
        self.action_button(page, "Hire engineer  /  GBP 8,000", lambda: self.team_action(hire_engineer, "Engineer hired"))
        self.action_button(page, "Hire mechanic  /  GBP 5,000", lambda: self.team_action(hire_mechanic, "Mechanic hired"))
        cost = calculate_workshop_upgrade_cost(team)
        self.section(page, "Facilities")
        self.action_button(page, f"Upgrade workshop to level {team.workshop_level + 1}  /  GBP {cost:,.0f}", lambda: self.team_action(upgrade_workshop, "Workshop upgraded"))
        self.section(page, "Sponsors")
        self._render_sponsor_objectives(page)
        active = set(self.campaign.sponsorship.active_sponsors)
        departed = set(self.campaign.sponsorship.departed_sponsors)
        for sponsor in SPONSOR_CATALOG:
            if sponsor.sponsor_id in active:
                continue
            if sponsor.sponsor_id in departed:
                tk.Label(page, text=f"WITHDRAWN  /  {sponsor.name}  /  will not return after a missed target", bg=INK, fg=ACCENT, font=(FONT, 9)).pack(anchor="w", pady=4)
                continue
            available = sponsor in available_sponsors(team.reputation, active, departed)
            if sponsor.objective_kind == RUNS_OBJECTIVE:
                demand = f"demands {sponsor.objective_value:.0f} successful runs"
            else:
                demand = f"demands {sponsor.objective_value:.0%} of the world record"
            detail = (
                f"{sponsor.name}  /  signing GBP {sponsor.signing_bonus_gbp:,.0f}  /  per turn GBP {sponsor.income_per_turn_gbp:,.0f}  /  "
                f"reliability +{sponsor.reliability_bonus:.0%}  /  {demand} every {SPONSOR_OBJECTIVE_DEADLINE_TURNS} turns"
            )
            if available:
                self.action_button(page, detail, lambda selected=sponsor: self.sign_sponsor_action(selected), True)
            else:
                tk.Label(page, text=f"LOCKED  /  {sponsor.name}  /  {sponsor.reputation_required:.1f} reputation required", bg=INK, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=4)
        self.section(page, "Campaign controls")
        self.action_button(page, "RESET CAMPAIGN", self.confirm_reset)

    def team_action(self, action, success):
        try:
            action(self.campaign)
            save_campaign(self.campaign)
            self.last_run_note = success
        except ValueError as exc:
            messagebox.showerror("Action unavailable", str(exc), parent=self)
        self.show_page("Team")

    def sign_sponsor_action(self, sponsor):
        try:
            objective = sign_sponsor(self.campaign, sponsor.sponsor_id)
            save_campaign(self.campaign)
            messagebox.showinfo(
                "Sponsor signed",
                f"{sponsor.name} is on board.\n\nFirst demand: {describe_sponsor_objective(self.campaign, objective)}.\n\nMiss the deadline and they withdraw for good.",
                parent=self,
            )
        except ValueError as exc:
            messagebox.showerror("Sponsor unavailable", str(exc), parent=self)
        self.show_page("Team")

    def _render_sponsor_objectives(self, parent):
        objectives = self.campaign.sponsorship.objectives
        if not objectives:
            tk.Label(parent, text="No sponsors signed.", bg=INK, fg=MUTED, font=(FONT, 10)).pack(anchor="w", pady=3)
            return
        for objective in objectives:
            urgent = objective.turns_remaining <= 1
            tk.Label(
                parent,
                text=f"{SPONSOR_BY_ID[objective.sponsor_id].name.upper()}  /  {describe_sponsor_objective(self.campaign, objective)}",
                bg=INK,
                fg=ACCENT if urgent else LIME,
                font=(FONT, 10, "bold"),
                wraplength=1050,
                justify="left",
            ).pack(anchor="w", pady=3)

    def confirm_reset(self):
        if messagebox.askyesno("Reset campaign", "This erases the active campaign save and diagnostics log and starts a new team. Continue?", parent=self):
            self.campaign = reset_campaign()
            clear_diagnostic_log()
            save_campaign(self.campaign)
            self.last_result = None
            self.last_vehicle = None
            self.last_track = None
            self.show_page("Dashboard")

    def render_records(self):
        page = self.scroll_area()
        self.page_title(page, "Archive", "Historical records", "Successful campaign runs are ranked by measured-mile speed.")
        records = [record for record in load_records() if record.get("campaign_id") == self.campaign.campaign_id]
        records.sort(key=lambda record: record.get("measured_mile_speed_mph", 0), reverse=True)
        if not records:
            tk.Label(page, text="No completed runs recorded for this campaign yet.", bg=INK, fg=MUTED, font=(FONT, 11)).pack(anchor="w")
            return
        for index, record in enumerate(records[:30], start=1):
            frame = tk.Frame(page, bg=PANEL, padx=16, pady=12)
            frame.pack(fill="x", pady=3)
            tk.Label(frame, text=f"{index:02d}  /  {record['measured_mile_speed_mph']:.1f} mph", bg=PANEL, fg=LIME if index == 1 else PAPER, font=(DISPLAY_FONT, 17, "bold")).pack(side="left")
            tk.Label(frame, text=f"{record['car_name']}  /  {record['track_name']}  /  Peak {record['peak_speed_mph']:.1f} mph", bg=PANEL, fg=MUTED, font=(FONT, 9)).pack(side="right")

    def render_challenges(self):
        page = self.scroll_area()
        self.page_title(page, "Historical programme", "Record challenges", "Recreate landmark record attempts. Challenge runs use the historical vehicle and venue and do not spend campaign funds.")
        for challenge in CHALLENGES:
            self.action_button(page, f"{challenge.name}  /  target {challenge.target_speed_mph:.1f} mph\n{challenge.description}", lambda selected=challenge: self.run_challenge(selected))

    def render_encyclopedia(self):
        page = self.scroll_area()
        self.page_title(page, "Reference library", "Historical encyclopedia", "Vehicle, engine, transmission, brake, and venue definitions from the current catalogues.")
        self.section(page, "Vehicles")
        for factory in AVAILABLE_CARS.values():
            vehicle = factory()
            tk.Label(page, text=f"{vehicle.name}  /  {vehicle.engine.name}  /  {vehicle.power:,.0f} hp  /  {vehicle.mass:,.0f} kg", bg=INK, fg=PAPER, font=(FONT, 10)).pack(anchor="w", pady=3)
        self.section(page, "Engines")
        for engine in AVAILABLE_ENGINES.values():
            tk.Label(page, text=f"{engine.name}  /  {engine.era}  /  {engine.power_hp:,.0f} hp  /  {engine.torque_nm:,.0f} Nm", bg=INK, fg=PAPER, font=(FONT, 10)).pack(anchor="w", pady=3)
        self.section(page, "Transmissions & brakes")
        for gearbox in PREBUILT_GEARBOXES + TRANSMISSION_CATALOG:
            tk.Label(page, text=f"{gearbox.name}  /  {gearbox.gear_count} gear(s)  /  {gearbox.efficiency:.0%} efficiency", bg=INK, fg=PAPER, font=(FONT, 10)).pack(anchor="w", pady=3)
        for brakes in BRAKE_CATALOG:
            tk.Label(page, text=f"{brakes.name}  /  {brakes.max_braking_g:.2f} g  /  {brakes.efficiency:.0%} efficiency", bg=INK, fg=PAPER, font=(FONT, 10)).pack(anchor="w", pady=3)
        self.section(page, "Tracks")
        for track in AVAILABLE_TRACKS.values():
            tk.Label(page, text=f"{track.name}  /  {track.length_miles:g} mi  /  introduced {track.introduced_year}", bg=INK, fg=PAPER, font=(FONT, 10)).pack(anchor="w", pady=3)

    def run_challenge(self, challenge):
        vehicle, result = simulate_challenge(challenge)
        self.last_report = create_engineering_report(
            vehicle, challenge.track, result, previous_report=self.last_report
        )
        self.last_run_is_sandbox = True
        self.last_result = result
        self.last_vehicle = vehicle
        self.last_vehicle_entry = None
        self.last_track = challenge.track
        self.last_record_message = None
        if result.measured_mile_speed_mph >= challenge.target_speed_mph:
            self.last_run_note = f"Challenge complete. Target {challenge.target_speed_mph:.1f} mph beaten."
        else:
            self.last_run_note = f"Challenge result: {challenge.target_speed_mph - result.measured_mile_speed_mph:.1f} mph short of the historical target."
        self.show_page("Telemetry")


def launch():
    app = BonnevilleApp()
    app.mainloop()