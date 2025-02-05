import streamlit as st
import pandas as pd
from datetime import datetime
import os
from openai import OpenAI
from dotenv import load_dotenv


default_names = ['Emir Sevim', "Enis Sevim"]

# Set page config for wider layout and better title
st.set_page_config(
    page_title="Warehouse Inventory Tracker",
    page_icon="📦",
    layout="wide"
)

CSV_FILE = "warehouse_inventory.csv"

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stButton>button {
        width: 100%;
    }
    .reportview-container .main .block-container {
        padding-top: 2rem;
    }
    div[data-testid="stForm"] {
        border: 1px solid #ddd;
        padding: 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Load environment variables
load_dotenv()

# Verify OpenAI API key is available
if not os.getenv("OPENAI_API_KEY"):
    st.error("Please set your OPENAI_API_KEY environment variable")
    st.stop()  # Stop execution if API key is missing

# Add OpenAI client initialization with API key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def initialize_csv():
    """
    Create the CSV file with default headers if it doesn't exist.
    """
    if not os.path.exists(CSV_FILE):
        df = pd.DataFrame(
            columns=["SKU", "Notes", "Inventory Level", "Updated By", "Updated On"])
        df.to_csv(CSV_FILE, index=False)


# Ensure CSV file exists on startup
initialize_csv()


def load_data():
    df = pd.read_csv(CSV_FILE)
    # Convert 'Updated On' column to datetime
    df['Updated On'] = pd.to_datetime(df['Updated On'])
    return df


def update_csv(sku, new_notes, updated_by, inventory_level):
    # Load current data
    df = pd.read_csv(CSV_FILE)
    updated_on = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if sku in df["SKU"].values:
        # Update the existing SKU
        idx = df.index[df["SKU"] == sku][0]
        df.at[idx, "Notes"] = new_notes
        df.at[idx, "Inventory Level"] = inventory_level
        df.at[idx, "Updated By"] = updated_by
        df.at[idx, "Updated On"] = updated_on
    else:
        # Append a new row if the SKU does not exist
        new_row = {
            "SKU": sku,
            "Notes": new_notes,
            "Inventory Level": inventory_level,
            "Updated By": updated_by,
            "Updated On": updated_on
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # Save the updated DataFrame to the CSV file
    df.to_csv(CSV_FILE, index=False)
    return True


# Add function to enhance notes using GPT-4
def enhance_notes(original_notes):
    """Use GPT-4 to enhance and clarify notes."""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that helps to corect grammar. Do not include any other information in the response other than the corrected notes."},
                {"role": "user", "content": f"{original_notes}"}
            ],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error enhancing notes: {str(e)}")
        return original_notes


def main():
    # Header with icon
    st.markdown("# 📦 Warehouse Inventory Tracking")
    st.markdown("---")

    # Create two columns for main layout
    col1, col2 = st.columns([2, 1])

    with col2:
        st.markdown("### 🔍 Search & Filters")
        with st.expander("Search Options", expanded=True):
            global_search = st.text_input("🔎 Global Search")
            sku_filter = st.text_input("Filter by SKU")
            notes_filter = st.text_input("Filter by Notes")
            updated_by_filter = st.text_input("Filter by Updated By")

        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()

        # Entry management section
        st.markdown("### ✏️ Manage Inventory")

        # Tab selection for Add/Update
        tab1, tab2 = st.tabs(["Update Existing", "Add New"])

        # Get current SKUs for dropdown
        current_skus = load_data()['SKU'].tolist()

        with tab1:
            # Move selection outside the form
            selected_sku = st.selectbox(
                "Select SKU to Update",
                options=current_skus,
                index=None,
                placeholder="Choose SKU..."
            )

            # Get current data for the selected SKU
            current_notes = ""
            current_updated_by = ""
            current_inventory_level = "Full"  # Default value
            if selected_sku:
                current_row = load_data().loc[load_data()[
                    'SKU'] == selected_sku].iloc[0]
                current_notes = current_row['Notes']
                current_updated_by = current_row['Updated By']
                current_inventory_level = current_row['Inventory Level']

            with st.form("update_form"):
                new_notes = st.text_area("Update Notes", value=current_notes)
                inventory_level = st.selectbox(
                    "Inventory Level",
                    options=["Full", "Low", "Out"],
                    index=["Full", "Low", "Out"].index(
                        current_inventory_level) if current_inventory_level in ["Full", "Low", "Out"] else 0
                )
                updated_by = st.selectbox(
                    "Your Name",
                    options=default_names,
                    index=default_names.index(
                        current_updated_by) if current_updated_by in default_names else 0
                )

                # Add checkbox for AI enhancement
                enhance_with_ai = st.checkbox(
                    "✨ Enhance notes with AI before submitting")
                submitted_update = st.form_submit_button("📝 Update Entry")

                if submitted_update:
                    if selected_sku and new_notes and updated_by:
                        if enhance_with_ai:
                            with st.spinner("Enhancing notes with AI..."):
                                new_notes = enhance_notes(new_notes)
                        success = update_csv(
                            selected_sku, new_notes, updated_by, inventory_level)
                        if success:
                            st.success(
                                f"✅ SKU '{selected_sku}' updated successfully!")
                            st.rerun()
                    else:
                        st.error("❌ Please fill in all fields.")

        with tab2:
            with st.form("add_form"):
                new_sku = st.text_input("New SKU Code")
                # Warn if SKU already exists
                if new_sku in current_skus:
                    st.warning(
                        "⚠️ This SKU already exists. Please use the Update tab instead.")
                new_notes = st.text_area("Notes")
                inventory_level = st.selectbox(
                    "Inventory Level",
                    options=["Full", "Low", "Out"],
                    key="add_form_inventory"
                )

                # Add checkbox for AI enhancement
                enhance_with_ai = st.checkbox(
                    "✨ Enhance notes with AI before submitting")
                updated_by = st.selectbox(
                    "Your Name",
                    options=default_names,
                    key="add_form_name"
                )
                submitted_new = st.form_submit_button("➕ Add New Entry")

                if submitted_new:
                    if new_sku and new_notes and updated_by:
                        if new_sku in current_skus:
                            st.error(
                                "❌ This SKU already exists. Please use the Update tab.")
                        else:
                            if enhance_with_ai:
                                with st.spinner("Enhancing notes with AI..."):
                                    new_notes = enhance_notes(new_notes)
                            success = update_csv(
                                new_sku, new_notes, updated_by, inventory_level)
                            if success:
                                st.success(
                                    f"✅ New SKU '{new_sku}' added successfully!")
                                st.rerun()
                    else:
                        st.error("❌ Please fill in all fields.")

    with col1:
        # Load and filter data
        df = load_data()

        # Apply filters
        if global_search:
            df = df[df.apply(lambda row: row.astype(str).str.contains(
                global_search, case=False).any(), axis=1)]
        if sku_filter:
            df = df[df["SKU"].astype(str).str.contains(sku_filter, case=False)]
        if notes_filter:
            df = df[df["Notes"].astype(str).str.contains(
                notes_filter, case=False)]
        if updated_by_filter:
            df = df[df["Updated By"].astype(str).str.contains(
                updated_by_filter, case=False)]

        # Display inventory table
        st.markdown("### 📋 Inventory Overview")
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            height=300,
            column_config={
                "SKU": st.column_config.TextColumn("SKU", width="medium"),
                "Notes": st.column_config.TextColumn("Notes", width="large"),
                "Inventory Level": st.column_config.SelectboxColumn(
                    "Inventory Level",
                    options=["Full", "Low", "Out"],
                    width="small"
                ),
                "Updated By": st.column_config.SelectboxColumn(
                    "Updated By",
                    options=default_names,
                    width="medium"
                ),
                "Updated On": st.column_config.DatetimeColumn(
                    "Updated On",
                    width="medium",
                    format="DD/MM/YYYY HH:mm",
                    disabled=True  # Make this column read-only
                )
            },
            num_rows="dynamic"
        )

        # If the dataframe was edited, update the CSV
        if not df.equals(edited_df):
            # Convert datetime back to string before saving
            edited_df['Updated On'] = edited_df['Updated On'].dt.strftime(
                '%Y-%m-%d %H:%M:%S')
            edited_df.to_csv(CSV_FILE, index=False)
            st.rerun()

        # Display detailed notes
        st.markdown("### 📝 Detailed Notes")
        for idx, row in df.iterrows():
            with st.expander(f"SKU: {row['SKU']}", expanded=False):
                inventory_color = {
                    "Full": "green",
                    "Low": "orange",
                    "Out": "red"
                }.get(row['Inventory Level'], "grey")

                st.markdown(f"""
                    **Notes:** {row['Notes']}  
                    **Inventory Level:** :{inventory_color}[{row['Inventory Level']}]  
                    **Last Updated By:** {row['Updated By']}  
                    **Last Updated:** {row['Updated On']}
                """)


if __name__ == "__main__":
    main()
