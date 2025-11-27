# timetable_generator_improved.py
# Complete app with Teachers / Classes / Assignments side-by-side inside expanders

import streamlit as st
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Tuple, Any
import random, copy, time, itertools, json

# -----------------------
# Page config & CSS
# -----------------------
st.set_page_config(layout="wide", page_title="Timetable Generator — Refined", page_icon="📘")
st.markdown("""
<style>
/* Style the column headers (P1, P2, P3...) */
.centered-table th {
    background-color: #0047AB !important;   /* Change this color */
    color: white !important;
    font-weight: bold;
    text-align: center;
    padding: 8px;
}

/* Style the row headers (Mon, Tue, Wed...) */
.centered-table tbody tr th {
    background-color: #FFA500 !important;  /* Change this color */
    color: black !important;
    font-weight: bold;
    text-align: center;
    padding: 8px;
}

/* Optional: Add borders and table style */
.centered-table td {
    border: 1px solid #ccc !important;
    padding: 8px;
    text-align: center;
}
.centered-table {
    border-collapse: collapse;
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.header-row{display:flex;align-items:center;gap:16px}
.brand{font-size:26px; font-weight:700}
.tagline{color:#6c757d}
.card{background:#ffffffaa;border-radius:10px;padding:12px;box-shadow:0 2px 8px rgba(0,0,0,0.05)}
.small-muted{color:#6c757d;font-size:13px}
</style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
.centered-table {
    width: 100%;
    border-collapse: collapse;
}
.centered-table th, .centered-table td {
    text-align: center;
    vertical-align: middle;
    padding: 8px;
    border: 1px solid #ddd;
}
</style>
""", unsafe_allow_html=True)




# -----------------------
# Domain dataclasses
# -----------------------
@dataclass
class Teacher:
    id: int
    name: str
    subjects: List[str]

@dataclass
class ClassGroup:
    id: int
    name: str

@dataclass
class Assignment:
    id: int
    teacher_id: int
    class_id: int
    subject: str
    category: str      # NEW FIELD
    periods_per_week: int

# -----------------------
# Session state init
# -----------------------
if "teachers" not in st.session_state:
    st.session_state.teachers = []
if "classes" not in st.session_state:
    st.session_state.classes = []
if "assignments" not in st.session_state:
    st.session_state.assignments = []
if "next_teacher_id" not in st.session_state:
    st.session_state.next_teacher_id = 1
if "next_class_id" not in st.session_state:
    st.session_state.next_class_id = 1
if "next_assign_id" not in st.session_state:
    st.session_state.next_assign_id = 1

# single-class specific
if "single_assignments" not in st.session_state:
    st.session_state.single_assignments = []
if "single_schedule" not in st.session_state:
    st.session_state.single_schedule = None
if "attempt_seed" not in st.session_state:
    st.session_state.attempt_seed = 0

# -----------------------
# Utility: save / load JSON for portability
# -----------------------
def export_state_json():
    payload = {
        "teachers":[{"id":t.id,"name":t.name,"subjects":t.subjects} for t in st.session_state.teachers],
        "classes":[{"id":c.id,"name":c.name} for c in st.session_state.classes],
        "assignments":[{"id":a.id,"teacher_id":a.teacher_id,"class_id":a.class_id,"subject":a.subject,"periods_per_week":a.periods_per_week} for a in st.session_state.assignments]
    }
    return json.dumps(payload, indent=2)

def import_state_json(text):
    try:
        obj = json.loads(text)
        st.session_state.teachers = [Teacher(**t) for t in obj.get("teachers",[])]
        st.session_state.classes = [ClassGroup(**c) for c in obj.get("classes",[])]
        loaded_assignments = []
        for a in obj.get("assignments", []):
            if "category" not in a:
                a["category"] = "Theory"
            loaded_assignments.append(Assignment(**a))
        st.session_state.assignments = loaded_assignments
       # update next ids
        st.session_state.next_teacher_id = max([t.id for t in st.session_state.teachers], default=0) + 1
        st.session_state.next_class_id = max([c.id for c in st.session_state.classes], default=0) + 1
        st.session_state.next_assign_id = max([a.id for a in st.session_state.assignments], default=0) + 1
        return True, "Imported state successfully"
    except Exception as e:
        return False, str(e)

# -----------------------
# Header
# -----------------------
with st.container():
    st.markdown("""
    <div style='text-align:center;'>
      <div style='font-size:40px; font-weight:800;'> 🗓 Timetable Generator</div>
      <div style='font-size:16px; color:gray; margin-top:6px; margin-left:37%;'>
    — your complete scheduling companion</div>

    </div>
    """, unsafe_allow_html=True)

