import streamlit as st
import pandas as pd
from my_pipeline import run_pipeline
import tkinter as tk
from tkinter import filedialog
import os
from datetime import datetime
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="altair")
warnings.filterwarnings("ignore", message="I don't know how to infer vegalite type")
pd.set_option('future.no_silent_downcasting', True)

st.set_page_config(page_title="Well Report Analytics Tool")

st.title("Well Report Analytics Tool")

st.divider()

# =========================================================
# --- 1. GLOBAL INITIALIZATION (Fixes AttributeError) ---
# =========================================================
if 'folder_path' not in st.session_state:
    st.session_state.folder_path = ""

if 'last_updated' not in st.session_state:
    st.session_state.last_updated = None

if 'folder_history' not in st.session_state:
    st.session_state.folder_history = {}

if 'last_file_count' not in st.session_state:
    st.session_state.last_file_count = 0
# =========================================================
# --- 2. FOLDER SELECTION LOGIC ---
# =========================================================
st.sidebar.header("Data Source")

if st.sidebar.button("📁 Select DDR/DCR Folder"):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    selected_path = filedialog.askdirectory(master=root)
    root.update()
    root.destroy()

    if selected_path:
        st.session_state.folder_path = selected_path
        st.cache_data.clear()
        # REMOVED the line that set history to 0
        st.rerun()

# Stop the app if no folder is selected
if not st.session_state.folder_path:
    st.sidebar.info("Please select the folder containing your DDR/DCR PDFs.")
    st.stop()

# Display current folder info
st.sidebar.success(f"Selected: {os.path.basename(st.session_state.folder_path)}")


# =========================================================
# --- 3. DATA LOADING WRAPPER ---
# =========================================================
def get_well_data(path):
    return cached_run_pipeline(path)


@st.cache_data(show_spinner=False)
def cached_run_pipeline(path):
    progress_text = "Analyzing Wells... Please wait."
    my_bar = st.progress(0, text=progress_text)
    df, df_npt = run_pipeline(path, progress_bar=my_bar)
    my_bar.empty()
    return df, df_npt

