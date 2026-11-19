"""Project Bonneville web adapter."""

from flask import Flask, render_template

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