# -----------------------
# Sidebar: config & state
# -----------------------
with st.sidebar:
    st.header("Let’s Configure Your Week ")
    days = st.multiselect("Weekdays (preserve order)", ["Mon","Tue","Wed","Thu","Fri","Sat"], default=["Mon","Tue","Wed","Thu","Fri"], key="cfg_days")
    periods_per_day = st.number_input("Periods per day", min_value=1, max_value=12, value=6, step=1, key="cfg_ppd")
    period_length_mins = st.number_input("Period length (mins)", min_value=20, max_value=120, value=50, step=5, key="cfg_plen")
    
    period_timings = [
    "8:15am - 9:05am",
    "9:05am - 9:55am",
    "10:05am - 10:55am",
    "10:55am - 11:45am",
    "12:45pm - 1:30pm",
    "1:30pm - 2:15pm",
    "2:25pm - 3:10pm",
    "3:10pm - 3:55pm"
    ]
    st.divider()
    trials = st.number_input("Randomized trials (best-of-N)", min_value=10, max_value=2000, value=300, step=10, key="cfg_trials")

# -----------------------
# Helper: render side-by-side tables (expanders inside columns)
# -----------------------
def _render_teachers_table():
    if st.session_state.teachers:
        rows = [{"id": t.id, "name": t.name, "subjects": ", ".join(t.subjects)} for t in st.session_state.teachers]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
        # simple delete control
        options = [f"{r['id']} - {r['name']}" for r in rows] + ["None"]
        default_index = len(options)-1
        choice = st.selectbox("Delete teacher", options=options, index=default_index, key="del_teacher_sel")
        if choice != "None" and st.button("Delete selected teacher", key="del_teacher_btn"):
            tid = int(choice.split(" - ")[0])
            st.session_state.teachers = [t for t in st.session_state.teachers if t.id != tid]
            st.session_state.assignments = [a for a in st.session_state.assignments if a.teacher_id != tid]
            st.success("Deleted teacher and related assignments")
    else:
        st.info("No teachers added yet")

def _render_classes_table():
    if st.session_state.classes:
        rows = [{"id": c.id, "name": c.name} for c in st.session_state.classes]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
        options = [f"{r['id']} - {r['name']}" for r in rows] + ["None"]
        default_index = len(options)-1
        choice = st.selectbox("Delete class", options=options, index=default_index, key="del_class_sel")
        if choice != "None" and st.button("Delete selected class", key="del_class_btn"):
            cid = int(choice.split(" - ")[0])
            st.session_state.classes = [c for c in st.session_state.classes if c.id != cid]
            st.session_state.assignments = [a for a in st.session_state.assignments if a.class_id != cid]
            st.success("Deleted class and related assignments")
    else:
        st.info("No classes added yet.")

def _render_assignments_table():
    if st.session_state.assignments:
        rows = []
        for a in st.session_state.assignments:
            tname = next((t.name for t in st.session_state.teachers if t.id == a.teacher_id), "Unknown")
            cname = next((c.name for c in st.session_state.classes if c.id == a.class_id), "Unknown")
            rows.append({
                "id": a.id,
                "teacher": tname,
                "class": cname,
                "subject": a.subject,
                "category": getattr(a, "category", "Theory"),
                "periods_per_week": a.periods_per_week
            })

        st.dataframe(pd.DataFrame(rows), use_container_width=True)
        options = [f"{r['id']} - {r['teacher']} → {r['class']} ({r['subject']})" for r in rows] + ["None"]
        default_index = len(options)-1
        choice = st.selectbox("Delete assignment", options=options, index=default_index, key="del_assign_sel")
        if choice != "None" and st.button("Delete selected assignment", key="del_assign_btn"):
            aid = int(choice.split(" - ")[0])
            st.session_state.assignments = [a for a in st.session_state.assignments if a.id != aid]
            st.success("Deleted assignment")
    else:
        st.info("No assignments added yet.")

def render_side_by_side_tables(use_expanders=True, expand_teachers=True, expand_classes=True, expand_assignments=True):
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        if use_expanders:
            with st.expander("Teachers", expanded=expand_teachers):
                _render_teachers_table()
        else:
            st.subheader("Teachers")
            _render_teachers_table()
    with col2:
        if use_expanders:
            with st.expander("Classes", expanded=expand_classes):
                _render_classes_table()
        else:
            st.subheader("Classes")
            _render_classes_table()
    with col3:
        if use_expanders:
            with st.expander("Assignments", expanded=expand_assignments):
                _render_assignments_table()
        else:
            st.subheader("Assignments")
            _render_assignments_table()

# -----------------------
# Scheduling helpers (kept same as original)
# -----------------------
def build_grid(days: List[str], periods_per_day: int) -> Tuple[List[str], Dict[int, Tuple[str,int]]]:
    timeslots = []
    idx2dp = {}
    idx = 0
    for d in days:
        for p in range(1, periods_per_day+1):
            label = f"{d}-P{p}"
            timeslots.append(label)
            idx2dp[idx] = (d, p)
            idx += 1
    return timeslots, idx2dp

