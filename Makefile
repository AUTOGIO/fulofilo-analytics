PROJECT_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PYTHON := $(PROJECT_ROOT)/.venv/bin/python3
AUTOMATION := $(PYTHON) $(PROJECT_ROOT)/scripts/automation_cli.py

.PHONY: setup-automations automation-refresh-dashboard-data automation-sync-excel-master automation-generate-replenishment-alerts automation-generate-forecasts automation-generate-po-drafts automation-generate-daily-briefing automation-export-reports automation-validate-data-integrity automation-webhook automation-run-daily

setup-automations:
	bash $(PROJECT_ROOT)/scripts/setup_automations.sh

automation-refresh-dashboard-data:
	$(AUTOMATION) refresh-dashboard-data

automation-sync-excel-master:
	$(AUTOMATION) sync-excel-master

automation-generate-replenishment-alerts:
	$(AUTOMATION) generate-replenishment-alerts

automation-generate-forecasts:
	$(AUTOMATION) generate-forecasts

automation-generate-po-drafts:
	$(AUTOMATION) generate-po-drafts

automation-generate-daily-briefing:
	$(AUTOMATION) generate-daily-briefing

automation-export-reports:
	$(AUTOMATION) export-reports

automation-reconcile-loyverse-sales:
	$(AUTOMATION) reconcile-loyverse-sales

automation-validate-data-integrity:
	$(AUTOMATION) validate-data-integrity

automation-run-daily:
	$(AUTOMATION) run-daily-automation

automation-webhook:
	$(AUTOMATION) serve-webhook --host 0.0.0.0 --port 8787
