
import streamlit as st

st.set_page_config(
    page_title="COP31 Free Vegan Meal | GNPA",
    layout="centered"
)

st.markdown("""
<style>
.stApp {
    background-color: #FAFAF7;
}
.block-container {
    max-width: 800px;
    padding-top: 90px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;">

<div style="
    color:#2F765D;
    font-size:26px;
    font-weight:800;
    letter-spacing:6px;">
    GNPA
</div>

<div style="
    color:#123047;
    font-size:13px;
    margin-top:8px;">
    Global Nature &amp; Plant-based Diet Shift Agency
</div>

<h1 style="
    color:#123047;
    font-size:44px;
    margin-top:70px;">
    COP31 Free Vegan Meal
</h1>

</div>
""", unsafe_allow_html=True)



st.divider()

st.markdown("## Free Vegan Meal Reservation")

st.write(
    "Welcome to the COP31 Free Vegan Meal reservation page."
)

reservation_type = st.radio(
    "Please select your reservation type:",
    [
        "Individual Meal Reservation",
        "Group Meal Request"
    ]
)

if reservation_type == "Individual Meal Reservation":
    st.info("One free vegan meal per person per day.")

elif reservation_type == "Group Meal Request":
    st.info(
        "Group meal requests are subject to GNPA confirmation."
    )

st.markdown("### Your Information")

full_name = st.text_input("Full Name *")

job_title = st.text_input(
    "Professional Position / Job Title *"
)

organization = st.text_input(
    "Organization / Institution *"
)