def compute_totals(classes, teachers, assignments):
    class_totals = {}
    teacher_totals = {}
    for a in assignments:
        class_totals[a.class_id] = class_totals.get(a.class_id, 0) + a.periods_per_week
        teacher_totals[a.teacher_id] = teacher_totals.get(a.teacher_id, 0) + a.periods_per_week
    return class_totals, teacher_totals

def diagnose(classes, teachers, assignments, num_slots):
    class_totals, teacher_totals = compute_totals(classes, teachers, assignments)
    class_map = {c.id:c.name for c in classes}
    teacher_map = {t.id:t.name for t in teachers}

    class_rows = []
    for cid, tot in class_totals.items():
        class_rows.append({
            "Class": class_map.get(cid, str(cid)),
            "Requested (pw)": tot,
            "Available": num_slots,
            "Overload": max(0, tot - num_slots)
        })
    teacher_rows = []
    for tid, tot in teacher_totals.items():
        teacher_rows.append({
            "Teacher": teacher_map.get(tid, str(tid)),
            "Requested (pw)": tot,
            "Available": num_slots,
            "Overload": max(0, tot - num_slots)
        })

    class_df = pd.DataFrame(class_rows).sort_values(by="Overload", ascending=False) if class_rows else pd.DataFrame()
    teacher_df = pd.DataFrame(teacher_rows).sort_values(by="Overload", ascending=False) if teacher_rows else pd.DataFrame()

    problems = {
        "class_overload": [(r["Class"], r["Requested (pw)"], r["Available"]) for _,r in class_df.iterrows() if r["Overload"]>0] if not class_df.empty else [],
        "teacher_overload": [(r["Teacher"], r["Requested (pw)"], r["Available"]) for _,r in teacher_df.iterrows() if r["Overload"]>0] if not teacher_df.empty else []
    }

    return {"num_slots": num_slots, "class_df": class_df, "teacher_df": teacher_df, "problems": problems}

