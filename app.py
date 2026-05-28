import streamlit as st
import pandas as pd
from fpdf import FPDF
from PIL import Image
import io
from datetime import datetime
from zoneinfo import ZoneInfo
import os

# Set up page config
st.set_page_config(page_title="Prepress Cylinder Validator & PDF Generator", layout="centered")

st.title("🖨️ Prepress Cylinder Validator & PDF Exporter")
st.write("Input job specifications, validate constraints against live inventory, upload artwork, and generate a print-ready job sheet PDF.")

# --- INITIALIZE SESSION STATE FOR CLEAN FORM RESETTING ---
if "reset_trigger" not in st.session_state:
    st.session_state.reset_trigger = 0

def reset_callback():
    st.session_state.reset_trigger += 1

# --- DATABASE / INVENTORY LOADING ---
csv_filename = "inventory.csv"
if not os.path.exists(csv_filename):
    machines = [
        "Narrow Gravure", "Narrow Gravure", "Narrow Gravure", "Narrow Gravure", "Narrow Gravure", 
        "Wider Gravure", "Wider Gravure",
        "New Flexo", "New Flexo", "New Flexo", "New Flexo", "New Flexo", "New Flexo", 
        "New Flexo", "New Flexo", "New Flexo", "New Flexo", "New Flexo", "New Flexo", "New Flexo",
        "JK Flexo", "JK Flexo", "JK Flexo", "JK Flexo", "JK Flexo", "JK Flexo",
        "JK Flexo", "JK Flexo", "JK Flexo", "JK Flexo", "JK Flexo", "JK Flexo", "JK Flexo"
    ]
    cutbags = [
        420, 450, 500, 550, 600, 
        680, 750, 
        300, 320, 340, 350, 360, 370, 380, 400, 420, 450, 460, 500, 520,
        300, 320, 340, 360, 380, 400, 430, 450, 460, 500, 550, 570, 580
    ]
    cylinders = list(cutbags)
    for idx in range(5):
        cylinders[idx] = cutbags[idx] + 50
    cylinders[5] = 730
    cylinders[6] = 800

    max_colors = [
        7, 7, 7, 7, 7, 
        8, 8, 
        8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
        6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6
    ]
    quantities = [
        5, 2, 0, 8, 4, 
        3, 6, 
        12, 4, 6, 2, 8, 5, 7, 9, 11, 4, 6, 3, 7,
        8, 5, 6, 9, 4, 7, 3, 5, 8, 4, 6, 2, 5
    ]

    hyplass_rollers = [
        260.35, 279.4, 311.15, 330.2, 361.95, 381.0, 406.4, 412.75, 463.55, 
        514.35, 539.75, 558.8, 571.5, 615.95, 641.35, 711.2, 812.8, 762.0, 914.4
    ]
    
    for r_val in hyplass_rollers:
        machines.append("Hyplass")
        cutbags.append(r_val)
        cylinders.append(r_val)
        max_colors.append(8)
        quantities.append(6)

    df_inv = pd.DataFrame({
        "machine": machines,
        "cutbag": cutbags,
        "cylinder": cylinders,
        "max_colors": max_colors,
        "quantity_available": quantities
    })
    df_inv.to_csv(csv_filename, index=False)
else:
    df_inv = pd.read_csv(csv_filename)

# --- TOP INPUT FIELDS ---
st.header("Job Identifiers")
top_col1, top_col2 = st.columns(2)
with top_col1:
    customer_name = st.text_input("Customer Name", placeholder="e.g., Brand Name Ltd", key=f"cust_{st.session_state.reset_trigger}")
with top_col2:
    design_name = st.text_input("Design Name", placeholder="e.g., Mango Juice 500ml Label", key=f"dsgn_{st.session_state.reset_trigger}")

materials = st.text_input("Materials Specification", placeholder="e.g., BOPP 20mic / White LDPE 35mic", key=f"mat_{st.session_state.reset_trigger}")


# --- STEP 1: JOB SPECIFICATIONS & UNIT TOGGLING ---
st.markdown("---")
st.header("1. Job Specifications")

use_inches = st.checkbox("⚙️ Input measurements in Inches instead of mm", key=f"unit_{st.session_state.reset_trigger}")
unit_lbl = "inches" if use_inches else "mm"

col1, col2 = st.columns(2)

