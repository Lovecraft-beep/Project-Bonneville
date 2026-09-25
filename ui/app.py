"""Button-driven desktop interface for Project Bonneville."""

from copy import deepcopy
from dataclasses import replace
import tkinter as tk
from tkinter import messagebox

from brakes import BRAKE_CATALOG, available_brakes
from cars import AVAILABLE_CARS
from chassis import available_chassis
from diagnostics import append_run_log
from engines import AVAILABLE_ENGINES, ENGINE_TUNE_STAGES, available_engines
from gearbox import (
    DIRECT_DRIVE,
    PREBUILT_GEARBOXES,
    TRANSMISSION_CATALOG,
    optimize_gearbox_for_engine,
    recommended_transmission,
)
from historical_challenges import CHALLENGES
from historical_records import next_historical_target
from management import (
    advance_turn,
    build_vehicle,
    calculate_run_cost,
    calculate_workshop_upgrade_cost,
    complete_failed_run,
    complete_run,
    hire_engineer,
    hire_mechanic,
    load_campaign,
    research_aerodynamics_technology,
    research_brake_technology,
    research_chassis_technology,
    research_engine_technology,
    research_gearbox_technology,
    research_tyre_technology,
    reset_campaign,
    save_campaign,
    sign_sponsor,
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
    aerodynamics_effects,
)
from simulation import run_simulation
from sponsors import SPONSOR_CATALOG, available_sponsors
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
        self.last_track = None
        self.last_run_note = "No test run recorded this session."

        self.sidebar = tk.Frame(self, bg=INK, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self.main = tk.Frame(self, bg=INK)
        self.main.pack(side="left", fill="both", expand=True)
        self._build_sidebar()
        self._build_header()
        self.body = tk.Frame(self.main, bg=INK)
        self.body.pack(fill="both", expand=True, padx=24, pady=(16, 22))
        self.show_page("Dashboard")

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
        for name in ("Dashboard", "Research", "Garage", "Test Runs", "Test Facility", "Telemetry", "Team", "Records", "Challenges", "Encyclopedia"):
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
            pady=12,
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
        self.header_status = tk.Label(
            bar, text="", bg=INK, fg=LIME, font=(FONT, 10, "bold")
        )
        self.header_status.pack(side="right", anchor="center")

    def _refresh_header(self):
        self.header_status.configure(
            text=f"{self.campaign.current_year}  /  TURN {self.campaign.turn_number}     GBP {self.campaign.team.cash:,.0f}"
        )

    def show_page(self, name):
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
            "Test Facility": self.render_test_facility,
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
        values = (
            ("Available funds", f"GBP {self.campaign.team.cash:,.0f}", f"{self.campaign.team.reputation:.1f} reputation"),
            ("Best measured mile", f"{self.campaign.best_measured_mile_speed_mph:.1f} mph", "Campaign record"),
            ("Engineering team", str(self.campaign.team.engineers), f"{self.campaign.team.mechanics} mechanics"),
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
        self.section(right, "Campaign objective")
        if target:
            gap = max(0.0, target.speed_mph - self.campaign.best_measured_mile_speed_mph)
            tk.Label(right, text=f"{target.year}  /  {target.vehicle}", bg=INK, fg=PAPER, font=(DISPLAY_FONT, 17, "bold"), wraplength=470, justify="left").pack(anchor="w")
            tk.Label(right, text=f"{target.speed_mph:.1f} mph target  |  {gap:.1f} mph to go\n{target.milestone}", bg=INK, fg=MUTED, font=(FONT, 10), justify="left").pack(anchor="w", pady=8)
            self.action_button(right, "Attempt historical record", self.start_record_attempt, True)
        else:
            tk.Label(right, text="All campaign records achieved.", bg=INK, fg=LIME, font=(FONT, 13, "bold")).pack(anchor="w")
        self.section(page, "Latest headlines")
        for headline in self.campaign.world.headlines[-3:]:
            tk.Label(page, text=f"-  {headline}", bg=INK, fg=PAPER, font=(FONT, 10), wraplength=1050, justify="left").pack(anchor="w", pady=3)
        if self.campaign.world.reactions:
            tk.Label(page, text=self.campaign.world.reactions[-1], bg=INK, fg=LIME, font=(FONT, 10, "italic"), wraplength=1050, justify="left").pack(anchor="w", pady=(10, 0))

    def render_research(self):
        page = self.scroll_area()
        self.page_title(page, "Research & development", "Technology tree", "Select a branch, then fund any available project. Costs, staffing requirements, prerequisites, and turn advancement use the campaign rules.")
        tabs = tk.Frame(page, bg=INK)
        tabs.pack(fill="x", pady=(0, 10))
        for branch in ("Engine", "Chassis", "Aerodynamics", "Gearbox", "Tyres", "Brakes"):
            tk.Button(
                tabs, text=branch.upper(), command=lambda value=branch: self.set_research_branch(value),
                bg=PANEL_LIGHT if self.research_branch == branch else PANEL,
                fg=LIME if self.research_branch == branch else PAPER,
                activebackground=ACCENT, activeforeground=INK, relief="flat", borderwidth=0,
                font=(FONT, 9, "bold"), padx=13, pady=10, cursor="hand2",
            ).pack(side="left", padx=(0, 5))
        self._render_research_nodes(page)

    def set_research_branch(self, branch):
        self.research_branch = branch
        self.show_page("Research")

    def _research_data(self):
        branches = {
            "Engine": (ENGINE_TECHNOLOGY_TREE, self.campaign.research.engine_technology, self.campaign.research.chassis_technology, research_engine_technology),
            "Chassis": (CHASSIS_TECHNOLOGY_TREE, self.campaign.research.chassis_technology, self.campaign.research.aerodynamics_technology, research_chassis_technology),
            "Aerodynamics": (AERODYNAMICS_TECHNOLOGY_TREE, self.campaign.research.aerodynamics_technology, self.campaign.research.chassis_technology, research_aerodynamics_technology),
            "Gearbox": (GEARBOX_TECHNOLOGY_TREE, self.campaign.research.gearbox_technology, self.campaign.research.chassis_technology, research_gearbox_technology),
            "Tyres": (TYRE_TECHNOLOGY_TREE, self.campaign.research.tyre_technology, self.campaign.research.chassis_technology, research_tyre_technology),
            "Brakes": (BRAKE_TECHNOLOGY_TREE, self.campaign.research.brake_technology, self.campaign.research.chassis_technology, research_brake_technology),
        }
        return branches[self.research_branch]

    def _render_research_nodes(self, parent):
        tree, researched, shared_researched, action = self._research_data()
        researched_set = set(researched)
        combined = researched_set | set(shared_researched)
        ready = [node for node in tree if node.technology_id not in researched_set and set(node.prerequisites).issubset(combined)]
        for node in tree:
            is_done = node.technology_id in researched_set
            is_ready = node in ready
            status = "COMPLETE" if is_done else "AVAILABLE" if is_ready else "LOCKED"
            card = tk.Frame(parent, bg=PANEL, padx=16, pady=13)
            card.pack(fill="x", pady=4)
            row = tk.Frame(card, bg=PANEL)
            row.pack(fill="x")
            info = tk.Frame(row, bg=PANEL)
            info.pack(side="left", fill="both", expand=True)
            tk.Label(info, text=f"{node.era.upper()}  /  {status}", bg=PANEL, fg=LIME if is_done else ACCENT if is_ready else MUTED, font=(FONT, 8, "bold")).pack(anchor="w")
            tk.Label(info, text=node.name, bg=PANEL, fg=PAPER, font=(DISPLAY_FONT, 16, "bold")).pack(anchor="w", pady=(4, 2))
            tk.Label(info, text=f"GBP {node.cost_gbp:,.0f}    /    {node.engineers_required} engineer(s)\n{node.description or 'Prerequisites: ' + (', '.join(node.prerequisites) or 'None')}", bg=PANEL, fg=MUTED, font=(FONT, 9), wraplength=690, justify="left").pack(anchor="w")
            if is_ready:
                tk.Button(row, text="RESEARCH", command=lambda tech=node, fn=action: self.research(tech, fn), bg=ACCENT, fg=INK, activebackground=LIME, relief="flat", borderwidth=0, font=(FONT, 9, "bold"), padx=14, pady=10, cursor="hand2").pack(side="right", padx=(12, 0))
            elif not is_done:
                tk.Label(row, text="LOCKED", bg=PANEL, fg=MUTED, font=(FONT, 9, "bold")).pack(side="right", padx=12)

    def research(self, technology, action):
        try:
            action(self.campaign, technology.technology_id)
            advance_turn(self.campaign)
            save_campaign(self.campaign)
        except ValueError as exc:
            messagebox.showerror("Research unavailable", str(exc), parent=self)
        self.show_page("Research")

    def render_garage(self):
        page = self.scroll_area()
        self.page_title(page, "Vehicle department", "Garage", "Built vehicles retain their installed components between tests. Select a vehicle to inspect, tune, or replace components.")
        self.action_button(page, "+  DESIGN NEW VEHICLE", self.start_vehicle_builder, True)
        if not self.campaign.garage.vehicles:
            self.section(page, "Empty garage")
            tk.Label(page, text="Build your first car to unlock campaign test runs.", bg=INK, fg=MUTED, font=(FONT, 11)).pack(anchor="w")
            return
        self.section(page, f"{len(self.campaign.garage.vehicles)} vehicles")
        for entry in self.campaign.garage.vehicles:
            vehicle = build_vehicle_from_garage_entry(entry)
            frame = tk.Frame(page, bg=PANEL, padx=16, pady=14)
            frame.pack(fill="x", pady=4)
            tk.Label(frame, text=vehicle.name, bg=PANEL, fg=PAPER, font=(DISPLAY_FONT, 17, "bold")).pack(anchor="w")
            tk.Label(frame, text=f"{vehicle.engine.name}  /  {vehicle.engine.power_hp:,.0f} hp     {vehicle.gearbox.name}     {vehicle.mass:,.0f} kg", bg=PANEL, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=(4, 10))
            self.action_button(frame, "OPEN VEHICLE", lambda item=entry: self.open_garage_vehicle(item))

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
        self.section(page, "Workshop controls")
        self.action_button(page, "TEST THIS VEHICLE", lambda: self.choose_track_for_vehicle(entry), True)
        self.action_button(page, "Replace engine", lambda: self.choose_component(entry, "engine"))
        self.action_button(page, "Replace gearbox", lambda: self.choose_component(entry, "gearbox"))
        self.action_button(page, "Replace brakes", lambda: self.choose_component(entry, "brakes"))
        if entry.engine_name in AVAILABLE_ENGINES:
            stages = ENGINE_TUNE_STAGES
            current = min(entry.engine_tune_stage, len(stages) - 1)
            next_stage = (current + 1) % len(stages)
            self.action_button(page, f"Tune engine: advance to stage {next_stage}", lambda: self.set_engine_tune(entry, next_stage))
        self.action_button(page, "Tune gearbox ratios", lambda: self.tune_vehicle_gearbox(entry))
        if self.campaign.research.has_gearbox_technology("computer_optimised_gear_ratios"):
            self.action_button(page, "Optimise gear ratios", lambda: self.optimise_vehicle(entry))
        if set(self.campaign.research.aerodynamics_technology) - set(entry.aerodynamics_technology):
            self.action_button(page, "Fit latest aerodynamics package", lambda: self.fit_aero(entry))
        self.action_button(page, "BACK TO GARAGE", lambda: self.show_page("Garage"))

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
        if gear_index is None:
            ratio = round(vehicle.gearbox.final_drive_ratio + delta, 3)
            if not 0.5 <= ratio <= 6.0:
                return
            entry.gearbox_final_drive = ratio
        else:
            ratios = list(vehicle.gearbox.gears)
            ratio = round(ratios[gear_index] + delta, 3)
            if not 0.5 <= ratio <= 5.0:
                return
            ratios[gear_index] = ratio
            entry.gearbox_ratios = tuple(ratios)
        save_campaign(self.campaign)
        self.tune_vehicle_gearbox(entry)

    def start_vehicle_builder(self):
        self.builder = {"step": "chassis"}
        self.render_builder()

    def render_builder(self):
        self.page = "Garage"
        self._refresh_header()
        for child in self.body.winfo_children():
            child.destroy()
        page = self.scroll_area()
        steps = ("chassis", "engine", "gearbox", "brakes")
        step = self.builder.get("step", "chassis")
        labels = {"chassis": "Select a chassis", "engine": "Select an engine", "gearbox": "Select a gearbox", "brakes": "Select a brake system"}
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
        else:
            for item in available_brakes(self.campaign.current_year):
                self.action_button(page, f"{item.name}  /  {item.max_braking_g:.2f} g  /  GBP {item.cost_gbp:,.0f}", lambda value=item: self.builder_select("brakes", value))
        self.action_button(page, "CANCEL DESIGN", lambda: self.show_page("Garage"))

    def builder_select(self, key, value):
        self.builder[key] = value
        order = ("chassis", "engine", "gearbox", "brakes")
        current_index = order.index(key)
        if current_index < len(order) - 1:
            self.builder["step"] = order[current_index + 1]
            self.render_builder()
            return
        self.finish_vehicle_build()

    def finish_vehicle_build(self):
        chassis = self.builder["chassis"]
        engine = self.builder["engine"]
        gearbox = deepcopy(self.builder["gearbox"])
        brakes = replace(self.builder["brakes"])
        aero = tuple(self.campaign.research.aerodynamics_technology)
        effect = aerodynamics_effects(aero)
        name = f"Bonneville Special {len(self.campaign.garage.vehicles) + 1:02d}"
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
            advance_turn(self.campaign)
            save_campaign(self.campaign)
        except ValueError as exc:
            messagebox.showerror("Unable to build vehicle", str(exc), parent=self)
        self.show_page("Garage")

    def render_test_runs(self):
        page = self.scroll_area()
        self.page_title(page, "Track operations", "Prepare a test run", "Select a garage vehicle, then an available circuit. The simulation, costs, reliability checks, records, and campaign turn are unchanged.")
        self.section(page, "Garage vehicles")
        if not self.campaign.garage.vehicles:
            tk.Label(page, text="No campaign vehicles are available. Build one in the Garage first.", bg=INK, fg=MUTED, font=(FONT, 11)).pack(anchor="w")
            return
        for entry in self.campaign.garage.vehicles:
            self.action_button(page, f"{entry.vehicle_name}  /  {entry.engine_name}  /  {entry.gearbox_name}", lambda selected=entry: self.choose_track_for_vehicle(selected))
        target = next_historical_target(self.campaign.current_year, self.campaign.completed_historical_record_ids)
        if target:
            self.section(page, "Historical record attempt")
            self.action_button(page, f"Attempt {target.year} {target.vehicle}  /  {target.speed_mph:.1f} mph", self.start_record_attempt, True)

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
        self.last_result = result
        self.last_vehicle = vehicle
        self.last_track = track
        self.last_run_note = "Engineering facility / sandbox result. The campaign was not changed."
        self.show_page("Telemetry")

    def choose_track_for_vehicle(self, entry, record_attempt=False):
        self.selected_vehicle = entry
        self._render_track_choices(record_attempt)

    def _render_track_choices(self, record_attempt=False):
        for child in self.body.winfo_children():
            child.destroy()
        page = self.scroll_area()
        entry = self.selected_vehicle
        self.page_title(page, "Track operations", "Select a venue", f"Vehicle: {entry.vehicle_name}. Available tracks follow the campaign year.")
        for track in available_tracks(self.campaign.current_year).values():
            vehicle = build_vehicle_from_garage_entry(entry)
            cost = calculate_run_cost(vehicle, track)
            self.action_button(page, f"{track.name}  /  {track.length_miles:g} mi  /  friction {track.friction_factor:.2f}  /  estimated GBP {cost:,.0f}", lambda venue=track: self.execute_run(entry, venue, record_attempt))
        self.action_button(page, "BACK", lambda: self.show_page("Test Runs"))

    def start_record_attempt(self):
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
        self._render_track_choices(record_attempt=True)

    def execute_run(self, entry, track, record_attempt=False):
        vehicle = build_vehicle_from_garage_entry(entry)
        cost = calculate_run_cost(vehicle, track)
        if cost > self.campaign.team.cash:
            messagebox.showerror("Insufficient funds", f"This run costs GBP {cost:,.0f}; the campaign has GBP {self.campaign.team.cash:,.0f}.", parent=self)
            return
        if not messagebox.askyesno("Confirm test run", f"{vehicle.name} at {track.name}\nEstimated cost: GBP {cost:,.0f}\nProceed with simulation?", parent=self):
            return
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
        record_target = (
            next_historical_target(
                self.campaign.current_year,
                self.campaign.completed_historical_record_ids,
            )
            if record_attempt
            else None
        )
        if outcome.failed:
            complete_failed_run(self.campaign, cost)
            self.last_run_note = f"ABORTED: {outcome.failure_type.name}. Failure probability {outcome.failure_probability:.1%}."
        else:
            complete_run(self.campaign, cost, result.measured_mile_speed_mph, is_record_attempt=record_attempt)
            self.last_run_note = f"Completed. Measured mile {result.measured_mile_speed_mph:.1f} mph; peak {result.peak_speed_mph:.1f} mph."
            if record_target and result.measured_mile_speed_mph >= record_target.speed_mph:
                self.last_run_note += f" Historical target beaten: {record_target.vehicle}."
            save_record(create_record(vehicle, track, result, self.campaign))
        advance_turn(self.campaign, days=7)
        save_campaign(self.campaign)
        self.last_result = result
        self.last_vehicle = vehicle
        self.last_track = track
        self.show_page("Telemetry")

    def render_telemetry(self):
        page = self.scroll_area()
        if self.last_result is None:
            self.page_title(page, "Run telemetry", "Telemetry", "Speed and acceleration traces appear here after a test run.")
            self.action_button(page, "PREPARE A TEST RUN", lambda: self.show_page("Test Runs"), True)
            return
        result = self.last_result
        self.page_title(page, f"{self.last_vehicle.name}  /  {self.last_track.name}", "Run telemetry", self.last_run_note)
        metrics = tk.Frame(page, bg=INK)
        metrics.pack(fill="x", pady=(0, 10))
        for label, value, sub in (("Measured mile", f"{result.measured_mile_speed_mph:.1f} mph", f"{result.measured_mile_time_seconds:.1f} s"), ("Peak speed", f"{result.peak_speed_mph:.1f} mph", f"{result.total_time_seconds:.1f} s total"), ("Average acceleration", f"{result.average_acceleration_g:.3f} G", f"{result.gear_change_count} gear changes"), ("Brake temperature", f"{result.maximum_brake_temperature_c:.0f} C", f"{result.wheelspin_event_count} wheelspin events")):
            self.card(metrics, label, value, sub).pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.section(page, "Speed / time")
        self.draw_graph(page, [(sample.time_seconds, sample.speed_mph) for sample in result.telemetry], "Speed (mph)", ACCENT)
        self.section(page, "Acceleration / time")
        self.draw_graph(page, [(sample.time_seconds, sample.acceleration_g) for sample in result.telemetry], "Acceleration (G)", LIME, include_zero=True)
        self.action_button(page, "RUN ANOTHER TEST", lambda: self.show_page("Test Runs"), True)

    def draw_graph(self, parent, values, label, color, include_zero=False):
        canvas = tk.Canvas(parent, bg=PANEL, height=220, highlightthickness=0)
        canvas.pack(fill="x", pady=(0, 6))

        def paint(_event=None):
            canvas.delete("all")
            width = max(canvas.winfo_width(), 500)
            height = max(canvas.winfo_height(), 200)
            left, right, top, bottom = 58, width - 22, 20, height - 34
            xs = [point[0] for point in values]
            ys = [point[1] for point in values]
            x_max = max(xs) if xs else 1.0
            low = min(0.0, min(ys)) if include_zero else 0.0
            high = max(ys) if ys else 1.0
            if include_zero:
                high = max(high, 0.05)
            else:
                high = max(high, 1.0)
            span = max(high - low, 1.0)
            canvas.create_text(left, 8, text=label, fill=PAPER, anchor="w", font=(FONT, 9, "bold"))
            for index in range(5):
                fraction = index / 4
                y = top + fraction * (bottom - top)
                value = high - fraction * span
                canvas.create_line(left, y, right, y, fill=LINE)
                canvas.create_text(left - 8, y, text=f"{value:.0f}" if not include_zero else f"{value:.1f}", fill=MUTED, anchor="e", font=(FONT, 8))
            canvas.create_line(left, bottom, right, bottom, fill=MUTED)
            canvas.create_text(left, height - 13, text="0 s", fill=MUTED, anchor="w", font=(FONT, 8))
            canvas.create_text(right, height - 13, text=f"{x_max:.0f} s", fill=MUTED, anchor="e", font=(FONT, 8))
            points = []
            for x_value, y_value in values:
                x = left + (x_value / x_max if x_max else 0) * (right - left)
                y = bottom - ((y_value - low) / span) * (bottom - top)
                points.extend((x, y))
            if len(points) >= 4:
                canvas.create_line(*points, fill=color, width=2, smooth=True)

        canvas.bind("<Configure>", paint)
        canvas.after(50, paint)

    def render_team(self):
        page = self.scroll_area()
        team = self.campaign.team
        self.page_title(page, "People & facilities", "Team management", f"{team.engineers} engineers  /  {team.mechanics} mechanics  /  workshop level {team.workshop_level}")
        self.section(page, "Staffing")
        self.action_button(page, "Hire engineer  /  GBP 8,000  /  advances one turn", lambda: self.team_action(hire_engineer, "Engineer hired"))
        self.action_button(page, "Hire mechanic  /  GBP 5,000  /  advances one turn", lambda: self.team_action(hire_mechanic, "Mechanic hired"))
        cost = calculate_workshop_upgrade_cost(team)
        self.section(page, "Facilities")
        self.action_button(page, f"Upgrade workshop to level {team.workshop_level + 1}  /  GBP {cost:,.0f}", lambda: self.team_action(upgrade_workshop, "Workshop upgraded"))
        self.section(page, "Sponsors")
        active = set(self.campaign.sponsorship.active_sponsors)
        for sponsor in SPONSOR_CATALOG:
            if sponsor.sponsor_id in active:
                continue
            available = sponsor in available_sponsors(team.reputation, self.campaign.sponsorship.active_sponsors)
            detail = f"{sponsor.name}  /  signing GBP {sponsor.signing_bonus_gbp:,.0f}  /  per turn GBP {sponsor.income_per_turn_gbp:,.0f}  /  reliability +{sponsor.reliability_bonus:.0%}"
            if available:
                self.action_button(page, detail, lambda selected=sponsor: self.sign_sponsor_action(selected), True)
            else:
                tk.Label(page, text=f"LOCKED  /  {sponsor.name}  /  {sponsor.reputation_required:.1f} reputation required", bg=INK, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=4)
        self.section(page, "Campaign controls")
        self.action_button(page, "RESET CAMPAIGN", self.confirm_reset)

    def team_action(self, action, success):
        try:
            action(self.campaign)
            advance_turn(self.campaign)
            save_campaign(self.campaign)
            self.last_run_note = success
        except ValueError as exc:
            messagebox.showerror("Action unavailable", str(exc), parent=self)
        self.show_page("Team")

    def sign_sponsor_action(self, sponsor):
        try:
            sign_sponsor(self.campaign, sponsor.sponsor_id)
            advance_turn(self.campaign)
            save_campaign(self.campaign)
        except ValueError as exc:
            messagebox.showerror("Sponsor unavailable", str(exc), parent=self)
        self.show_page("Team")

    def confirm_reset(self):
        if messagebox.askyesno("Reset campaign", "This erases the active campaign save and starts a new team. Continue?", parent=self):
            self.campaign = reset_campaign()
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
        vehicle = challenge.create_vehicle()
        result = run_simulation(
            vehicle,
            track_miles=challenge.track.length_miles,
            measured_mile_start=challenge.track.measured_mile_start,
            track_friction_factor=challenge.track.friction_factor,
            air_density_kg_m3=challenge.track.air_density_kg_m3,
        )
        self.last_result = result
        self.last_vehicle = vehicle
        self.last_track = challenge.track
        if result.measured_mile_speed_mph >= challenge.target_speed_mph:
            self.last_run_note = f"Challenge complete. Target {challenge.target_speed_mph:.1f} mph beaten."
        else:
            self.last_run_note = f"Challenge result: {challenge.target_speed_mph - result.measured_mile_speed_mph:.1f} mph short of the historical target."
        self.show_page("Telemetry")


def launch():
    app = BonnevilleApp()
    app.mainloop()