# read.py  
  
import streamlit as st  
from svc_db import count_records, fetch_records, update_field
from svc_blob import fetch_json
from streamlit_helper import plot_curves
from curve_helper import CurveHelper


def display_records(records, table_name, num_columns=1, thumbnail_width=640):
    columns = st.columns(num_columns)
    
    for idx, record in enumerate(records):
        col = columns[idx % num_columns]
        with col:
            st.write(f"**UUID:** {record['uuid']}")
            thumbnail_url = record.get('thumbnail_url')
            if thumbnail_url:
                st.image(thumbnail_url, caption=record.get('name', 'N/A'), width=thumbnail_width)

            # Initialize name_options
            name_options = [name.strip() for name in record.get('name', '').split(',')] if record.get('name') else []

            # Generate a unique key for each record
            record_key = f"{record['uuid']}_{idx}"
            
            if len(name_options) > 1:
                st.write(f"**Description:** {record.get('description', 'N/A')}")
                st.write("**Name Options:**")
                
                # Define maximum number of columns per row
                max_cols = 3
                for i in range(0, len(name_options), max_cols):
                    # Get the current batch of name_options
                    batch = name_options[i:i + max_cols]
                    cols = st.columns(len(batch))
                    for col, name_option in zip(cols, batch):
                        with col:
                            # Use combination of record key and context for unique button key
                            if st.button(name_option, key=f"name_choice_{record_key}_{name_option}"):
                                if update_field(record['uuid'], table_name, "name", name_option):
                                    st.success(f"Name updated to '{name_option}' for UUID {record['uuid']}")
                                    st.rerun()
            elif len(name_options) == 1:
                st.write(f"**Name:** {name_options[0]}")
                st.write(f"**Description:** {record.get('description', 'N/A')}")
            
            # Use CurveHelper methods if needed
            if 'curve_json' in record:
                curve_json = record['curve_json']
                thumbnail, gradient_info = CurveHelper.generate_thumbnail_from_curve(curve_json, transparent_background=True)
                if thumbnail:
                    st.image(thumbnail, caption="Curve Thumbnail")
                if gradient_info:
                    st.write("**Gradient Info:**")
                    st.json(gradient_info)

            # Common fields display
            with st.expander("Show More"):
                # Fetch and plot the curves from the JSON URL
                json_url = record.get('curve_json_url')
                if json_url:
                    response = fetch_json(json_url)
                    if response["status"] == "success":
                        curve_data = response["data"]
                    else:
                        st.error(response["message"])
                        curve_data = None
                    thumbnail_image, _ = CurveHelper.generate_thumbnail_from_curve(curve_data, transparent_background=True) if curve_data else (None, None)
                    if curve_data and 'floatCurves' in curve_data:
                        plot_curves(curve_data['floatCurves'], thumbnail=thumbnail_image)
                st.write(f"**Machine Description:** {record.get('machine_description', 'N/A')}")
                st.write(f"**Human Description:** {record.get('human_description', 'N/A')}")
                st.write(f"**JSON URL:** {record.get('curve_json_url', 'N/A')}")
                st.write(f"**Created At:** {record.get('created_at', 'N/A')}")
                
            st.markdown("---")

def read_page(table_name):
    st.subheader(f"View All Color Curves from {table_name}")
    records_per_page = st.sidebar.number_input("Records per page", min_value=1, max_value=100, value=10)
    
    # Count total records
    total_records = count_records(table_name)
    total_pages = (total_records // records_per_page) + (1 if total_records % records_per_page > 0 else 0)
    
    # Pagination logic
    if "page" not in st.session_state:
        st.session_state.page = 1

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("◀️", key="previous") and st.session_state.page > 1:
            st.session_state.page -= 1
    with col3:
        if st.button("▶️", key="next") and st.session_state.page < total_pages:
            st.session_state.page += 1
    with col2:
        st.write(f"Page {st.session_state.page} of {total_pages}")

    offset = (st.session_state.page - 1) * records_per_page
    
    # Assuming you have a function to fetch records with limit and offset
    records = fetch_records(table_name=table_name, limit=records_per_page, offset=offset)

    # Display records
    if records:
        display_records(records, table_name=table_name, num_columns=1, thumbnail_width=640)
    else:
        st.write("No records found.")

# Call the function with the table name
if __name__ == "__main__":
    read_page("Color_Curves")