with col1:
    input_width = st.number_input(f"Artwork Width ({unit_lbl})", min_value=0.0, value=0.0, step=0.1 if use_inches else 1.0, key=f"w_{st.session_state.reset_trigger}")
    input_height = st.number_input(f"Artwork Height ({unit_lbl})", min_value=0.0, value=0.0, step=0.1 if use_inches else 1.0, key=f"h_{st.session_state.reset_trigger}")
    ups = st.number_input("Number of Ups", min_value=1, value=1, step=1, key=f"ups_{st.session_state.reset_trigger}")
    colors = st.number_input("Number of Colors", min_value=0, max_value=8, value=1, step=1, key=f"col_{st.session_state.reset_trigger}")

with col2:
    trim_type = st.selectbox("Trim Type", ["Center Seal", "Bottle Sleeve", "Reel", "Stand Up Pouch", "Manual"], key=f"tt_{st.session_state.reset_trigger}")
    
    input_gusset = 0.0
    if trim_type == "Stand Up Pouch":
        input_gusset = st.number_input(f"Gusset Width ({unit_lbl})", min_value=0.0, value=0.0, step=0.1 if use_inches else 1.0, key=f"gus_{st.session_state.reset_trigger}")
        trim = 0.0
    elif trim_type == "Center Seal":
        if use_inches:
            trim_choice = st.selectbox("Center Seal Trim (inches)", [0.39, 0.31, 0.59], index=0, key=f"tcs_{st.session_state.reset_trigger}")
            trim = trim_choice * 25.4
        else:
            trim = st.selectbox("Center Seal Trim (mm)", [10.0, 8.0, 15.0], index=0, key=f"tcs_{st.session_state.reset_trigger}")
    elif trim_type == "Bottle Sleeve":
        trim = 13.0
        st.info("Bottle Sleeve standard trim: 13mm (0.51 inches)")
    elif trim_type == "Reel":
        trim = 0.0
        st.info("Reel standard trim: 0mm (Flat-web processing enabled)")
    else:
        if use_inches:
            manual_input_trim = st.number_input("Manual Trim (inches)", min_value=0.0, value=0.39, step=0.05, key=f"tm_{st.session_state.reset_trigger}")
            trim = manual_input_trim * 25.4
        else:
            trim = st.number_input("Manual Trim (mm)", min_value=0.0, value=10.0, step=0.5, key=f"tm_{st.session_state.reset_trigger}")

    repeats_count = st.number_input("Number of Repeats on Cylinder/Roller", min_value=1, value=1, step=1, key=f"rep_{st.session_state.reset_trigger}")

# PRINTING SIDE RADIO SELECTOR
print_side = st.radio(
    "Select Printing Side", 
    options=["Reverse", "Surface"], 
    index=None, 
    horizontal=True, 
    key=f"side_{st.session_state.reset_trigger}"
)

# --- INTERNAL INTERPOLATION / UNIT NORMALIZATION ---
if use_inches:
    job_width = input_width * 25.4
    job_height = input_height * 25.4
    gusset_width = input_gusset * 25.4
else:
    job_width = input_width
    job_height = input_height
    gusset_width = input_gusset


# --- STEP 2: MACHINE & EQUIPMENT ALLOCATION ---
st.header("2. Machine & Equipment Allocation")
machine = st.radio("Select Printing Machine", ["Narrow Gravure", "Wider Gravure", "New Flexo", "JK Flexo", "Hyplass"], horizontal=True, key=f"mach_{st.session_state.reset_trigger}")

filtered_df = df_inv[df_inv["machine"] == machine]
tool_options = filtered_df["cutbag"].tolist()

col3, col4 = st.columns(2)
with col3:
    if machine in ["New Flexo", "JK Flexo", "Hyplass"]:
        formatted_options = []
        for val in tool_options:
            inch_calc = val / 25.4
            formatted_options.append(f"{val} mm ({inch_calc:.2f} in)")
            
        selected_display = st.selectbox("Select Roller Size", formatted_options, index=0, key=f"cb_{st.session_state.reset_trigger}")
        selected_tool_size = float(selected_display.split(" ")[0])
    else:
        default_idx = 2 if (machine == "Narrow Gravure" and 500 in tool_options) else 0
        selected_tool_size = st.selectbox("Select Cutbag Size (mm)", tool_options, index=default_idx, key=f"cb_{st.session_state.reset_trigger}")

selected_row = filtered_df[filtered_df["cutbag"] == selected_tool_size].iloc[0]
stock_qty = int(selected_row["quantity_available"])

