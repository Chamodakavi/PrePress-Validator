import streamlit as st
import pandas as pd
from fpdf import FPDF
from PIL import Image
import io
from datetime import datetime
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
    default_data = {
        "machine": ["Narrow Gravure", "Narrow Gravure", "Narrow Gravure", "Narrow Gravure", "Narrow Gravure", "Wider Gravure", "Wider Gravure"],
        "cutbag": [420, 450, 500, 550, 600, 680, 750],
        "cylinder": [470, 500, 550, 600, 650, 730, 800],
        "max_colors": [7, 7, 7, 7, 7, 8, 8],
        "quantity_available": [5, 2, 0, 8, 4, 3, 6]
    }
    df_inv = pd.DataFrame(default_data)
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

# --- SIDEBAR REF ---
st.sidebar.header("📊 Live DB Inventory Stock")
st.sidebar.dataframe(df_inv, hide_index=True)

# --- STEP 1: JOB SPECIFICATIONS ---
st.header("1. Job Specifications")
col1, col2 = st.columns(2)

with col1:
    job_width = st.number_input("Artwork Width (mm)", min_value=0.0, value=0.0, step=1.0, key=f"w_{st.session_state.reset_trigger}")
    job_height = st.number_input("Artwork Height (mm)", min_value=0.0, value=0.0, step=1.0, key=f"h_{st.session_state.reset_trigger}")
    ups = st.number_input("Number of Ups", min_value=1, value=1, step=1, key=f"ups_{st.session_state.reset_trigger}")
    colors = st.number_input("Number of Colors", min_value=0, max_value=8, value=1, step=1, key=f"col_{st.session_state.reset_trigger}")

with col2:
    trim_type = st.selectbox("Trim Type", ["Center Seal", "Bottle Sleeve", "Manual"], key=f"tt_{st.session_state.reset_trigger}")
    if trim_type == "Center Seal":
        trim = st.selectbox("Center Seal Trim (mm)", [10.0, 8.0, 15.0], index=0, key=f"tcs_{st.session_state.reset_trigger}")
    elif trim_type == "Bottle Sleeve":
        trim = 13.0
        st.info("Bottle Sleeve standard trim: 13mm")
    else:
        trim = st.number_input("Manual Trim (mm)", min_value=0.0, value=10.0, step=0.5, key=f"tm_{st.session_state.reset_trigger}")

    repeats_count = st.number_input("Number of Repeats on Cylinder", min_value=1, value=1, step=1, key=f"rep_{st.session_state.reset_trigger}")


# --- STEP 2: MACHINE & CYLINDER SELECTION ---
st.header("2. Machine & Cylinder Selection")
machine = st.radio("Select Gravure Machine", ["Narrow Gravure", "Wider Gravure"], horizontal=True, key=f"mach_{st.session_state.reset_trigger}")

filtered_df = df_inv[df_inv["machine"] == machine]
cutbag_options = filtered_df["cutbag"].tolist()

col3, col4 = st.columns(2)
with col3:
    default_idx = 2 if (machine == "Narrow Gravure" and 500 in cutbag_options) else 0
    cutbag = st.selectbox("Select Cutbag Size (mm)", cutbag_options, index=default_idx, key=f"cb_{st.session_state.reset_trigger}")

selected_row = filtered_df[filtered_df["cutbag"] == cutbag].iloc[0]
cylinder = float(selected_row["cylinder"])

with col4:
    st.metric(label="Automated Cylinder Size", value=f"{cylinder} mm")
    stock_qty = int(selected_row["quantity_available"])
    if stock_qty > 0:
        st.success(f"Stock Status: {stock_qty} Cylinders Available")
    else:
        st.error("Stock Status: OUT OF STOCK ❌")

# --- FORMULA CALCULATIONS ---
total_print_width = (job_width + trim)*2 * ups
calculated_cutbag_val = (job_width + trim) * 2 * ups
formula_passed = calculated_cutbag_val < cutbag
etch_width = total_print_width + 21.0
calculated_repeat_length = job_height * repeats_count

# --- STEP 3: VALIDATION LOGIC ---
st.header("3. Validation Results")
errors = []

if stock_qty <= 0:
    errors.append(f"❌ **Inventory Error:** The chosen {cutbag}mm Cutbag layout configuration is currently **Out of Stock** in the plant storage registry.")

if colors > int(selected_row["max_colors"]):
    errors.append(f"❌ **Color Capacity Error:** The selected configuration exceeds the maximum limit of {selected_row['max_colors']} color stations supported by this cylinder set.")

if not formula_passed:
    errors.append(f"❌ **Formula Failed:** `(Width + Trim) * 2 * Ups` [{calculated_cutbag_val:.1f}mm] must be less than Cutbag [{cutbag}mm].")
if ups >= cutbag:
    errors.append(f"❌ **Ups Error:** Ups ({ups}) must be less than cutbag size ({cutbag}).")
if calculated_repeat_length < 420:
    errors.append(f"❌ **Repeat Error:** Calculated Repeat Layout Length ({calculated_repeat_length:.1f}mm) must be higher than 420mm.")

if machine == "Wider Gravure":
    if job_width > 700:
        errors.append("❌ **Width Error:** Max printing width for Wider Gravure is 700mm.")
    elif job_width == 700 and (cutbag != 750 or cylinder != 800):
        errors.append("❌ **Special Rule:** For 700mm width, Cutbag must be 750 and Cylinder must be 800.")

