"""Project Bonneville web adapter."""

from flask import Flask, redirect, render_template, request, url_for

from application import CampaignApplication

app = Flask(__name__)
campaign_app = CampaignApplication()

@app.get("/health")
def health():
    return "Project Bonneville: OK"


@app.get("/")
def dashboard():
    return render_template(
        "dashboard.html",
        campaign=campaign_app.summary(),
    )


@app.get("/new")
def new_campaign_confirmation():
    return render_template(
        "new_campaign.html",
        campaign=campaign_app.summary(),
    )

@app.post("/new")
def new_campaign():
    campaign_app.new_campaign()
    campaign_app.save()
    return redirect(url_for("dashboard"))

@app.post("/turn")
def end_turn():
    campaign_app.advance_turn()
    return redirect(url_for("dashboard"))

@app.get("/research")
def research():
    return render_template(
        "research.html",
        research=campaign_app.research_summary(),
    )

@app.post("/research/program")
def select_research_program():
    campaign_app.select_development_program(
        request.form["program_id"]
    )
    return redirect(url_for("research"))