# --- CORE MATH PRODUCTION FORMULAS WITH UPDATED SUP LOGIC ---
if trim_type == "Stand Up Pouch":
    # Flipped structural logic: Input width used for repeat length, input height used for width logic
    calc_width_factor = job_height
    calc_height_factor = job_width
    
    # NEW FORMULA: Design Width = Height + (Gusset Width / 2) + 15
    sup_design_width = (calc_width_factor * 2) + (gusset_width / 2.0) + 15.0
    base_print_width = sup_design_width * ups
    calculated_repeat_length = calc_height_factor * repeats_count
elif trim_type == "Bottle Sleeve":
    base_print_width = ((job_width * 2) + 13.0) * ups
    calculated_repeat_length = job_height * repeats_count
elif trim_type == "Reel":
    base_print_width = (job_width + trim) * ups
    calculated_repeat_length = job_height * repeats_count
else:
    calculated_repeat_length = job_height * repeats_count
    if machine in ["New Flexo", "JK Flexo", "Hyplass"]:
        base_print_width = (job_width + trim) * ups
    else:
        base_print_width = (job_width + trim) * 2 * ups

# Adjust dynamic targets based on printing technology choice
if machine in ["New Flexo", "JK Flexo", "Hyplass"]:
    # Flexo margins add +19mm dot space directly onto the calculated layout total width
    etch_width = base_print_width + 19.0
    width_check_val = etch_width
    tooling_target_label = "Selected Roller Size"
else:
    # Gravure margins add +21mm etch clearance directly onto the calculated layout total width
    etch_width = base_print_width + 21.0
    width_check_val = base_print_width
    tooling_target_label = "Selected Cutbag Size"

cylinder_or_roller_size = float(selected_row["cylinder"])

with col4:
    if machine in ["New Flexo", "JK Flexo", "Hyplass"]:
        st.metric(label="Assigned Flexo Roller Size", value=f"{cylinder_or_roller_size} mm", delta=f"{cylinder_or_roller_size / 25.4:.2f} inches")
    else:
        st.metric(label="Automated Cylinder Size", value=f"{cylinder_or_roller_size} mm")
        
    if stock_qty > 0:
        st.success(f"Stock Status: {stock_qty} Units Available")
    else:
        st.error("Stock Status: OUT OF STOCK ❌")


# --- STEP 3: VALIDATION LOGIC ---
st.header("3. Validation Results")
errors = []

# Stock & Color Capacity Validation
if stock_qty <= 0:
    errors.append(f"❌ **Inventory Error:** The chosen tooling dimension [{selected_tool_size}mm] is currently **Out of Stock**.")

if colors > int(selected_row["max_colors"]):
    errors.append(f"❌ **Color Capacity Error:** The requested design requires {colors} colors. {machine} limits production to a maximum of {selected_row['max_colors']} color channels.")

# Specialized Stand Up Pouch Size Matrix Validation Check
if trim_type == "Stand Up Pouch":
    valid_pouch_combos = [(65, 40), (100, 60), (125, 70), (140, 70), (175, 90)]
    current_combo = (int(round(job_width)), int(round(gusset_width)))
    
    if current_combo not in valid_pouch_combos:
        errors.append(f"❌ **SUP Configuration Mismatch:** Entered Width [{current_combo[0]}mm] and Gusset [{current_combo[1]}mm] do not match standard factory limits. Valid pairs are: (65-40), (100-60), (125-70), (140-70), (175-90).")

# Machine Math Rule Verifications
if machine in ["New Flexo", "JK Flexo", "Hyplass"]:
    if width_check_val >= 550.0:
        errors.append(f"❌ **Flexo Width Error:** Calculated layout tracking value (Print Width + 19mm Dot/Box) [{width_check_val:.1f}mm] must be strictly less than 550mm.")
    
    if abs(calculated_repeat_length - cylinder_or_roller_size) > 0.01:
        errors.append(f"❌ **Flexo Gear Step Mismatch:** Target roller circumference [{cylinder_or_roller_size}mm] does not match your layout dimensions [{calculated_repeat_length:.2f}mm].")
