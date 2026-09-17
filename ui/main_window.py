from PySide6.QtWidgets import (
    QApplication,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from management import load_campaign


class ProjectBonnevilleWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Project Bonneville")
        self.resize(520, 520)

        self.campaign = load_campaign()

        self.team_group = QGroupBox("Team")
        self.team_form = QFormLayout()
        self.team_form.addRow("Name:", QLabel(self.campaign.team.name))
        self.team_form.addRow("Turn:", QLabel(f"{self.campaign.turn_number} | {self.campaign.current_year}"))
        self.team_form.addRow("Cash:", QLabel(f"GBP {self.campaign.team.cash:,.0f}"))
        self.team_form.addRow("Reputation:", QLabel(f"{self.campaign.team.reputation:.1f}"))
        self.team_form.addRow("Engineers:", QLabel(str(self.campaign.team.engineers)))
        self.team_form.addRow("Mechanics:", QLabel(str(self.campaign.team.mechanics)))
        self.team_form.addRow("Workshop:", QLabel(str(self.campaign.team.workshop_level)))
        self.team_group.setLayout(self.team_form)

        self.rnd_group = QGroupBox("Research & Development")
        self.rnd_layout = QFormLayout()
        self.rnd_layout.addRow(
            "Engine tech level:",
            QLabel(str(self.campaign.research.engine_technology_level)),
        )
        self.rnd_layout.addRow(
            "Best measured mile:",
            QLabel(f"{self.campaign.best_measured_mile_speed_mph:.1f} mph"),
        )
        self.rnd_group.setLayout(self.rnd_layout)

        self.stats_label = QLabel(
            f"Completed runs: {self.campaign.completed_runs}\n"
            f"Failed runs: {self.campaign.failed_runs}"
        )

        self.run_button = QPushButton("Run a test")
        self.run_button.clicked.connect(self.on_run_clicked)

        self.research_button = QPushButton("Research")
        self.research_button.clicked.connect(self.on_research_clicked)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.team_group)
        layout.addWidget(self.rnd_group)
        layout.addWidget(self.stats_label)
        layout.addWidget(self.run_button)
        layout.addWidget(self.research_button)
        self.setCentralWidget(container)

    def on_run_clicked(self):
        QMessageBox.information(
            self,
            "Test run",
            "This dashboard is the management shell. The actual run flow still lives in the CLI simulation.",
        )

    def on_research_clicked(self):
        QMessageBox.information(
            self,
            "Research",
            "Engine technology tree management is next, but the core engine tree is already in the campaign state.",
        )


def main():
    app = QApplication([])
    window = ProjectBonnevilleWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
