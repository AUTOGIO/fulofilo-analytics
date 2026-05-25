PROJECT_ROOT := /Users/eduardofgiovannini/Documents/GitHub/fulofilo-analytics
PYTHON := $(PROJECT_ROOT)/.venv/bin/python3
AUTOMATION := $(PYTHON) $(PROJECT_ROOT)/scripts/automation_cli.py

.PHONY: automation-refresh-dashboard-data automation-sync-excel-master automation-generate-replenishment-alerts automation-export-reports automation-validate-data-integrity automation-webhook

automation-refresh-dashboard-data:
	$(AUTOMATION) refresh-dashboard-data

automation-sync-excel-master:
	$(AUTOMATION) sync-excel-master

automation-generate-replenishment-alerts:
	$(AUTOMATION) generate-replenishment-alerts

automation-export-reports:
	$(AUTOMATION) export-reports

automation-validate-data-integrity:
	$(AUTOMATION) validate-data-integrity

automation-run-daily:
	$(AUTOMATION) run-daily-automation

automation-webhook:
	$(AUTOMATION) serve-webhook --host 0.0.0.0 --port 8787