else:
    if width_check_val >= selected_tool_size:
        errors.append(f"❌ **Formula Failed:** Layout requirements [{width_check_val:.1f}mm] must be strictly less than your chosen Cutbag [{selected_tool_size}mm].")
    if ups >= selected_tool_size:
        errors.append(f"❌ **Ups Error:** Ups ({ups}) must be less than cutbag size ({selected_tool_size}).")
    if calculated_repeat_length < 420:
        errors.append(f"❌ **Repeat Error:** Calculated Repeat Layout Length ({calculated_repeat_length:.1f}mm) must be higher than 420mm.")

    if machine == "Wider Gravure":
        if job_width > 700:
            errors.append("❌ **Width Error:** Max printing width for Wider Gravure is 700mm.")
        elif job_width == 700 and (selected_tool_size != 750 or cylinder_or_roller_size != 800):
            errors.append("❌ **Special Rule:** For 700mm width, Cutbag must be 750 and Cylinder must be 800.")

    if machine == "Narrow Gravure":
        if cylinder_or_roller_size > 650: errors.append("❌ **Cylinder Error:** Max cylinder size for Narrow Gravure is 650mm.")
        if selected_tool_size > 600: errors.append("❌ **Cutbag Error:** Max cutbag size for Narrow Gravure is 600mm.")
        if job_width == 700: errors.append("❌ **Machine Match Error:** 700mm width requires Wider Gravure.")

if errors:
    for error in errors:
        st.error(error)
else:
    st.success(f"✅ **All Prepress Specs & Technical Tooling Requirements for {machine} Passed Inspection!**")


# --- STEP 4: SUMMARY ---
st.markdown("---")
st.subheader("Production Summary (Standard mm Targets)")

m_col1, m_col2, m_col3, m_col4 = st.columns(4)
m_col1.metric("Etch/Printing Width", f"{etch_width:.1f} mm")
m_col2.metric(tooling_target_label, f"{selected_tool_size:.1f} mm")
m_col3.metric("Cylinder/Roller Size", f"{cylinder_or_roller_size:.1f} mm")
m_col4.metric("Repeat Layout Height", f"{calculated_repeat_length:.1f} mm")

# --- SIDEBAR REF ---
st.sidebar.markdown("---")
st.sidebar.header("📊 Live DB Inventory Stock")
st.sidebar.dataframe(df_inv, hide_index=True)


# --- STEP 5: ARTWORK IMAGE UPLOAD ---
st.header("5. Artwork Attachments")
st.write("Upload or paste images individually. Click the **clear/cross button** on a slot if you need to delete a mistaken file.")

artwork_list = []
upload_cols = st.columns(2)

for i in range(4):
    target_column = upload_cols[i % 2]
    with target_column:
        slot_file = st.file_uploader(f"Slot {i+1}: Choose or paste artwork", type=["png", "jpg", "jpeg"], key=f"art_slot_{i}_{st.session_state.reset_trigger}")
        if slot_file is not None:
            img = Image.open(slot_file)
            st.image(img, caption=f"Slot {i+1} Active Design", use_container_width=True)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            artwork_list.append(img)


