def run_pipeline(ddr_folder, progress_bar=None):
    import os
    import pdfplumber
    import pandas as pd
    import re

    records = []
    npt_records = []

    if not os.path.exists(ddr_folder):
        return pd.DataFrame(), pd.DataFrame()

    NPT_WHITELIST = {
        "RIG-CO", "DH-OT", "EX-WOW", "SC-TRS", "SC-TCP",
        "OC-WE", "SC-OCTG", "SC-CM", "DH-FL", "OC-OT",
        "DH-MUDCIRC", "SC-LWD", "SC-WH", "SC-WBCU", "SC-UC", "SC-WFS", "SC-XM"
    }

    files = [f for f in sorted(os.listdir(ddr_folder)) if f.lower().endswith(".pdf")]
    total_files = len(files)

    for i, file in enumerate(files):
        # ✅ UPDATE PROGRESS BAR
        if progress_bar is not None and total_files > 0:
            percent_complete = (i + 1) / total_files
            progress_bar.progress(percent_complete, text=f"Processing {file} ({i + 1}/{total_files})")

        file_path = os.path.join(ddr_folder, file)
        well_name = file.split("_")[0].upper()

        report_number = None
        report_date = None
        end_depth = None
        depth_progress = None
        drilling_hours = None
        avg_rop = None
        hole_size = None
        day_cost = None
        cumulative_cost = None
        afe_cost = None
        lead_digit = None
        dcr_narrative = ""

        report_type = "DDR"



        ####
        with pdfplumber.open(file_path) as pdf:

            # -------------------------
            # ✅ FILE VALIDATION (CRITICAL FIX)
            # -------------------------
            first_page_text = pdf.pages[0].extract_text()

            if not first_page_text:
                continue

            first_page_upper = first_page_text.upper()

            if "DRILLING REPORT" in first_page_upper:
                report_type = "DDR"
            elif "COMPLETION REPORT" in first_page_upper:
                report_type = "DCR"
            else:
                # 🚫 NOT A VALID REPORT → SKIP FILE
                continue
        ####

            ############################################################################

            pattern = re.compile(r"Operations Summary(.*?)(?=Operations at 06:00hrs)", re.DOTALL)
            match = pattern.search(first_page_text)

            if match:
                raw_content = match.group(1).strip()

                # Dynamic Clean: The Supervisor table ends with 'Position' or the last title.

                if "Position" in raw_content:
                    # We take only the part after the 'Position' header of the table
                    raw_content = raw_content.split("Position")[-1].strip()



                # Usually, the paragraph starts with a full sentence (Capital letter)
                clean_match = re.search(r"[A-Z].*", raw_content, re.DOTALL)
                if clean_match:
                    dcr_narrative = clean_match.group(0).strip()
                else:
                    dcr_narrative = raw_content
            else:
                dcr_narrative = "Summary Section Not Found"
            ########################################################################

        #with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue



                # -------------------------
                # HEADERS
                # -------------------------
                if not report_date:
                    m = re.search(r"Report Date:\s*(\d{2}/\d{2}/\d{4})", text)
                    if m:
                        report_date = m.group(1)

                if not report_number:
                    m = re.search(r"Report\s*No[:\s]*(\d+)", text, re.IGNORECASE)
                    if m:
                        report_number = m.group(1)

                # -------------------------
                # NPT EXTRACTION
                # -------------------------
                if "OPERATIONS SUMMARY" in text.upper():
                    parts = re.split(r'00:00\s?[-to]+\s?24:00', text, flags=re.IGNORECASE)

                    if len(parts) >= 2:
                        section = re.split(r'00:00\s?hrs\s?to\s?06:00', parts[1], flags=re.IGNORECASE)[0]
                        lines = section.split('\n')

                        for i, line in enumerate(lines):
                            m = re.search(
                                r'(\d{2}:\d{2})\s+(\d{2}:\d{2})\s+(\d+\.\d{2})\s+([\d,]+\.\d{2})?\s*([A-Z]{3,8})',
                                line
                            )

                            if m:
                                start_t, end_t, dur, depth_val, act_code = m.groups()
                                duration = float(dur)

                                if duration > 0:
                                    words = line.split(act_code)[-1].strip().split()
                                    valid_code = None

                                    if words:
                                        candidate = words[0]

                                        if candidate.endswith("-") and i + 1 < len(lines):
                                            nxt = lines[i + 1].strip().split()
                                            if nxt:
                                                combined = candidate + nxt[0]
                                                if combined in NPT_WHITELIST:
                                                    valid_code = combined

                                        if not valid_code and candidate in NPT_WHITELIST:
                                            valid_code = candidate

                                    if valid_code:
                                        desc = " ".join(words[1:]) if len(words) > 1 else ""

                                        npt_records.append({
                                            "Well": well_name,
                                            "Report_No": int(report_number) if report_number else None,
                                            "Report_Date": report_date,
                                            "Report_Type": report_type,  # ✅ ADD THIS
                                            "Start": start_t,
                                            "End": end_t,
                                            "Duration": duration,
                                            "NPT_Code": valid_code,
                                            "Description": desc
                                        })
                # -------------------------
                # TABLE EXTRACTION
                # -------------------------
                for table in page.extract_tables():

                    for row in table:

                        for cell in row:
                            if not cell:
                                continue

                            cell = str(cell)

                            if "End Depth" in cell:
                                nums = re.findall(r"[\d,]+\.\d+|\d+", cell)
                                if nums:
                                    end_depth = nums[0]

                            if "Progress" in cell:
                                m = re.search(r"\d+\.\d+", cell)
                                if m:
                                    depth_progress = m.group()

                            if "Drilling Hours" in cell:
                                m = re.search(r"\d+\.\d+", cell)
                                if m:
                                    drilling_hours = m.group()

                            if "Avg ROP" in cell:
                                m = re.search(r"\d+\.\d+", cell)
                                if m:
                                    avg_rop = m.group()

                            if "Day Total" in cell:
                                m = re.search(r"[\d,]+", cell)
                                if m:
                                    day_cost = m.group()

                            if "Cumulative Cost" in cell or "Cum Cost" in cell:
                                m = re.search(r"[\d,]+", cell)
                                if m:
                                    cumulative_cost = m.group()

                            if "Total AFE" in cell:
                                m = re.search(r"[\d,]+", cell)
                                if m:
                                    afe_cost = m.group()

                            if "Size (in)" in cell:
                                m = re.search(r"\d+\s+\d+/\d+|\d+", cell)
                                if m:
                                    hole_size = m.group()


        records.append({
            "Well": well_name,
            "Report_No": report_number,
            "Report_Date": report_date,
            "Report_Type": report_type,
            "Hole_Size_in": hole_size,
            "End_Depth_m": end_depth,
            "Depth_Progress_m": depth_progress,
            "Drilling_Hours_hr": drilling_hours,
            "Avg_ROP_mhr": avg_rop,
            "Day_Cost_USD": day_cost,
            "Cumulative_Cost_USD": cumulative_cost,
            "AFE_Cost_USD": afe_cost,
            "DCR_Summary_Narrative": dcr_narrative
        })

    # -------------------------
    # BUILD DATAFRAME
    # -------------------------
    df = pd.DataFrame(records)

    if df.empty:
        return df, pd.DataFrame()

    # -------------------------
    # CLEANING
    # -------------------------
    #df["Report_Date"] = pd.to_datetime(df["Report_Date"], errors="coerce")
    df["Report_Date"] = pd.to_datetime(df["Report_Date"], dayfirst=True, errors="coerce")

    numeric_cols = [
        "End_Depth_m", "Depth_Progress_m", "Drilling_Hours_hr",
        "Avg_ROP_mhr", "Day_Cost_USD", "Cumulative_Cost_USD", "AFE_Cost_USD"
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")

    df = df.dropna(subset=["Report_Date"])
    df["Report_No"] = pd.to_numeric(df["Report_No"], errors="coerce")

    df = df.sort_values(["Well", "Report_No"]).reset_index(drop=True)

    # -------------------------
    # ✅ AFE LOGIC (FIXED)
    # -------------------------
    df["AFE_Cost_USD"] = df["AFE_Cost_USD"].ffill()

    df["AFE_Change"] = df.groupby("Well")["AFE_Cost_USD"].diff().fillna(0)
    df["New_Section"] = abs(df["AFE_Change"]) > 1
    df["Section_ID"] = df.groupby("Well")["New_Section"].cumsum()

    # FINAL AFE PER WELL
    df["Final_AFE_Well"] = df.groupby("Well")["AFE_Cost_USD"].transform("max")

    # -------------------------
    # ✅ CALCULATIONS
    # -------------------------
    df["ROP_calculated"] = df["Depth_Progress_m"] / df["Drilling_Hours_hr"]
    df["Cost_per_meter"] = df["Day_Cost_USD"] / df["Depth_Progress_m"]

    # SAFE DIVISION
    df.loc[df["Drilling_Hours_hr"] == 0, "ROP_calculated"] = None
    df.loc[df["Depth_Progress_m"] == 0, "Cost_per_meter"] = None

    # ✅ EFFICIENCY (IMPORTANT FIX)
    df["Efficiency"] = df["Avg_ROP_mhr"] / df["ROP_calculated"]

    # -------------------------
    # NPT DF
    # -------------------------
    df_npt = pd.DataFrame(npt_records)

    if df_npt.empty:
        df_npt = pd.DataFrame(columns=[
            "Well", "Report_No", "Report_Date",
            "Start", "End", "Duration", "NPT_Code", "Description"
        ])

    # ---------------------------------------------------------
    # ✅ GNPC COMPLETION PHASE DETECTION (V4 - UPDATED LABELS)
    # ---------------------------------------------------------
    PHASES_MAP = [
        "Rig Move, BOP Operations", "Barrier Removal", "Wellbore Cleanup",
        "TCP Shoot and Pull", "Post-Perforation Cleanup", "Completion Installation",
        "Tubing Hanger Installation", "Flowback", "Well Suspension, BOP Pull to surface"
    ]

    MASTER_KEYS = {
        "Barrier Removal": ["gtv", "mechanical plug", "unseated cbp", "retrieval assembly"],
        "Wellbore Cleanup": ["scraper", "wbcu", "cleanup pill", "displace"],
        "TCP Shoot and Pull": ["fired guns", "perforated", "tcp guns", "detonated"],
        "Post-Perforation Cleanup": ["pooh spent", "laid out guns", "safevis", "circulate riser"],
        "Completion Installation": ["lower icv", "middle icv", "upper icv", "control line"],
        "Tubing Hanger Installation": ["cctlf", "sft", "thrt", "landed", "tubing hanger"],
        "Flowback": [
            "slickline pce", "isolation sleeve", "commingle", "well testing",
            "flowing", "performed flowback", "performed flow back", "commingle flow", "cleaned up well",
            "opened middle icv", "opened upper icv"
        ],
        "Well Suspension, BOP Pull to surface": [
            "crown plug", "ta cap", "unlatch bop", "skidded",
            "shut in", "secured well", "deepset gtv", "shallow gtv", "scale inhibition"
        ]
    }

    final_phases = []

    for well, well_df in df.groupby("Well", sort=False):
        current_idx = 0
        bop_confirmed = False

        for _, row in well_df.iterrows():
            report_type = str(row.get("Report_Type", "")).upper()
            narrative = str(row.get("DCR_Summary_Narrative", "")).lower()

            if report_type == "DDR":
                final_phases.append("Drilling Phase")
                continue

            # 1. 🚨 ABSOLUTE END TRIGGER
            if "completions operations ended" in narrative:
                current_idx = PHASES_MAP.index("Well Suspension, BOP Pull to surface")
                final_phases.append(PHASES_MAP[current_idx])
                continue

            # 2. START ANCHOR
            if "pressure tested bop" in narrative or "tested bp" in narrative:
                bop_confirmed = True

            # 3. FORWARD-ONLY SEQUENCE PROGRESSION
            unlock_keys = ["gtv", "scraper", "wbcu", "unseated", "icv", "flow", "commingle"]

            if bop_confirmed or any(k in narrative for k in unlock_keys) or current_idx > 0:

                if current_idx + 1 < len(PHASES_MAP):
                    next_p = PHASES_MAP[current_idx + 1]

                    # --- THE FLOWBACK GUARD ---
                    is_actively_flowing = any(
                        k in narrative for k in ["commingle", "performed flowback", "flowing"])
                    is_suspension_key = any(
                        k in narrative for k in MASTER_KEYS["Well Suspension, BOP Pull to surface"])

                    if next_p == "Well Suspension, BOP Pull to surface":
                        if is_suspension_key and not is_actively_flowing:
                            current_idx += 1
                    elif any(key in narrative for key in MASTER_KEYS.get(next_p, [])):
                        current_idx += 1

                final_phases.append(PHASES_MAP[current_idx])
            else:
                # Returns the first phase in the list automatically
                final_phases.append(PHASES_MAP[0])

    df["Detected_Phase"] = final_phases
    return df, df_npt