if machine == "Narrow Gravure":
    if cylinder > 650: errors.append("❌ **Cylinder Error:** Max cylinder size for Narrow Gravure is 650mm.")
    if cutbag > 600: errors.append("❌ **Cutbag Error:** Max cutbag size for Narrow Gravure is 600mm.")
    if job_width == 700: errors.append("❌ **Machine Match Error:** 700mm width requires Wider Gravure.")

if errors:
    for error in errors:
        st.error(error)
else:
    st.success("✅ **All Prepress Specs & Inventory Validated Successfully!**")

# --- STEP 4: SUMMARY ---
st.markdown("---")
st.subheader("Production Summary")

m_col1, m_col2, m_col3, m_col4 = st.columns(4)
m_col1.metric("Etch Width (+21mm)", f"{etch_width:.1f} mm")
m_col2.metric("Selected Cutbag", f"{cutbag} mm")
m_col3.metric("Cylinder Size", f"{cylinder} mm")
m_col4.metric("repeat Height", f"{calculated_repeat_length:.1f} mm")

# --- STEP 5: ARTWORK IMAGE UPLOAD ---
st.header("5. Artwork Attachments")
st.write("Upload or paste images individually. Click the **clear/cross button** on a slot if you need to delete a mistaken file.")

artwork_list = []  # This will now hold PIL Image objects directly
upload_cols = st.columns(2)

for i in range(4):
    target_column = upload_cols[i % 2]
    with target_column:
        slot_file = st.file_uploader(f"Slot {i+1}: Choose or paste artwork", type=["png", "jpg", "jpeg"], key=f"art_slot_{i}_{st.session_state.reset_trigger}")
        if slot_file is not None:
            img = Image.open(slot_file)
            st.image(img, caption=f"Slot {i+1} Active Design", use_container_width=True)
            
            # Convert to RGB mode safely
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # FIX: Append the actual PIL image object, not the bytes
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

    # SECTION 1: Metadata (Includes Materials parameters now)
    current_time_str = datetime.now().strftime("%Y-%m-%d  %I:%M %p")
    pdf.set_font("Arial", style="B", size=11)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(180, 7, txt="1. PROCESSING METADATA", ln=True)
    pdf.ln(1.5)
    draw_table_row("Customer Name", customer_name.strip())
    draw_table_row("Design Description", design_name.strip())
    draw_table_row("Materials Config", materials.strip())
    draw_table_row("Generated Date & Time", current_time_str)
    pdf.ln(6)

    # SECTION 2: Dimensions
    pdf.set_font("Arial", style="B", size=11)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(180, 7, txt="2. INPUT DIMENSIONS & SPECS", ln=True)
    pdf.ln(1.5)
    draw_table_row("Artwork Width", f"{job_width} mm")
    draw_table_row("Artwork Height", f"{job_height} mm")
    draw_table_row("Number of Ups", str(ups))
    draw_table_row("Repeats Configured", f"{repeats_count} Repeat(s)")
    draw_table_row("Calculated Repeat Distance", f"{calculated_repeat_length:.1f} mm")
    draw_table_row("Trim Layout", f"{trim} mm ({trim_type})")
    draw_table_row("Number of Colors", f"{colors} Channels")
    pdf.ln(5)

    # SECTION 3: Equipment Target
    pdf.set_font("Arial", style="B", size=11)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(180, 7, txt="3. EQUIPMENT & LAYOUT TARGET", ln=True)
    pdf.ln(1.5)
    draw_table_row("Selected Machine", machine)
    draw_table_row("Chosen Cutbag Size", f"{cutbag} mm")
    draw_table_row("Cylinder Size", f"{cylinder} mm")
    draw_table_row("Calculated Etch Width", f"{etch_width:.1f} mm", highlight=True)
    pdf.ln(5)

    # SECTION 4: Images
    # SECTION 4: Images (Strict 1 per page rule)
    if artwork_list:
        for idx, img_obj in enumerate(artwork_list):
            pdf.add_page()
            pdf.set_font("Arial", style="B", size=12)
            pdf.set_text_color(44, 62, 80)
            pdf.cell(180, 8, txt=f"ATTACHED DESIGN - COMPONENT {idx + 1}", ln=True)
            pdf.set_draw_color(189, 195, 199)
            pdf.line(10, pdf.get_y() + 1, 200, pdf.get_y() + 1)
            pdf.ln(5)
            
            # FIX: Pass the PIL image object directly to fpdf
            pdf.image(img_obj, x=15, y=pdf.get_y() + 2, w=180)
    return pdf.output()


# --- STEP 6: EXPORT CONTROL ENGINE & GLOBAL RESET ---
st.markdown("---")
st.subheader("Form Management Actions")

action_col1, action_col2 = st.columns(2)

with action_col1:
    # Check if any mandatory structural information parameters are empty strings
    is_fields_empty = not customer_name.strip() or not design_name.strip() or not materials.strip()

    if is_fields_empty:
        st.warning("⚠️ **Prepress Export Locked:** You must enter **Customer Name**, **Design Name**, and **Materials Specification** to compile the document.")
        st.button("Generate & Download Job Sheet PDF", disabled=True, key="dl_btn_disabled")
    elif len(errors) > 0:
        st.error("🛑 **Prepress Export Locked:** Resolve technical validation errors before exporting.")
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
    # Reset button execution block
    st.write("Need to clear out structural measurements for a new job?")
    st.button("🔄 RESET FORM FIELDS", on_click=reset_callback, type="secondary")