# FPDF2 Generator Function
def generate_fpdf2_report():
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Arial", style="B", size=18)
    
    pdf.cell(180, 12, txt="Prepress Job Specification Sheet", ln=True, align="L")
    pdf.set_draw_color(44, 62, 80)
    pdf.set_line_width(0.8)
    pdf.line(10, 24, 200, 24)
    pdf.ln(6)
    
    def draw_table_row(label, val, highlight=False):
        pdf.set_font("Arial", style="B", size=10)
        if highlight:
            pdf.set_fill_color(232, 244, 248)
            pdf.set_text_color(41, 128, 185)
        else:
            pdf.set_fill_color(248, 249, 250)
            pdf.set_text_color(44, 62, 80)
            
        pdf.cell(70, 8.5, txt=f"  {label}", border=1, fill=True)
        pdf.set_font("Arial", style="", size=10)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(110, 8.5, txt=f"  {val}", border=1, ln=True)

    # SECTION 1: Metadata
    local_tz = ZoneInfo("Asia/Colombo")
    current_time_str = datetime.now(local_tz).strftime("%Y-%m-%d  %I:%M %p")
    pdf.set_font("Arial", style="B", size=11)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(180, 7, txt="1. PROCESSING METADATA", ln=True)
    pdf.ln(1.5)
    draw_table_row("Customer Name", customer_name.strip())
    draw_table_row("Design Description", design_name.strip())
    draw_table_row("Materials Config", materials.strip())
    draw_table_row("Printing Side", print_side)
    draw_table_row("Generated Date & Time", current_time_str)
    pdf.ln(6)

    # SECTION 2: Dimensions
    pdf.set_font("Arial", style="B", size=11)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(180, 7, txt="2. INPUT DIMENSIONS & SPECS", ln=True)
    pdf.ln(1.5)
    draw_table_row("Artwork Width", f"{job_width:.2f} mm ({job_width / 25.4:.2f} in)")
    draw_table_row("Artwork Height", f"{job_height:.2f} mm ({job_height / 25.4:.2f} in)")
    
    draw_table_row("Number of Ups", str(ups))
    draw_table_row("Repeats Configured", f"{repeats_count} Repeat(s)")
    draw_table_row("Calculated Repeat Distance", f"{calculated_repeat_length:.2f} mm")
    draw_table_row("Trim Layout", f"{trim:.2f} mm ({trim_type})")
    draw_table_row("Number of Colors", f"{colors} Channels")
    pdf.ln(5)

    # SECTION 3: Equipment Target
    pdf.set_font("Arial", style="B", size=11)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(180, 7, txt="3. EQUIPMENT & LAYOUT TARGET", ln=True)
    pdf.ln(1.5)
    draw_table_row("Selected Machine", machine)
    if machine in ["New Flexo", "JK Flexo", "Hyplass"]:
        draw_table_row("Target Roller Selection", f"{selected_tool_size:.2f} mm ({selected_tool_size / 25.4:.2f} in)")
        draw_table_row("Calculated Flexo Print Width (+19mm)", f"{etch_width:.2f} mm", highlight=True)
    else:
        draw_table_row("Chosen Cutbag Size", f"{selected_tool_size:.2f} mm")
        draw_table_row("Calculated Etch Width (+21mm)", f"{etch_width:.2f} mm", highlight=True)
    if trim_type == "Stand Up Pouch":
        draw_table_row("Bottom Gusset Width", f"{gusset_width:.2f} mm ({gusset_width / 25.4:.2f} in)")
        draw_table_row("Computed SUP Design Width", f"{sup_design_width:.2f} mm")
    draw_table_row("Tooling Size (Cylinder/Roller)", f"{cylinder_or_roller_size:.2f} mm")
    pdf.ln(5)

    # SECTION 4: Images
    if artwork_list:
        for idx, img_obj in enumerate(artwork_list):
            pdf.add_page()
            pdf.set_font("Arial", style="B", size=12)
            pdf.set_text_color(44, 62, 80)
            pdf.cell(180, 8, txt=f"ATTACHED DESIGN - COMPONENT {idx + 1}", ln=True)
            pdf.set_draw_color(189, 195, 199)
            pdf.line(10, pdf.get_y() + 1, 200, pdf.get_y() + 1)
            pdf.ln(5)
            pdf.image(img_obj, x=15, y=pdf.get_y() + 2, w=180)
    return pdf.output()


# --- STEP 6: EXPORT CONTROL ENGINE & GLOBAL RESET ---
st.markdown("---")
st.subheader("Form Management Actions")
action_col1, action_col2 = st.columns(2)

with action_col1:
    is_fields_empty = not customer_name.strip() or not design_name.strip() or not materials.strip() or print_side is None

    if print_side is None:
        st.warning("⚠️ **Prepress Export Locked:** You must select a **Printing Side** (Reverse or Surface) to enable download operations.")
        st.button("Generate & Download Job Sheet PDF", disabled=True, key="dl_btn_side_missing")
    elif is_fields_empty:
        st.warning("⚠️ **Prepress Export Locked:** You must enter **Customer Name**, **Design Name**, and **Materials Specification** to compile the document.")
        st.button("Generate & Download Job Sheet PDF", disabled=True, key="dl_btn_disabled")
    elif len(errors) > 0:
        st.error("🛑 **Prepress Export Locked:** Fix the validation or inventory errors shown above before downloading the job sheet.")
        st.button("Generate & Download Job Sheet PDF", disabled=True, key="dl_btn_error")
    else:
        if st.button("Generate & Download Job Sheet PDF", key="dl_btn_active"):
            with st.spinner("Compiling structural production sheets..."):
                try:
                    pdf_data = generate_fpdf2_report()
                    pdf_bytes = bytes(pdf_data)
                    
                    safe_customer = "".join(x for x in customer_name if x.isalnum() or x in "._- ").strip().replace(" ", "_")
                    safe_design = "".join(x for x in design_name if x.isalnum() or x in "._- ").strip().replace(" ", "_")
                    final_filename = f"{safe_customer}_{safe_design}_job_sheet.pdf"
                    
                    st.download_button(
                        label="📥 Click Here to Download PDF",
                        data=pdf_bytes,
                        file_name=final_filename,
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Failed to compile layout output: {e}")

with action_col2:
    st.write("Need to clear out structural measurements for a new job?")
    st.button("🔄 RESET FORM FIELDS", on_click=reset_callback, type="secondary")