if st.session_state.folder_path:
    # 1. Check current folder status
    current_files = [f for f in os.listdir(st.session_state.folder_path) if f.lower().endswith(".pdf")]
    current_count = len(current_files)

    # # 2. Fetch data from cache or pipeline
    # df, df_npt = get_well_data(st.session_state.folder_path)
    # 2. Fetch data from cache or pipeline
    df, df_npt = get_well_data(st.session_state.folder_path)

    #  Ensure last_updated is set on initial load
    if st.session_state.last_updated is None:
        st.session_state.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Ensure required columns exist (prevents crashes across DDR/DCR)
    required_cols = ["Efficiency", "Report_Type"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0

    # ✅ ADD THIS BLOCK (AFE safety)
    afe_cols = ["Final_AFE_Well", "AFE_Cost_USD", "Section_ID", "New_Section"]

    for col in afe_cols:
        if col not in df.columns:
            if col == "New_Section":
                df[col] = False
            else:
                df[col] = 0


    # 3. Handle empty data immediately
    if df.empty:
        st.error(f"❌ No valid drilling/Completion data found in: {os.path.basename(st.session_state.folder_path)}")
        if st.button("Try another folder"):
            st.session_state.folder_path = ""
            st.rerun()
        st.stop()

    # # 4. Set initial baseline if first time running
    # if st.session_state.last_updated is None:
    #     st.session_state.last_file_count = current_count
    #     st.session_state.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 5. Create the "All Wells" copies for comparison
    df_all = df.copy()
    df_npt_all = df_npt.copy()

    # =========================================================
    # --- FIXED FILE CHANGE DETECTION (SAFE VERSION)
    # =========================================================

    current_path = st.session_state.folder_path

    current_files = sorted([
        f for f in os.listdir(current_path)
        if f.lower().endswith(".pdf")
    ])

    # --- Ensure correct data type (fix old int bug)
    if current_path in st.session_state.folder_history:
        if isinstance(st.session_state.folder_history[current_path], int):
            st.session_state.folder_history[current_path] = current_files

    # First time seeing folder
    if current_path not in st.session_state.folder_history:
        st.session_state.folder_history[current_path] = current_files
        last_files = current_files
    else:
        last_files = st.session_state.folder_history[current_path]

    # Detect actual new files
    new_files = list(set(current_files) - set(last_files))

    # --- ALERT ---
    if new_files:
        st.sidebar.warning(f"✨ {len(new_files)} new file(s) detected")

        if st.sidebar.button("Update Dashboard 🔄"):
            st.cache_data.clear()
            st.session_state.folder_history[current_path] = current_files
            st.session_state.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.rerun()

    else:
        if st.sidebar.button("Force Refresh Cache"):
            st.cache_data.clear()
            st.session_state.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.rerun()
# --- Sidebar Status ---
st.sidebar.success(f"✅ Dataset Loaded")
if st.session_state.last_updated:
    st.sidebar.caption(f"Last processed at: {st.session_state.last_updated}")
###
# -------------------
# REPORT TYPE FILTER
# -------------------
report_type_selected = st.sidebar.radio(
    "Select Report Type",
    ["DDR", "DCR"]
)
###
is_drilling = report_type_selected == "DDR"
is_completion = report_type_selected == "DCR"
###
#
# SAFE CHECK (prevents crash if column not yet created in pipeline)
if "Report_Type" in df.columns:
    df = df[df["Report_Type"] == report_type_selected]
else:
    st.sidebar.warning("Report_Type not detected yet - showing all data")

#####
# ✅ ADD THIS BLOCK (CRITICAL FIX)
if df.empty:
    st.warning(f"No {report_type_selected} data found in selected folder.")
    st.stop()
#####
# ✅ FILTER NPT ALSO
if "Report_Type" in df_npt.columns:
    df_npt = df_npt[df_npt["Report_Type"] == report_type_selected]
###
st.sidebar.write("---")
st.sidebar.write(f"**Folder:** {os.path.basename(st.session_state.folder_path)}")
#st.sidebar.write(f"**Total PDFs found:** {st.session_state.last_file_count}")
st.sidebar.write(f"**Total PDFs found:** {len(current_files)}")
#st.sidebar.write(f"**Total PDFs found:** {current_count}")
st.sidebar.write(f"**Unique Wells:** {df_all['Well'].nunique()}")

# -------------------
# WELL FILTER
# -------------------
st.sidebar.header("Filters")

# WELL
well_options = df["Well"].unique()
well = st.sidebar.selectbox("Select Well", well_options)

# Apply Well Filter to both DataFrames
df = df[df["Well"] == well]
df_npt = df_npt[df_npt["Well"] == well]

# REPORT NUMBER
reports = ["All"] + sorted(df["Report_No"].dropna().unique())
report_selected = st.sidebar.selectbox("Report Number", reports)

if report_selected != "All":
    df = df[df["Report_No"] == report_selected]
    df_npt = df_npt[df_npt["Report_No"] == report_selected]



# -------------------
# ✅ CUMULATIVE NPT PER REPORT
# -------------------
if not df_npt.empty:
    npt_summary = (
        df_npt.groupby("Report_No")["Duration"]
        .sum()
        .reset_index()
        .rename(columns={"Duration": "NPT_hrs"})
    )

    ###
    # Ensure same datatype before merge
    df["Report_No"] = pd.to_numeric(df["Report_No"], errors="coerce")
    df_npt["Report_No"] = pd.to_numeric(df_npt["Report_No"], errors="coerce")
    ###

    df = df.merge(npt_summary, on="Report_No", how="left")
    df["NPT_hrs"] = df["NPT_hrs"].fillna(0)
else:
    df["NPT_hrs"] = 0


# HOLE SECTION
if is_drilling:
    sections = ["All"] + sorted(df["Hole_Size_in"].dropna().unique())
    section = st.sidebar.selectbox("Hole Section", sections)

    if section != "All":
        df = df[df["Hole_Size_in"] == section]

#-------------
# Report Range Filter
#----------------
st.sidebar.subheader("Report Range")

min_report = int(df["Report_No"].min())
max_report = int(df["Report_No"].max())

# ✅ HANDLE SINGLE REPORT CASE
if min_report == max_report:

    st.sidebar.info(f"Only one report available: {min_report}")

    report_range = (min_report, max_report)

else:

    report_range = st.sidebar.slider(
        "Select Report Range",
        min_report,
        max_report,
        (min_report, max_report)
    )

# Apply filter
df = df[
    (df["Report_No"] >= report_range[0]) &
    (df["Report_No"] <= report_range[1])
]

####
if df.empty:
    st.warning("No data available for selected filters")
    st.stop()
####

#st.sidebar.write("Total Files in Folder:", st.session_state.last_file_count)
#st.sidebar.write(f"**Total PDFs found:** {current_count}")
if is_drilling:
    st.sidebar.write("Meters Drilled:", f"{df['End_Depth_m'].max():,.0f} m")
#st.sidebar.write("Meters Drilled:", f"{df['End_Depth_m'].max():,.0f} m")

#------------------------------------------------------
# After all sidebar filtering logic...
#------------------------------------------------------
if df.empty:
    st.warning("⚠️ No data matches these filters. Please adjust your selection.")
    st.stop() # This stops the script safely without a "Crash" screen


# -------------------
# SORT DATA
# -------------------

df = df.sort_values("Report_Date")



# -------------------
# KPI calculations
# -------------------

current_depth = df["End_Depth_m"].max()

if is_drilling:
    avg_rop = df["Avg_ROP_mhr"].mean()
else:
    avg_rop = 0

total_cost = df["Cumulative_Cost_USD"].max()

total_depth = df["End_Depth_m"].max()

if total_depth == 0:
    avg_cost_meter = 0
else:
    avg_cost_meter = df["Day_Cost_USD"].sum() / total_depth


if is_drilling and "Efficiency" in df.columns:
    avg_efficiency = df["Efficiency"].mean()
else:
    avg_efficiency = 0


# -------------------
# ✅ NPT KPI
# -------------------
total_npt = df_npt["Duration"].sum()

#---------------------------------
# Current Phase
#-----------------------------------
latest_phase = df.sort_values("Report_Date").iloc[-1]["Detected_Phase"]
# -------------------
# KPI display
# -------------------
col1, col2, col3 = st.columns(3)
col4, col5, col6 = st.columns(3)

#col1.metric("Current Depth (m)", f"{current_depth:,.0f}")
if is_drilling:
    col1.metric("Current Depth (m)", f"{current_depth:,.0f}")
else:
    col1.metric("Total Reports", df["Report_No"].nunique())

col2.metric("Total Cost (USD)", f"${total_cost:,.0f}")

if is_drilling:

    col3.metric("Average ROP (m/hr)", f"{avg_rop:.2f}")
    col4.metric("Avg Cost per Meter", f"${avg_cost_meter:.2f}")
    col5.metric("Drilling Efficiency", f"{avg_efficiency:.2f}")
else:
    latest_phase = (
        df.sort_values("Report_Date")
        .iloc[-1]["Detected_Phase"]
    )

    col3.metric("Current Phase", latest_phase)
    #col3.metric("Reports Count", df["Report_No"].nunique())
    col4.metric("Avg Daily Cost", f"${df['Day_Cost_USD'].mean():,.0f}")
    col5.metric("Total Days", df["Report_No"].nunique())

col6.metric("Total NPT (hrs)", f"{total_npt:.2f}")
#--------------------------------------------------------------
# NPT Percentage vs drilling hours
#-----------------------------------------------------------------
# -------------------
# ✅ TIME-BASED NPT CALCULATION (DDR + DCR)
# -------------------

max_report = df["Report_No"].max()

if pd.notna(max_report) and max_report > 0:
    total_time = max_report * 24  # hours
else:
    total_time = 0

if total_time > 0:
    npt_pct = (total_npt / total_time) * 100
    productive_pct = ((total_time - total_npt) / total_time) * 100
else:
    npt_pct = 0
    productive_pct = 0

# Display
col7, col8, col9 = st.columns(3)

col7.metric("NPT %", f"{npt_pct:.1f}%")
col8.metric("Productive Time %", f"{productive_pct:.1f}%")


# -------------------
# ✅ NPT COST IMPACT
# -------------------
df["NPT_Cost"] = df["NPT_hrs"] * (df["Day_Cost_USD"] / 24)

##
st.divider()
##

#------------------
# Total npt cost
#----------------------
total_npt_cost = df["NPT_Cost"].sum()
col9.metric("NPT Cost Impact", f"${total_npt_cost:,.0f}")
##
st.divider()
##

#--------------------------------------
# Worst NPT day
#-----------------------------------------

if not df.empty and "NPT_hrs" in df.columns:
    worst_npt_idx = df["NPT_hrs"].idxmax()
    worst_npt_day = df.loc[worst_npt_idx]

    st.warning(
        f"Highest NPT on Report {int(worst_npt_day['Report_No'])}: "
        f"{worst_npt_day['NPT_hrs']:.2f} hrs"
    )


##
st.divider()
##

# -------------------
# ✅ EXECUTIVE SUMMARY (AUTO-GENERATED)
# -------------------
st.subheader("Executive Summary")

# Calculations for the summary
current_well = well
days_drilled = df["Report_No"].nunique()
depth_reached = df["End_Depth_m"].max()
last_date = df["Report_Date"].max().strftime('%d-%b-%Y')
total_npt_val = df_npt["Duration"].sum()
#total_npt_val = df["NPT_hrs"].sum()
afe_val = df["Final_AFE_Well"].max() if "Final_AFE_Well" in df.columns else 0

if afe_val and afe_val > 0:
    budget_pct = (df["Cumulative_Cost_USD"].max() / afe_val) * 100
else:
    budget_pct = 0

# Determine Status Color
status_color = "green"
if budget_pct > 90 or total_npt_val > 24:
    status_color = "orange"
if budget_pct > 100:
    status_color = "red"

# Construct the Summary Sentence
if is_drilling:
    summary_text = f"""

    Current depth: **{depth_reached:,.0f} m**  
    Budget used: **{budget_pct:.1f}%**

    NPT: **{total_npt_val:.2f} hrs ({npt_pct:.1f}%)**
    """
else:
    summary_text = f"""

    Total cost to date: **${df['Cumulative_Cost_USD'].max():,.0f}**

    NPT: **{total_npt_val:.2f} hrs ({npt_pct:.1f}%)**
    """
st.info(summary_text)

# Quick "At-a-Glance" Status Indicator
if status_color == "green":
    st.success("Project is ON TRACK and within budget parameters.")
elif status_color == "orange":
    st.warning("⚠️ Project requires ATTENTION due to NPT accumulation or budget threshold (90%+).")
else:
    st.error("🚨 Project is OVER BUDGET. Immediate financial review recommended.")



##
st.divider()
##
#-----------------------------------------------
# Download Button
#-------------------------------------------
st.download_button(
    label="Download Dataset",
    data=df.to_csv(index=False),
    file_name="drilling_analysis.csv",
    mime="text/csv"
)


##
st.divider()
##


#-----------------------------------------------
# Data Statistics Panel
#----------------------------------------------
st.subheader("Dataset Statistics")

st.write("Total Reports For Selected Well:", df["Report_No"].nunique())
if is_drilling:
    st.write("Total Meters Drilled:", df["End_Depth_m"].max())
#st.write("Total Meters Drilled:", df["End_Depth_m"].max())





#------------------------------------------------------------
# Daily Progress
#---------------------------------------------------------
df = df.sort_values("Report_Date")

df["Daily_Progress"] = df["End_Depth_m"].diff().clip(lower=0)

last_progress = df["Daily_Progress"].iloc[-1]

if is_drilling:
    ##
    st.divider()
    ##
    st.subheader("Latest Activity")

    if last_progress > 0:
        st.success(f"Drilling in progress: {last_progress:.1f} m drilled last report")
    else:
        st.warning("No drilling progress in last report (possible NPT or operations)")





#---------------------------------
# Recent Progress
#----------------------------------

recent_progress = df["Daily_Progress"].tail(5).mean()
###
if is_drilling:
    ##
    st.divider()
    ##
    st.metric(
        "Avg Progress (Last 5 Reports)",
        f"{recent_progress:.1f} m/day"
    )
###






#----------------------------------------
# Well Planning
#------------------------------------
if is_drilling:
    st.sidebar.subheader("Well Planning")


    planned_td = st.sidebar.number_input(
        "Planned Total Depth (m)",
        min_value=0,
        value=int(df["End_Depth_m"].max())
    )

    current_depth = df["End_Depth_m"].max()


    if planned_td == current_depth:
        st.sidebar.warning(
            "Planned TD currently equals the current depth!!. "
            "Enter the Planned Total Depth (TD) from the drilling program. "
            "The default value equals the current depth. "
            "If the well is completed you may leave it unchanged."
        )

    elif planned_td < current_depth:
        st.sidebar.warning(
            "Planned TD is less than current depth!!. "
            "Enter the CORRECT Planned Total Depth (TD) from the drilling program. "
            "Planned TD have to be above the current depth in Most Cases."

        )



#----------------------------
# Well Progress
#------------------------------
if is_drilling:
    st.subheader("Well Progress")

    current_depth = df["End_Depth_m"].max()

    if planned_td == 0:
        progress = 0
    else:
        progress = min(current_depth / planned_td, 1.0)

    progress_percent = progress * 100

    st.progress(min(progress, 1.0))

    st.write(f"Current Depth: **{current_depth:,.0f} m**")
    st.write(f"Planned TD: **{planned_td:,.0f} m**")
    st.write(f"Well Completion: **{progress_percent:.1f}%**")
###



##
st.divider()
##

#--------------------------------
# AFE Analysis
#--------------------------------

st.subheader("Well Budget (AFE Analysis)")

# -------------------
# ✅ STEP 1: CLEAN AFE PER REPORT
# -------------------
afe_per_report = (
    df.groupby("Report_No")["AFE_Cost_USD"]
    .last()
    .reset_index()
    .sort_values("Report_No")
)

# -------------------
# ✅ STEP 2: DETECT REAL AFE CHANGES
# -------------------
afe_per_report["AFE_Change"] = (
    afe_per_report["AFE_Cost_USD"]
    .round(2)
    .diff()
    .fillna(0) != 0
)

# -------------------
# ✅ STEP 3: TOTAL AFE LOGIC (KEY FIX)
# -------------------
unique_afe_values = afe_per_report["AFE_Cost_USD"].round(2).unique()

if len(unique_afe_values) == 1:
    total_afe = unique_afe_values[0]
else:
    total_afe = unique_afe_values.sum()

# -------------------
# ✅ STEP 4: ACTUAL COST
# -------------------
actual_cost = df["Cumulative_Cost_USD"].max()

# -------------------
# KPI DISPLAY
# -------------------
col1, col2 = st.columns(2)

col1.metric("Total AFE (Approved Budget)", f"${total_afe:,.0f}")
col2.metric("Actual Cost to Date", f"${actual_cost:,.0f}")

# -------------------
# Budget usage %
# -------------------
if total_afe > 0:
    budget_used = (actual_cost / total_afe) * 100
else:
    budget_used = 0

st.progress(min(budget_used / 100, 1.0))
st.write(f"Budget Used: **{budget_used:.1f}%**")

##
st.divider()
##

# -------------------
# ✅ AFE CHANGE DETECTION (CLEAN)
# -------------------
st.subheader("AFE Change Detection")

afe_changes = afe_per_report[afe_per_report["AFE_Change"]]

if afe_changes.empty:
    st.success("No AFE changes detected for this well")
else:
    st.warning(f"{len(afe_changes)} AFE change(s) detected")

    st.dataframe(
        afe_changes.rename(columns={
            "AFE_Cost_USD": "New AFE Value"
        })
    )



###3333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333333


if is_drilling:
    ##
    st.divider()
    ##
    st.subheader("Drilling Sections (Operational)")

    section_summary = df.groupby("Section_ID").agg(
        Reports=("Report_No", "count"),
        Max_Depth=("End_Depth_m", "max"),
        Cost_To_Date=("Cumulative_Cost_USD", "max")
    ).reset_index()

    st.dataframe(section_summary)


##
st.divider()
##
st.subheader("Cost vs AFE Trend")

chart_df = df.copy()

chart_df["AFE_Line"] = chart_df["AFE_Cost_USD"]

st.line_chart(
    chart_df.set_index("Report_Date")[
        ["Cumulative_Cost_USD", "AFE_Line"]
    ]
)

#####################
multi_afe_check = (
    df.groupby("Report_No")["AFE_Cost_USD"]
    .nunique()
    .reset_index(name="AFE_Count")
)

multi_afe_reports = multi_afe_check[multi_afe_check["AFE_Count"] > 1]

if not multi_afe_reports.empty:
    st.warning(f"{len(multi_afe_reports)} report(s) contain multiple AFE values")
###################
##
st.divider()
##

#------------------------
# Cost Spike Detection
#--------------------------
st.subheader("Cost Spike Detection")

cost_threshold = df["Day_Cost_USD"].mean() * 1.5

spikes = df[df["Day_Cost_USD"] > cost_threshold]

if spikes.empty:
    st.success("No abnormal cost spikes detected")
else:
    st.warning("High cost days detected")
    st.dataframe(spikes[["Report_No","Report_Date","Day_Cost_USD"]])



#----------------------------------------
# ROP Performance alert
#-----------------------------------------
if is_drilling:

    ##
    st.divider()
    ##
    st.subheader("ROP Performance Alerts")

    rop_threshold = df["Avg_ROP_mhr"].mean() * 0.5

    slow_days = df[df["Avg_ROP_mhr"] < rop_threshold]

    if slow_days.empty:
        st.success("No abnormal ROP drops detected")
    else:
        st.warning("Low ROP days detected")
        st.dataframe(slow_days[["Report_No","Report_Date","Avg_ROP_mhr"]])



# -------------------
# Drilling Progress
# -------------------
if is_drilling:
    ##
    st.divider()
    ##

    st.subheader("Depth vs Time")

    st.line_chart(df.set_index("Report_Date")["End_Depth_m"])



#---------------------------
# Daily Depth Progress
#----------------------------
if is_drilling:
    ##
    st.divider()
    ##
    st.subheader("Daily Depth Progress")

    st.bar_chart(df.set_index("Report_Date")["Depth_Progress_m"])

##
st.divider()
##

# -------------------
# ROP vs Depth
# -------------------
if is_drilling:
    st.subheader("ROP vs Depth")
    st.line_chart(df.set_index("End_Depth_m")["Avg_ROP_mhr"])

# -------------------
# Cost vs Depth
# -------------------
if is_drilling:
    ##
    st.divider()
    ##

    st.subheader("Cumulative Cost vs Depth")

    st.line_chart(df.set_index("End_Depth_m")["Cumulative_Cost_USD"])


# -------------------
# Daily Cost Trend
# -------------------

st.subheader("Daily Cost Trend")

st.line_chart(df.set_index("Report_Date")["Day_Cost_USD"])


##
st.divider()
##

#--------------------------------------------------
# NPT Trend
#--------------------------------------------------

st.subheader("NPT Trend")

if "NPT_hrs" in df.columns:
    st.bar_chart(df.set_index("Report_Date")["NPT_hrs"])

# -------------------
# Cost per Meter KPI
# -------------------
if is_drilling:
    ##
    st.divider()
    ##

    st.subheader("Cost per Meter")
    df["Cost_per_meter"] = df["Day_Cost_USD"] / df["Depth_Progress_m"].replace(0, pd.NA)
    st.line_chart(df.set_index("Report_Date")["Cost_per_meter"])




#---------------------------
# Best Drilling Day
#-----------------------------
if is_drilling:
    ##
    st.divider()
    ##
    st.subheader("Best Drilling Performance")

    if df["Avg_ROP_mhr"].notna().sum() == 0:

        st.warning("No valid ROP data available")

    else:

        best_idx = df["Avg_ROP_mhr"].idxmax()
        best_day = df.loc[best_idx]

        st.write(
            f"Highest ROP achieved on **Report {best_day['Report_No']}** "
            f"with **{best_day['Avg_ROP_mhr']:.2f} m/hr**"
        )

#---------------------------------------
# Worst Drilling Day
#-------------------------------------
if is_drilling:
    ##
    st.divider()
    ##

    st.subheader("Worst Drilling Performance")

    if df["Avg_ROP_mhr"].notna().sum() == 0:

        st.warning("No valid ROP data available")

    else:

        worst_idx = df["Avg_ROP_mhr"].idxmin()
        worst_day = df.loc[worst_idx]

        st.write(
            f"Lowest ROP recorded on **Report {worst_day['Report_No']}** "
            f"with **{worst_day['Avg_ROP_mhr']:.2f} m/hr**"
        )

#----------------------------------
# Selection Performance Comparison
#---------------------------------------
if is_drilling:
    ##
    st.divider()
    ##

    st.subheader("Average ROP by Hole Section")

    section_perf = df.groupby("Hole_Size_in")["Avg_ROP_mhr"].mean()

    st.bar_chart(section_perf)



#--------------------------------------
# Cost vs ROP Relationship
#---------------------------------------
if is_drilling:
    ##
    st.divider()
    ##
    st.subheader("Cost vs ROP Relationship")

    st.scatter_chart(
        df,
        x="Avg_ROP_mhr",
        y="Cost_per_meter"
    )



#-----------------------------
# Days to Drill Section
#--------------------------------
if is_drilling:
    ##
    st.divider()
    ##
    section_days = df.groupby("Hole_Size_in")["Report_No"].count()

    st.subheader("Days Spent per Hole Section")

    st.bar_chart(section_days)




#-----------------------------------
# Drilling Efficiency Trend
#------------------------------------
if is_drilling and "Efficiency" in df.columns:
    ##
    st.divider()
    ##
    st.subheader("Drilling Efficiency Trend")
    st.line_chart(df.set_index("Report_Date")["Efficiency"])



#-----------------------------------
# Cost Efficient
#-----------------------------------
if is_drilling:
    ##
    st.divider()
    ##
    st.subheader("Cost Efficiency")

    st.line_chart(df.set_index("Report_Date")["Cost_per_meter"])



#-----------------------------------
# ROP Distribution Chart
#-----------------------------------
if is_drilling:
    ##
    st.divider()
    ##
    st.subheader("ROP Distribution")

    st.bar_chart(df["Avg_ROP_mhr"].value_counts().sort_index())



#----------------------------------------
# Cost Vs Depth
#---------------------------------------
if is_drilling:
    ##
    st.divider()
    ##
    st.subheader("Cost vs Depth")

    st.scatter_chart(
        df,
        x="End_Depth_m",
        y="Cost_per_meter"
    )



#--------------------------
# Non Drilling Days
#-----------------------------
if is_drilling:
    ##
    st.divider()
    ##

    flat_days = df[df["Daily_Progress"] == 0]

    st.subheader("Non-Drilling Days")

    if flat_days.empty:
        st.success("No non-drilling days detected")
    else:
        st.warning(f"{len(flat_days)} non-drilling days detected")
        st.dataframe(flat_days[["Report_No", "Report_Date"]])
################################################################################################################
###############################################################################################################
if is_completion:
    ##
    st.divider()
    ##
    st.subheader("Completion Phase Duration")

    phase_duration = (
        df.groupby("Detected_Phase")["Report_No"]
        .count()
        .rename("Days")
        .sort_values(ascending=False)
    )

    st.bar_chart(phase_duration)






if is_completion:
    st.subheader("Cost by Phase")

    phase_cost = (
        df.groupby("Detected_Phase")["Day_Cost_USD"]
        .sum()
        .sort_values(ascending=False)
    )

    st.bar_chart(phase_cost)





if is_completion:
    st.subheader("NPT by Phase")

    npt_phase = (
        df.groupby("Detected_Phase")["NPT_hrs"]
        .sum()
        .sort_values(ascending=False)
    )

    st.bar_chart(npt_phase)




if is_completion:
    st.subheader("Completion Phase Timeline")

    timeline_df = df[["Report_No", "Detected_Phase"]].copy()
    timeline_df["Phase_Code"] = timeline_df["Detected_Phase"].astype("category").cat.codes

    st.line_chart(
        timeline_df.set_index("Report_No")["Phase_Code"]
    )



if is_completion:
    st.subheader("Phase Transitions")

    df["Prev_Phase"] = df["Detected_Phase"].shift()

    transitions = df[df["Detected_Phase"] != df["Prev_Phase"]][
        ["Report_No", "Prev_Phase", "Detected_Phase"]
    ]

    st.dataframe(transitions)


###############################################################################################################
###############################################################################################################

##
st.divider()
##

# ------------------------------------------------------------
# ✅ NEW: NPT ANALYSIS SECTION (Place this before or after KPIs)
# ------------------------------------------------------------
st.divider()
st.subheader("⚠️ Non-Productive Time (NPT) Events")

if df_npt.empty:
    st.success("No whitelisted NPT events recorded for this selection.")
else:
    # Calculate total NPT duration for the selection
    total_npt_hrs = df_npt["Duration"].sum()
    st.warning(f"Total NPT Duration: {total_npt_hrs:.2f} hrs")

    # Display the detailed NPT table
    st.dataframe(
        df_npt[["Report_No", "Report_Date", "NPT_Code", "Start", "End", "Duration", "Description"]],
        width="stretch",
        hide_index=True
    )



##
st.divider()
##

# -------------------
# ✅ NPT BY HOLE SECTION
# -------------------
if is_drilling:
    if not df_npt.empty:
        npt_with_section = df_npt.merge(
            df[["Report_No", "Hole_Size_in"]],
            on="Report_No",
            how="left"
        )

        section_npt = (
            npt_with_section.groupby("Hole_Size_in")["Duration"]
            .sum()
            .sort_values(ascending=False)
        )

        st.subheader("NPT by Hole Section")
        st.bar_chart(section_npt)

##
st.divider()
##

#-------------------------------------
# Top NPT Causes
#------------------------------------

st.subheader("Top NPT Causes")

top_npt = (
    df_npt.groupby("NPT_Code")["Duration"]
    .sum()
    .sort_values(ascending=False)
)

st.bar_chart(top_npt)

##
st.divider()
##

#-----------------------------------------
# Section Performance Table
#------------------------------------------
if is_drilling:
    st.subheader("Hole Section Performance Table")

    section_summary = df.groupby("Hole_Size_in").agg(
        Avg_ROP=("Avg_ROP_mhr","mean"),
        Total_Meters=("End_Depth_m","max"),
        Avg_Cost_per_meter=("Cost_per_meter","mean")
    )

    st.dataframe(section_summary)


##
st.divider()
##


#-------------------------------
# Table View
#------------------------------
#st.subheader(f"{report_type_selected} Data Table")
#st.subheader("Drilling Data Table")
st.subheader(f"{report_type_selected} Data Table")

if is_drilling:
    st.dataframe(df)

else:
    # Keep ONLY relevant completion columns
    dcr_columns = [
        "Well",
        "Report_No",
        "Report_Date",
        "Cumulative_Cost_USD",
        "Day_Cost_USD",
        "NPT_hrs"
    ]

    # Keep only existing columns (safe)
    dcr_columns = [col for col in dcr_columns if col in df.columns]

    st.dataframe(df[dcr_columns])
#st.dataframe(df)

###
st.divider()
###
st.subheader(f"{report_type_selected} Well Comparison")


# -------------------
# Select wells
# -------------------
# Filter master datasets by selected mode
df_all_filtered = df_all[df_all["Report_Type"] == report_type_selected].copy()

if "Report_Type" in df_npt_all.columns:
    df_npt_all_filtered = df_npt_all[df_npt_all["Report_Type"] == report_type_selected].copy()
else:
    df_npt_all_filtered = df_npt_all.copy()

# Now get wells ONLY from selected mode
all_wells = sorted(df_all_filtered["Well"].unique())

selected_wells = st.multiselect(
    "Select Wells to Compare",
    all_wells,
    default=all_wells[:3] if len(all_wells) >= 3 else all_wells
)

if not selected_wells:
    st.warning("Select at least one well")
    st.stop()

# -------------------
# FILTER FULL DATA (NOT df)
# -------------------
df_compare = df_all_filtered[df_all_filtered["Well"].isin(selected_wells)].copy()
df_npt_compare = df_npt_all_filtered[df_npt_all_filtered["Well"].isin(selected_wells)].copy()
#df_compare = df_all[df_all["Well"].isin(selected_wells)].copy()
#df_npt_compare = df_npt_all[df_npt_all["Well"].isin(selected_wells)].copy()

# -------------------
# SAFE NPT SUMMARY
# -------------------
if not df_npt_compare.empty:
    npt_summary = (
        df_npt_compare.groupby("Report_No")["Duration"]
        .sum()
        .reset_index()
        .rename(columns={"Duration": "NPT_hrs"})
    )

    df_compare["Report_No"] = pd.to_numeric(df_compare["Report_No"], errors="coerce")
    npt_summary["Report_No"] = pd.to_numeric(npt_summary["Report_No"], errors="coerce")

    df_compare = df_compare.merge(npt_summary, on="Report_No", how="left")
    df_compare["NPT_hrs"] = df_compare["NPT_hrs"].fillna(0)
else:
    df_compare["NPT_hrs"] = 0

# -------------------
# AGGREGATION (CLEAN + CONSISTENT)
# -------------------
###
# TRUE NPT per well (from raw events)
npt_per_well = (
    df_npt_compare.groupby("Well")["Duration"]
    .sum()
    .reset_index()
    .rename(columns={"Duration": "Total_NPT"})
)
###
comp_summary = df_compare.groupby("Well").agg(
    Total_Depth=("End_Depth_m", "max"),
    Total_Cost=("Cumulative_Cost_USD", "max"),
    Avg_ROP=("Avg_ROP_mhr", "mean")
).reset_index()

if is_completion:
    comp_summary = df_compare.groupby("Well").agg(
        #Total_Depth=("End_Depth_m", "max"),
        Total_Cost=("Cumulative_Cost_USD", "max"),
        #Avg_ROP=("Avg_ROP_mhr", "mean")
    ).reset_index()


    #comp_summary["Avg_ROP"] = 0  # ROP irrelevant in completion

comp_summary = comp_summary.merge(npt_per_well, on="Well", how="left")
comp_summary["Total_NPT"] = comp_summary["Total_NPT"].fillna(0)

# -------------------
# DISPLAY
# -------------------
st.dataframe(comp_summary, width="stretch")

# -------------------
# VISUALS
# -------------------
st.subheader("Cost Comparison")
st.bar_chart(comp_summary.set_index("Well")["Total_Cost"])

if is_drilling:
    if not df.empty:
        st.subheader("ROP Comparison")
        st.bar_chart(comp_summary.set_index("Well")["Avg_ROP"])
    else:
        st.info("No data available to display chart.")

st.subheader("NPT Comparison")
st.bar_chart(comp_summary.set_index("Well")["Total_NPT"])

#############################################################################################################
if is_completion:

    st.divider()
    st.subheader("Phase-Level Performance Analysis")

    # -------------------------
    # FULL DATASET (NOT FILTERED)
    # -------------------------
    df_phase = df_all[df_all["Report_Type"] == "DCR"].copy()

    if "Report_Type" in df_npt_all.columns:
        df_npt_phase = df_npt_all[df_npt_all["Report_Type"] == "DCR"].copy()
    else:
        df_npt_phase = df_npt_all.copy()

    # -------------------------
    # NPT PER REPORT
    # -------------------------q
    if not df_npt_phase.empty:
        npt_per_report = (
            df_npt_phase.groupby(["Well", "Report_No"])["Duration"]
            .sum()
            .reset_index()
            .rename(columns={"Duration": "NPT_hrs"})
        )

        df_phase["Report_No"] = pd.to_numeric(df_phase["Report_No"], errors="coerce")
        npt_per_report["Report_No"] = pd.to_numeric(npt_per_report["Report_No"], errors="coerce")

        df_phase = df_phase.merge(
            npt_per_report,
            on=["Well", "Report_No"],
            how="left"
        )
        df_phase["NPT_hrs"] = df_phase["NPT_hrs"].fillna(0)
        df_phase["Phase_Hours"] = 24
    else:
        df_phase["NPT_hrs"] = 0

    # -------------------------
    # GROUP BY WELL + PHASE
    # -------------------------
    phase_summary = df_phase.groupby(["Well", "Detected_Phase"]).agg(
        Reports=("Report_No", "nunique"),  # fix duplication issue
        Total_Hours=("Phase_Hours", "sum"),
        Total_NPT=("NPT_hrs", "sum"),
        Total_Cost=("Day_Cost_USD", "sum")
    ).reset_index()

    phase_summary["NPT_Intensity"] = (
            phase_summary["Total_NPT"] / phase_summary["Total_Hours"]
    )

    # -------------------------
    # DERIVED METRICS
    # -------------------------
    phase_summary["Avg_NPT_per_Report"] = phase_summary["Total_NPT"] / phase_summary["Reports"]
    phase_summary["Avg_Cost_per_Report"] = phase_summary["Total_Cost"] / phase_summary["Reports"]


    # -------------------------
    # NORMALIZATION FUNCTION
    # -------------------------
    def normalize(series):
        return (series - series.min()) / (series.max() - series.min() + 1e-6)


    # -------------------------
    # SCORE PER PHASE
    # -------------------------
    phase_summary["NPT_Score"] = 1 - normalize(phase_summary["Avg_NPT_per_Report"])
    phase_summary["Cost_Score"] = 1 - normalize(phase_summary["Avg_Cost_per_Report"])

    phase_summary["Phase_Score"] = (
                                           0.6 * phase_summary["NPT_Score"] +
                                           0.4 * phase_summary["Cost_Score"]
                                   ) * 100

    # -------------------------
    # PHASE SELECTOR
    # -------------------------
    phases = sorted(phase_summary["Detected_Phase"].unique())

    selected_phase = st.selectbox("Select Phase", phases)

    phase_filtered = phase_summary[phase_summary["Detected_Phase"] == selected_phase]

    phase_filtered = phase_filtered.sort_values("Phase_Score", ascending=False)

    phase_filtered["Rank"] = range(1, len(phase_filtered) + 1)

    st.dataframe(
        phase_filtered[[
            "Rank",
            "Well",
            "Phase_Score",
            "Reports",
            "Total_NPT",
            "Avg_Cost_per_Report"
        ]],
        #use_container_width=True
        width = "stretch"
    )

    st.subheader(f"{selected_phase} Performance")

    st.bar_chart(
        phase_filtered.set_index("Well")["Phase_Score"]
    )

    best = phase_filtered.iloc[0]
    worst = phase_filtered.iloc[-1]

    st.success(
        f"Best in {selected_phase}: {best['Well']} ({best['Phase_Score']:.1f})"
    )

    st.error(
        f"Worst in {selected_phase}: {worst['Well']} ({worst['Phase_Score']:.1f})"
    )
##
st.divider()
##

#######################################################################3
# --- DDR/DCR ACTIVITY LOG TABLE ---
if is_drilling:
    st.header("📋 Daily Drilling Operations Summary Log")

    # Ensure unique rows for every report processed
    st.dataframe(
        df[[ "Well", "Report_No", "Report_Date", "DCR_Summary_Narrative"]],
        column_config={
            "Report_No": st.column_config.NumberColumn("Rpt #", width="small"),
            "Report_Date": st.column_config.DateColumn("Date"),
            "DCR_Summary_Narrative": st.column_config.TextColumn(
                "Operations Activity",
                width="large"  # Wraps the paragraph for readability
            )
        },
        hide_index=True,
        #use_container_width=True
        width = "stretch"
    )

elif is_completion:
    st.header("📋 Daily Completion Operations Summary Log")

    # Ensure unique rows for every report processed
    st.dataframe(
        df[["Well", "Report_No", "Report_Date", "Detected_Phase", "DCR_Summary_Narrative"]],
        column_config={
            "Report_No": st.column_config.NumberColumn("Rpt #", width="small"),
            "Report_Date": st.column_config.DateColumn("Date"),
            "DCR_Summary_Narrative": st.column_config.TextColumn(
                "Operations Activity",
                width="large"  # Wraps the paragraph for readability
            )
        },
        hide_index=True,
       # use_container_width=True
        width = "stretch"
    )



