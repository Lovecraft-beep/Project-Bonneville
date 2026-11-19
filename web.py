"""Project Bonneville web adapter."""

from flask import Flask, redirect, render_template, url_for

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

@app.post("/turn")
def end_turn():
    campaign_app.advance_turn()
    return redirect(url_for("dashboard"))