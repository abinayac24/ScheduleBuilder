# ScheduleBuilder
📘 Smart Timetable Generator — Automated Class & Faculty Scheduler

A fast and efficient timetable generation system built using Python and Streamlit.
This tool automatically schedules class periods for multiple teachers and classes while ensuring no conflicts, continuous lab periods, and balanced allocation across the week.

🚀 Project Overview

This project provides an intuitive web interface for generating academic timetables.
It supports bulk Excel data import, handles different subject categories (Theory, Lab, Library, Mentoring, OE, Project), and produces clean, color-coded timetables for both classes and teachers.

⭐ Key Features

✔ Automated timetable generation using custom rules & constraints

✔ Streamlit web interface — simple, fast, and interactive

✔ Excel upload support to add teacher/class/subject data instantly

✔ Handles theory, lab (2 continuous periods), library, mentoring, open electives, TP, project work, etc.

✔ No teacher conflicts and no subject repetition on the same day

✔ Class-wise and Teacher-wise timetable output

✔ Color-coded timetable visualization

✔ Export timetables as CSV

🛠 Tech Stack

Python 3.x

Streamlit – frontend UI

Pandas – data management

OpenPyXL – Excel file handling

Dataclasses – structured data models

Randomized + rule-based scheduling algorithm

🎯 Purpose

This project is designed for colleges and departments who want to quickly generate accurate, conflict-free timetables without doing manual adjustments.

📁 Input Format

Upload an Excel file containing:

Teacher

Class

Subject

Category

Periods per week

📤 Output

Weekly timetable for every class

Teacher workload table

Properly aligned periods

Color-highlighted subject types

Downloadable CSV files
