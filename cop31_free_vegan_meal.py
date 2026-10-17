)

if reservation_type == "Individual Meal Reservation":
    st.info("One free vegan meal per person per day.")
else:
    st.info("Group meal requests are subject to GNPA confirmation.")

# Database connectivity is tested server-side. Never expose credentials or
# detailed connection errors to visitors.
@st.cache_resource(show_spinner=False)
def database_connection_check():
    import psycopg2
    connection_url = st.secrets["connections"]["cop31_db"]["url"]
    conn = psycopg2.connect(connection_url, connect_timeout=8)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone()[0] == 1
    finally:
        conn.close()

# Only test on explicit request; avoids displaying operational details publicly.
with st.expander("GNPA technical connection test", expanded=False):
    st.caption("For GNPA setup only. This does not open reservations.")
    if st.button("Test database connection"):
        try:
            if database_connection_check():
                st.success("Database connection successful.")
            else:
                st.error("Database connection could not be verified.")
        except Exception:
            st.error("Database connection failed. Check Streamlit Secrets and Supabase settings.")

st.markdown("### Your Information")
with st.form("cop31_preview_form"):
    full_name = st.text_input("Full Name *")
    job_title = st.text_input("Professional Position / Job Title *")
    organization = st.text_input("Organization / Institution *")
    email = st.text_input("Email Address *")
    phone = st.text_input("Phone Number *")
    country = st.text_input("Country *")
    meal_date = st.date_input("Meal Date *", value=None)

    if reservation_type == "Group Meal Request":
        requested_quantity = st.number_input("Requested Number of Meals *", min_value=1, step=1)
        notes = st.text_area("Additional Information (optional)")
    else:
        st.write("Meal Quantity: 1 meal per person per day.")

    st.info("Pickup Location: To Be Announced")
    st.caption(
        "GNPA protects your privacy. Your information is used only for meal "
        "coordination and our plant-based mission."
    )
    st.warning("Reservations are not yet open. This form is currently for preview only.")
    st.form_submit_button("Reservations Not Yet Open", disabled=True)



