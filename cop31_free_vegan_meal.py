import streamlit as st
from datetime import date
import psycopg2
from psycopg2 import errors

st.set_page_config(page_title='COP31 Free Vegan Meal | GNPA', layout='centered')

# Safety: reservations remain disabled unless GNPA deliberately configures
# a private testing password in Streamlit Secrets. Never put passwords in GitHub.
TEST_PASSWORD = st.secrets.get('cop31_test_password', '')

st.markdown('''<style>.stApp{background-color:#FAFAF7}.block-container{max-width:800px;padding-top:90px}</style>''', unsafe_allow_html=True)
st.markdown('''<div style="text-align:center"><div style="color:#2F765D;font-size:26px;font-weight:800;letter-spacing:6px">GNPA</div><div style="color:#123047;font-size:13px;margin-top:8px">Global Nature &amp; Plant-based Diet Shift Agency</div><h1 style="color:#123047;font-size:44px;margin-top:70px">COP31 Free Vegan Meal</h1></div>''', unsafe_allow_html=True)
st.divider()
st.markdown('## Free Vegan Meal Reservation')
st.write('Welcome to the COP31 Free Vegan Meal reservation page.')

@st.cache_resource(show_spinner=False)
def database_connection_check():
    conn = psycopg2.connect(st.secrets['connections']['cop31_db']['url'], connect_timeout=8)
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
            return cur.fetchone()[0] == 1
    finally:
        conn.close()

def run_booking(kind, values):
    conn = psycopg2.connect(st.secrets['connections']['cop31_db']['url'], connect_timeout=8)
    try:
        with conn:
            with conn.cursor() as cur:
                if kind == 'individual':
                    cur.execute('''SELECT booking_id, booking_status FROM public.cop31_book_individual(%s,%s,%s,%s,%s,%s,%s)''', values)
                    return cur.fetchone()
                cur.execute('''SELECT public.cop31_request_group(%s,%s,%s,%s,%s,%s,%s,%s,%s)''', values)
                return (cur.fetchone()[0], 'pending')
    finally:
        conn.close()

with st.expander('GNPA technical connection test'):
    st.caption('For GNPA setup only. This does not open public reservations.')
    if st.button('Test database connection'):
        try:
            st.success('Database connection successful.') if database_connection_check() else st.error('Database connection could not be verified.')
        except Exception:
            st.error('Database connection failed. Check Streamlit Secrets and Supabase settings.')

st.warning('Reservations are not yet open. This form is currently for preview only.')

# Private testing is off unless a password is explicitly configured.
test_authorized = False
if TEST_PASSWORD:
    with st.expander('GNPA private testing (not for public reservations)'):
        supplied_password = st.text_input('GNPA testing password', type='password')
        test_authorized = bool(supplied_password) and supplied_password == TEST_PASSWORD
        if test_authorized:
            st.success('Private test mode enabled for this session. Use fictional data only.')
        elif supplied_password:
            st.error('Incorrect testing password.')

reservation_type = st.radio('Please select your reservation type:', ['Individual Meal Reservation', 'Group Meal Request'])
if reservation_type == 'Individual Meal Reservation':
    st.info('One free vegan meal per person per day.')
else:
    st.info('Group meal requests are subject to GNPA confirmation.')

st.markdown('### Your Information')
with st.form('cop31_meal_form'):
    full_name = st.text_input('Full Name *')
    job_title = st.text_input('Professional Position / Job Title *')
    organization = st.text_input('Organization / Institution *')
    email = st.text_input('Email Address *')
    phone = st.text_input('Phone Number *')
    country = st.text_input('Country *')
    meal_date = st.date_input('Meal Date *', value=None)
    quantity = 1
    notes = ''
    if reservation_type == 'Group Meal Request':
        quantity = st.number_input('Requested Number of Meals *', min_value=1, step=1)
        notes = st.text_area('Additional Information (optional)')
    else:
        st.write('Meal Quantity: 1 meal per person per day.')
    st.info('Pickup Location: To Be Announced')
    st.caption('GNPA protects your privacy. Your information is used only for meal coordination and our plant-based mission.')
    submitted = st.form_submit_button('Submit TEST reservation' if test_authorized else 'Reservations Not Yet Open', disabled=not test_authorized)

if submitted and test_authorized:
    fields = [full_name, job_title, organization, email, phone, country]
    if not all(isinstance(x, str) and x.strip() for x in fields) or meal_date is None:
        st.error('Please complete all required fields.')
    elif '@' not in email or '.' not in email.split('@')[-1]:
        st.error('Please enter a valid email address.')
    else:
        try:
            common = (full_name, job_title, organization, email, phone, country, meal_date)
            if reservation_type == 'Individual Meal Reservation':
                booking_id, status = run_booking('individual', common)
            else:
                booking_id, status = run_booking('group', common + (int(quantity), notes))
            st.success(f'TEST submission recorded. Status: {status.upper()}. Reference: {booking_id}')
            st.info('This is a test record. GNPA must remove test records before public launch.')
        except Exception:
            st.error('The test submission could not be completed. Check the test date, capacity settings, duplicate emails, and Supabase configuration. No confirmation was issued.')
