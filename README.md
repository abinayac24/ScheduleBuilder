# ScheduleBuilder

📘 ScheduleBuilder — Automated Timetable Generator
Overview

ScheduleBuilder is a Python + Streamlit–based application that automatically generates class timetables for educational departments.
It supports multi-class scheduling, teacher-wise allocation, Excel uploads, and downloadable timetables.

**Features**

Add teachers, classes, and subject assignments

Import data directly from Excel (.xlsx)

Generate conflict-free timetables automatically

Handles Theory, Lab, Mentoring, Library periods

Multi-class output + Teacher-wise output

Download generated timetables as CSV

Clean and interactive UI using Streamlit

**Tech Stack**

Python 3.x

Streamlit – UI framework

Pandas – Data processing

Dataclasses – Structured data models

JSON – Import/Export for state

OpenPyXL – Excel file support

 **Installation**
Install required libraries:
pip install streamlit pandas openpyxl numpy

▶️ Run the Project
streamlit run website.py

 **Project Structure**
ScheduleBuilder/
│── website.py
│── requirements.txt
│── procedure to run.txt
│── README.md

**Output Preview**

Timetables for:

Each Class

Each Teacher

Download files in CSV



