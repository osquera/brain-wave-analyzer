@echo off
:: Run pytest with coverage and generate a report
python -m pytest tests -v --cov=src --cov-report=term --cov-report=html
