# Well Report Analytics Tool

An automated analytics application for processing drilling and completion reports (DDR/DCR) and generating real-time operational insights.



## Overview

This tool ingests daily drilling and completion reports in PDF format and transforms them into structured datasets for analysis.

It enables engineers and decision-makers to track:

- Non-Productive Time (NPT)
- Cost performance
- Drilling efficiency
- Completion phase progression
- Operational trends across wells



## Key Features

- Automated PDF parsing using pdfplumber  
- Real-time dashboard powered by Streamlit  
- NPT detection and classification using whitelist logic  
- Cost tracking and AFE analysis  
- Drilling performance metrics (ROP, efficiency, cost/meter)  
- Completion phase detection using rule-based sequencing  
- Multi-well comparison and benchmarking  



## Application Interface

The application provides:

- Interactive dashboards  
- KPI summaries  
- Trend visualizations  
- NPT analysis tables  
- Phase-based completion insights  



## Running the Application

### Option 1 - Run Locally

pip install -r requirements.txt
streamlit run my_app.py

### Option 2 - Run Executable (Windows)
This project includes a packaged executable built with PyInstaller.

my_run_app.py + my_app.spec

Used to generate a standalone .exe version of the tool.


## Project Structure

my_app.py            → Streamlit dashboard interface  
my_pipeline.py       → Core data processing logic  
my_run_app.py        → Entry point for executable build  
my_app.spec          → PyInstaller configuration


## Disclaimer

This tool is developed for internal engineering analytics and operational efficiency.

No confidential data is included in this repository. Users are responsible for ensuring compliance with company data governance policies when using this tool with operational data.

## License
This project is licensed under the MIT License

## Dashboard Preview
<img width="1915" height="865" alt="image" src="https://github.com/user-attachments/assets/cf4e053c-e33e-4297-9847-347941a14486" />