def try_place_once(classes, teachers, assignments, timeslots, seed=None):
    if seed is not None:
        random.seed(seed)

    num_slots = len(timeslots)
    class_table = {c.id: [None]*num_slots for c in classes}
    teacher_table = {t.id: [None]*num_slots for t in teachers}

    expanded = []

    # ---- Build block units (Lab / Theory / Others) ----
    for a in assignments:

        # 🧪 LAB — always 2 continuous periods
        if a.category == "Lab":
            for _ in range(a.periods_per_week // 2):
                expanded.append({
                    "teacher_id": a.teacher_id,
                    "class_id": a.class_id,
                    "subject": a.subject,
                    "block": 2,
                    "kind": "lab"
                })
            if a.periods_per_week % 2 == 1:
                expanded.append({
                    "teacher_id": a.teacher_id,
                    "class_id": a.class_id,
                    "subject": a.subject,
                    "block": 1,
                    "kind": "theory"
                })

        # 📘 LIBRARY or MENTORING — single period
        elif a.category in ("Library", "Mentoring"):
            expanded.append({
                "teacher_id": a.teacher_id,
                "class_id": a.class_id,
                "subject": a.subject,
                "block": 1,
                "kind": "theory"
            })

        # 🧮 THEORY / PH / TP — normal subjects
        else:
            subj_upper = a.subject.strip().upper()

            # TP → always 2 continuous periods
            if subj_upper == "TP":
                for _ in range(a.periods_per_week // 2):
                    expanded.append({
                        "teacher_id": a.teacher_id,
                        "class_id": a.class_id,
                        "subject": a.subject,
                        "block": 2,
                        "kind": "theory"
                    })
                if a.periods_per_week % 2 == 1:
                    expanded.append({
                        "teacher_id": a.teacher_id,
                        "class_id": a.class_id,
                        "subject": a.subject,
                        "block": 1,
                        "kind": "theory"
                    })

            # PH → treat like normal theory
            else:
                for _ in range(a.periods_per_week):
                    expanded.append({
                        "teacher_id": a.teacher_id,
                        "class_id": a.class_id,
                        "subject": a.subject,
                        "block": 1,
                        "kind": "theory"
                    })

    # Sort and shuffle blocks
    random.shuffle(expanded)
    expanded.sort(key=lambda x: -x["block"])

    remaining = []

    # ---- Placement loop ----
    for unit in expanded:
        placed = False
        slot_order = list(range(num_slots))
        random.shuffle(slot_order)

        for sidx in slot_order:
            block = unit["block"]
            cid = unit["class_id"]
            tid = unit["teacher_id"]
            subj = unit["subject"]
            kind = unit["kind"]

            day = sidx // periods_per_day
            period = sidx % periods_per_day

            # Prevent overflow across day
            if period + block > periods_per_day:
                continue

            # Block alignment rules
            # if block == 2 and period + 1 >= periods_per_day:
            #     continue


            # Check availability
            if any(class_table[cid][sidx+k] is not None or teacher_table[tid][sidx+k] is not None for k in range(block)):
                continue

            # Prevent same teacher consecutive teaching
            # bad = False
            # for k in range(block):
            #     si = sidx + k
            #     if si > 0 and teacher_table[tid][si-1] is not None:
            #         bad = True
            #         break
            #     if si < num_slots-1 and teacher_table[tid][si+1] is not None:
            #         bad = True
            #         break
            # if bad:
            #     continue

            # Prevent same subject twice in same day
            day_slice = class_table[cid][day*periods_per_day:(day+1)*periods_per_day]
            if any(cell and cell["subject"] == subj for cell in day_slice):
                continue

            # Place it
            for k in range(block):
                si = sidx + k
                class_table[cid][si] = {"subject": subj, "teacher_id": tid}
                teacher_table[tid][si] = {"subject": subj, "class_id": cid}

            placed = True
            break

        if not placed:
            remaining.append(unit)

    return class_table, teacher_table, remaining


def schedule_best_of_n(classes, teachers, assignments, timeslots, trials=300, st_progress=None):
    best_solution = None
    best_remaining = None
    best_placed_count = -1
    num_slots = len(timeslots)

    diag = diagnose(classes, teachers, assignments, num_slots)
    if (not diag["class_df"].empty and diag["class_df"]["Overload"].sum() > 0) or (not diag["teacher_df"].empty and diag["teacher_df"]["Overload"].sum() > 0):
        return None, None, None, {"diag": diag}

    start = time.time()
    for t in range(trials):
        seed = random.randrange(1_000_000)
        class_table, teacher_table, remaining = try_place_once(classes, teachers, assignments, timeslots, seed=seed)
        placed_count = sum(1 for cid in class_table for v in class_table[cid] if v is not None)
        rem_count = len(remaining)
        if best_solution is None or rem_count < best_remaining or (rem_count == best_remaining and placed_count > best_placed_count):
            best_solution = (copy.deepcopy(class_table), copy.deepcopy(teacher_table), list(remaining))
            best_remaining = rem_count
            best_placed_count = placed_count
            if best_remaining == 0:
                break
        if st_progress is not None:
            bar, status = st_progress
            bar.progress(int((t+1)/trials*100))
            if (t+1) % max(1, trials//10) == 0:
                status.text(f"Trials {t+1}/{trials} — best remaining {best_remaining}")
    elapsed = time.time() - start
    if best_solution is None:
        return None, None, None, {"diag": diag}
    return best_solution[0], best_solution[1], best_solution[2], {"best_remaining": best_remaining, "placed": best_placed_count, "elapsed": elapsed}

# -----------------------
# UI: Tabs (Detailed + Single-class)
# -----------------------
tabs = st.tabs(["Department Scheduler","Class Scheduler"])

# -----------------------
# Tab 1: Detailed Scheduler
# -----------------------
with tabs[0]:
    st.subheader("Detailed Department Scheduler")

    # Compact add panel (collapsible)
    with st.expander("Add Teacher / Class / Assignment", expanded=False):
        tcol1, tcol2 = st.columns([2,1])
        with tcol1:
            with st.form("add_teacher", clear_on_submit=True):
                tn = st.text_input("Teacher name", placeholder="e.g. Alice")
                tsubs = st.text_input("Subjects (comma separated)", placeholder="DBMS, OS")
                if st.form_submit_button("Add Teacher"):
                    if tn.strip():
                        subjects_list = [s.strip() for s in tsubs.split(",") if s.strip()]
                        t = Teacher(id=st.session_state.next_teacher_id, name=tn.strip(), subjects=subjects_list)
                        st.session_state.teachers.append(t)
                        st.session_state.next_teacher_id += 1
                        st.success(f"Added teacher {t.name}")
                    else:
                        st.warning("Teacher name required")
        with tcol2:
            with st.form("add_class", clear_on_submit=True):
                cn = st.text_input("Class name", placeholder="e.g. CSE-1")
                if st.form_submit_button("Add Class"):
                    if cn.strip():
                        c = ClassGroup(id=st.session_state.next_class_id, name=cn.strip())
                        st.session_state.classes.append(c)
                        st.session_state.next_class_id += 1
                        st.success(f"Added class {c.name}")
                    else:
                        st.warning("Class name required")

        st.markdown("---")
        if st.session_state.teachers and st.session_state.classes:
            with st.form("add_assignment", clear_on_submit=True):
                teacher_map = {t.name:t.id for t in st.session_state.teachers}
                class_map = {c.name:c.id for c in st.session_state.classes}
                sel_t = st.selectbox("Teacher", options=list(teacher_map.keys()))
                sel_c = st.selectbox("Class", options=list(class_map.keys()))
                subj = st.text_input("Subject name", placeholder="e.g. DBMS")
                category = st.selectbox("Category", ["Theory", "Lab", "Library", "Mentoring"])

                p = st.number_input("Periods per week", min_value=1, value=2, max_value=periods_per_day*max(1,len(days)), step=1)
                if st.form_submit_button("Add Assignment"):
                    if not subj.strip():
                        st.warning("Subject required")
                    else:
                        a = Assignment(
                            id=st.session_state.next_assign_id,
                            teacher_id=teacher_map[sel_t],
                            class_id=class_map[sel_c],
                            subject=subj.strip(),
                            category=category,
                            periods_per_week=int(p)
                        )
                        st.session_state.assignments.append(a)
                        st.session_state.next_assign_id += 1
                        st.success(f"Assigned {sel_t} → {sel_c} ({subj.strip()}, {p} pw)")
        else:
            st.info("Add at least one teacher and one class to create assignments")

    st.markdown("---")
    st.subheader("All Your Schedule Inputs at a Glance")
    # metrics row
    colA, colB, colC, colD = st.columns([1,1,1,1])
    num_teachers = len(st.session_state.teachers)
    num_classes = len(st.session_state.classes)
    num_assigns = len(st.session_state.assignments)
    total_periods = sum(a.periods_per_week for a in st.session_state.assignments)
    colA.metric("Teachers", num_teachers)
    colB.metric("Classes", num_classes)
    colC.metric("Assignments", num_assigns)
    colD.metric("Total requested periods/week", total_periods)
    
    # Render the three tables side-by-side in expanders
    render_side_by_side_tables(use_expanders=True, expand_teachers=True, expand_classes=True, expand_assignments=True)

    #st.markdown("---")
    # -----------------------
# 📥 Import from Excel
# -----------------------
st.markdown("### 📥 Import Timetable Data from Excel")

uploaded_file = st.file_uploader("Upload Excel file (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)

        # Expected columns
        required_cols = ["Teacher", "Class", "Subject", "Category", "Periods/week"]
        if not all(col in df.columns for col in required_cols):
            st.error(f"Excel must have these columns: {', '.join(required_cols)}")
        else:
            # Clear previous data
            st.session_state.teachers = []
            st.session_state.classes = []
            st.session_state.assignments = []
            st.session_state.next_teacher_id = 1
            st.session_state.next_class_id = 1
            st.session_state.next_assign_id = 1

            teacher_map = {}
            class_map = {}

            for _, row in df.iterrows():
                tname = str(row["Teacher"]).strip()
                cname = str(row["Class"]).strip()
                subj = str(row["Subject"]).strip()
                cat = str(row["Category"]).strip()
                pw = int(row["Periods/week"])

                # Add teacher
                if tname not in teacher_map:
                    t = Teacher(id=st.session_state.next_teacher_id, name=tname, subjects=[])
                    st.session_state.teachers.append(t)
                    teacher_map[tname] = t.id
                    st.session_state.next_teacher_id += 1

                # Add class
                if cname not in class_map:
                    c = ClassGroup(id=st.session_state.next_class_id, name=cname)
                    st.session_state.classes.append(c)
                    class_map[cname] = c.id
                    st.session_state.next_class_id += 1

                # Add assignment
                a = Assignment(
                    id=st.session_state.next_assign_id,
                    teacher_id=teacher_map[tname],
                    class_id=class_map[cname],
                    subject=subj,
                    category=cat,
                    periods_per_week=pw
                )
                st.session_state.assignments.append(a)
                st.session_state.next_assign_id += 1

            st.success("✅ Excel data imported successfully! Ready to generate timetable.")
            st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"Error reading Excel: {e}")


    # Generate button and diagnostics
    cols = st.columns([1,1,1])
    generate = cols[1].button("Generate Timetable — Detailed", type="primary")
    if generate:
        if not st.session_state.classes or not st.session_state.teachers or not st.session_state.assignments:
            st.warning("Add at least one teacher, one class, and one assignment first.")
        else:
            timeslots, idx2dp = build_grid(days, periods_per_day)
            num_slots = len(timeslots)

            diag = diagnose(st.session_state.classes, st.session_state.teachers, st.session_state.assignments, num_slots)
            st.header("Pre-schedule Diagnostics")
            st.markdown(f"Available slots per class / teacher: **{num_slots} (days={len(days)} × periods/day={periods_per_day})")

            if not diag["class_df"].empty:
                st.dataframe(diag["class_df"], use_container_width=True)
            if not diag["teacher_df"].empty:
                st.dataframe(diag["teacher_df"], use_container_width=True)

            if diag["problems"]["class_overload"] or diag["problems"]["teacher_overload"]:
                st.error("Overload detected — schedule cannot be generated. See suggested fixes above.")
            else:
                progress_bar = st.progress(0)
                status = st.empty()
                class_table, teacher_table, remaining, meta = schedule_best_of_n(st.session_state.classes, st.session_state.teachers, st.session_state.assignments, timeslots, trials=trials, st_progress=(progress_bar, status))
                progress_bar.progress(100)
                if "diag" in (meta or {}):
                    st.error("Scheduling aborted due to diagnose issues.")
                else:
                    status.text(f"Done — best_remaining: {meta.get('best_remaining')}, placed: {meta.get('placed')}, time: {meta.get('elapsed'):.2f}s")
                    st.success("Scheduling finished — see timetables below.")

                    st.markdown("### Timetables by Class")
                    for c in st.session_state.classes:
                        st.subheader(c.name)
                        matrix = []
                        for d_idx, d in enumerate(days):
                            row = []
                            for p in range(periods_per_day):
                                sidx = d_idx*periods_per_day + p
                                val = class_table[c.id][sidx]
                                if val is None:
                                    row.append(" ")
                                else:
                                    tname = next((t.name for t in st.session_state.teachers if t.id == val["teacher_id"]), "Unknown")
                                    row.append(f"{val['subject']} ({tname})")
                            matrix.append(row)
                        cols = [(f"P{p}", period_timings[p-1]) for p in range(1, periods_per_day+1)]
                        df = pd.DataFrame(matrix, index=days, columns=pd.MultiIndex.from_tuples(cols))

                        st.markdown(
    df.to_html(classes='centered-table', index=True, escape=False),
    unsafe_allow_html=True
)

                        st.download_button(
                            label=f"Download {c.name} CSV",
                            data=df.to_csv(),
                            file_name=f"timetable_{c.name}.csv",
                            mime="text/csv",
                            key=f"download_class_{c.name}"  # ✅ Unique key for each class
)


                    st.markdown("### Timetables by Teacher")
                    for t in st.session_state.teachers:
                        st.subheader(t.name)
                        matrix = []
                        for d_idx, d in enumerate(days):
                            row = []
                            for p in range(periods_per_day):
                                sidx = d_idx*periods_per_day + p
                                val = teacher_table[t.id][sidx]
                                if val is None:
                                    row.append(" ")
                                else:
                                    cname = next((c.name for c in st.session_state.classes if c.id == val["class_id"]), "Unknown")
                                    row.append(f"{val['subject']} ({cname})")
                            matrix.append(row)
                        cols = [(f"P{p}", period_timings[p-1]) for p in range(1, periods_per_day+1)]
                        df = pd.DataFrame(matrix, index=days, columns=pd.MultiIndex.from_tuples(cols))

                        st.markdown(
                        df.to_html(classes='centered-table', index=True, escape=False),
                        unsafe_allow_html=True
)

                        st.download_button(
                            label=f"Download {t.name} CSV",
                            data=df.to_csv(),
                            file_name=f"timetable_{t.name}.csv",
                            mime="text/csv",
                            key=f"download_teacher_{t.name}"  # ✅ Unique key for each teacher
                            )

                    if meta.get("best_remaining", 0) > 0:
                        st.warning(f"Could not place {meta.get('best_remaining')} periods even after {trials} trials.")
                        rem_df = pd.DataFrame(remaining) if remaining else pd.DataFrame()
                        if not rem_df.empty:
                            rem_df['teacher_name'] = rem_df['teacher_id'].map({t.id:t.name for t in st.session_state.teachers})
                            rem_df['class_name'] = rem_df['class_id'].map({c.id:c.name for c in st.session_state.classes})
                            st.dataframe(rem_df[['teacher_name','class_name','subject']])

# -----------------------
# Tab 2: Single-class 5x8 builder
# -----------------------
with tabs[1]:
    st.subheader("Customize your class Scheduler")
    CATEGORIES = ["Laboratory","Open Elective","Library","Mentoring","Main subject 1","Main subject 2","Professional Elective 1","Professional Elective 2","Project"]
    DEFAULT_PERIOD_SUGGEST = {"Laboratory":4,"Open Elective":4,"Library":1,"Mentoring":1,"Main subject 1":6,"Main subject 2":6,"Professional Elective 1":5,"Professional Elective 2":5,"Project":4}
    DAYS = ["Mon","Tue","Wed","Thu","Fri"]
    SLOTS_PER_DAY = 8

    st.markdown("Set up subjects for this class with flexible period customization.")
    sc1, sc2, sc3, sc4 = st.columns([2,2,2,1])
    with sc1:
        category = st.selectbox("Category", options=CATEGORIES, key="scat")
    with sc2:
        subject_name = st.text_input("Subject name", key="sname", placeholder="e.g. Data Structures")
    with sc3:
        staff_name = st.text_input("Staff name", key="sstaff", placeholder="e.g. Prof. X")
    with sc4:
        suggested = DEFAULT_PERIOD_SUGGEST.get(category,1)
        periods = st.number_input("Periods/week", min_value=1, max_value=40, value=suggested, key="speriods")

    add_col, clear_col = st.columns([1,1])
    with add_col:
        if st.button("Add subject to list"):
            if not subject_name.strip():
                st.warning("Enter a subject name")
            else:
                st.session_state.single_assignments.append({"category":category, "subject":subject_name.strip(), "staff":staff_name.strip(), "periods":int(periods)})
                st.success(f"Added {subject_name.strip()} ({periods} pw)")
    with clear_col:
        if st.button("Clear subject list"):
            st.session_state.single_assignments = []
            st.session_state.single_schedule = None
            st.info("Cleared subject list and schedule")

    st.markdown("### Current subjects")
    if st.session_state.single_assignments:
        st.dataframe(pd.DataFrame(st.session_state.single_assignments), use_container_width=True)
    else:
        st.info("No subjects added yet")

    st.markdown("---")
    if st.button("Create timetable — single class"):
        st.session_state.attempt_seed += 1
        seed = st.session_state.attempt_seed

        # create_single_class_timetable is unchanged (keeps behaviour)
        def create_single_class_timetable(subjects, seed=0):
            random.seed(seed)
            total = sum((s.get("periods",0) for s in subjects))
            if total > SLOTS_PER_DAY * len(DAYS):
                return None, f"Requested total periods {total} > available {SLOTS_PER_DAY*len(DAYS)}."

            blocks = []
            for s in subjects:
                cat = s.get("category","")
                name = s.get("subject","")
                staff = s.get("staff","")
                p = int(s.get("periods",0))
                if cat == "Laboratory":
                    if p < 2:
                        return None, f"Lab {name} has {p} periods — must be at least 2."
                    blocks.append({"subject": name, "staff": staff, "periods": p, "kind":"lab", "meta":{}})
                elif cat == "Open Elective":
                    if p != 4:
                        return None, f"Open Elective '{name}' must be exactly 4 periods (2+2)."
                    blocks.append({"subject": name, "staff": staff, "periods": p, "kind":"open_elective", "meta":{}})
                elif cat == "Library":
                    blocks.append({"subject": name, "staff": staff, "periods": p, "kind":"library", "meta":{}})
                elif cat == "Mentoring":
                    blocks.append({"subject": name, "staff": staff, "periods": p, "kind":"mentoring", "meta":{}})
                elif cat.startswith("Main subject"):
                    blocks.append({"subject": name, "staff": staff, "periods": p, "kind":"main", "meta":{}})
                elif cat.startswith("Professional Elective"):
                    blocks.append({"subject": name, "staff": staff, "periods": p, "kind":"prof", "meta":{}})
                elif cat == "Project":
                    if p != 4:
                        return None, f"Project '{name}' must be 4 periods and scheduled as 2+2."
                    blocks.append({"subject": name, "staff": staff, "periods": p, "kind":"project", "meta":{}})
                else:
                    blocks.append({"subject": name, "staff": staff, "periods": p, "kind":"other", "meta":{}})

            lib = [b for b in blocks if b["kind"] == "library"]
            ment = [b for b in blocks if b["kind"] == "mentoring"]
            if lib and ment:
                lib_b = lib[0]; ment_b = ment[0]
                blocks = [b for b in blocks if b not in (lib_b, ment_b)]
                combined = {
                    "subject": f"{lib_b['subject']}/{ment_b['subject']}",
                    "staff": f"{lib_b['staff']}/{ment_b['staff']}",
                    "periods": 2,
                    "kind": "lib_ment_combined",
                    "meta": {"order_options":[(lib_b['subject'], ment_b['subject']), (ment_b['subject'], lib_b['subject'])]}
                }
                blocks.append(combined)
            elif lib or ment:
                return None, "Library and Mentoring must both be present and scheduled together (adjacent)."

            def generate_partitions(total: int, max_block: int = 3):
                results = []
                def helper(remaining, max_part, current):
                    if remaining == 0:
                        results.append(current.copy())
                        return
                    for p in range(min(max_part, remaining), 0, -1):
                        if p > max_block:
                            continue
                        if current and p > current[-1]:
                            continue
                        current.append(p)
                        helper(remaining - p, p, current)
                        current.pop()
                helper(total, max_block, [])
                return results

            def partitions_for(subject_block):
                kind = subject_block["kind"]
                total_p = subject_block["periods"]
                if kind == "lab":
                    if total_p == 4:
                        return [[2,2]]
                    else:
                        parts = []
                        if total_p % 2 == 0 and total_p//2 <= 4:
                            parts.append([2]*(total_p//2))
                        parts.append([total_p])
                        return parts
                elif kind == "open_elective":
                    return [[2,2]]
                elif kind == "project":
                    return [[2,2]]
                elif kind == "lib_ment_combined":
                    return [[2]]
                elif kind == "main":
                    return generate_partitions(total_p, max_block=3) or [[total_p]]
                elif kind == "prof":
                    return generate_partitions(total_p, max_block=3) or [[total_p]]
                else:
                    return generate_partitions(total_p, max_block=3) or [[total_p]]

            subj_candidates = []
            for b in blocks:
                parts = partitions_for(b)
                if not parts:
                    parts = [[b['periods']]]
                subj_candidates.append({"block": b, "candidates": parts})

            MAX_PARTITION_COMBINATIONS = 6000
            choices_lists = [c["candidates"] for c in subj_candidates]
            prod_count = 1
            for ch in choices_lists:
                prod_count *= max(1, len(ch))

            def partition_combinations_iter():
                if prod_count <= MAX_PARTITION_COMBINATIONS:
                    for combo in itertools.product(*choices_lists):
                        yield combo
                else:
                    tried = set()
                    attempts = 0
                    while attempts < MAX_PARTITION_COMBINATIONS:
                        combo = tuple(random.choice(lst) for lst in choices_lists)
                        if combo not in tried:
                            tried.add(combo)
                            yield combo
                        attempts += 1

            def make_block_instances(combo):
                insts = []
                for subj_choice, subinfo in zip(combo, subj_candidates):
                    b = subinfo["block"]
                    sizes = list(subj_choice)
                    for sz in sizes:
                        inst = {"subject": b["subject"], "staff": b["staff"], "size": sz, "kind": b["kind"], "orig_periods": b["periods"], "meta": b.get("meta", {})}
                        insts.append(inst)
                insts.sort(key=lambda x: (-x["size"], x["kind"]))
                return insts

            def try_place(instances):
                sched = [[None]*SLOTS_PER_DAY for _ in DAYS]
                per_day_subject_counts = {d:{} for d in range(len(DAYS))}

                def backtrack(idx):
                    if idx >= len(instances):
                        return True
                    inst = instances[idx]
                    subj = inst["subject"]
                    size = inst["size"]
                    kind = inst["kind"]

                    day_order = list(range(len(DAYS)))
                    day_order.sort(key=lambda d: sum(1 for c in sched[d] if c is None), reverse=True)
                    slot_order = list(range(SLOTS_PER_DAY - size + 1))

                    for d in day_order:
                        for s in slot_order:
                            if any(sched[d][s+k] is not None for k in range(size)):
                                continue
                            if kind in ("main","prof"):
                                already = per_day_subject_counts[d].get(subj, 0)
                                if already + size > 3:
                                    continue
                            # place
                            if kind == "lib_ment_combined" and inst["meta"].get("order_options"):
                                first, second = inst["meta"]["order_options"][0]
                                labels = [first, second]
                                if size != 2:
                                    labels = [inst["subject"]] * size
                                for k in range(size):
                                    sched[d][s+k] = f"{labels[k]} ({inst['staff']})"
                            else:
                                for k in range(size):
                                    sched[d][s+k] = f"{subj} ({inst['staff']})"
                            per_day_subject_counts[d][subj] = per_day_subject_counts[d].get(subj, 0) + size

                            if backtrack(idx+1):
                                return True

                            for k in range(size):
                                sched[d][s+k] = None
                            per_day_subject_counts[d][subj] -= size
                            if per_day_subject_counts[d][subj] == 0:
                                del per_day_subject_counts[d][subj]
                    return False

                ok = backtrack(0)
                if ok:
                    return sched
                return None

            for combo in partition_combinations_iter():
                insts = make_block_instances(combo)
                if sum(i["size"] for i in insts) != total:
                    continue
                orderings = [insts]
                for _ in range(8):
                    tmp = insts.copy()
                    random.shuffle(tmp)
                    tmp.sort(key=lambda x: -x["size"])
                    orderings.append(tmp)
                for ordering in orderings:
                    sched = try_place(ordering)
                    if sched is not None:
                        out = []
                        for drow in sched:
                            out_row = []
                            for cell in drow:
                                out_row.append(cell if cell is not None else " ")
                            out.append(out_row)
                        return out, "ok"
            return None, "No feasible arrangement found with given constraints and subject partitions."

        schedule, msg = create_single_class_timetable(st.session_state.single_assignments, seed=seed)
        if schedule is None:
            st.error(msg)
            st.session_state.single_schedule = None
        else:
            st.success("Schedule created — preview below")
            st.session_state.single_schedule = schedule

    # render schedule preview
    if st.session_state.single_schedule is None:
        st.info("No single-class timetable generated yet")
    else:
        df = pd.DataFrame(st.session_state.single_schedule, index=DAYS, columns=[f"P{p}" for p in range(1, SLOTS_PER_DAY+1)])
        st.markdown(
    df.to_html(classes='centered-table', index=True, escape=False),
    unsafe_allow_html=True
)

        st.download_button("Download CSV", df.to_csv(), file_name="single_class_timetable.csv", mime="text/csv")

# -----------------------
# Footer
# -----------------------
#st.markdown("---")
#st.caption("Want tweaks? Tell me which specifically: colors, layout density, export options (PDF/Excel), or integration with your existing app.")