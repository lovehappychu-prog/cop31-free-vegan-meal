import csv
import hmac
import io
from datetime import date

import psycopg2
import streamlit as st

st.set_page_config(page_title='COP31 Free Vegan Meal | GNPA', layout='centered')
st.markdown('<style>.stApp{background-color:#FAFAF7}.block-container{max-width:900px;padding-top:45px}</style>', unsafe_allow_html=True)
st.markdown('<div style="text-align:center;color:#2F765D;font-size:28px;font-weight:800;letter-spacing:5px">GNPA</div>', unsafe_allow_html=True)
st.title('COP31 Free Vegan Meal')

TEST_PASSWORD = st.secrets.get('cop31_test_password', '')
ADMIN_PASSWORD = st.secrets.get('cop31_admin_password', '')
PUBLIC_OPEN = bool(st.secrets.get('cop31_public_open', False))


def db():
    return psycopg2.connect(st.secrets['connections']['cop31_db']['url'], connect_timeout=10)


def query(sql, args=()):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall() if cur.description else []


def booking(kind, args):
    with db() as conn:
        with conn.cursor() as cur:
            if kind == 'individual':
                cur.execute('SELECT booking_id,booking_status FROM public.cop31_book_individual(%s,%s,%s,%s,%s,%s,%s)', args)
                return cur.fetchone()
            cur.execute('SELECT public.cop31_request_group(%s,%s,%s,%s,%s,%s,%s,%s,%s)', args)
            return cur.fetchone()[0], 'pending'


def csv_bytes(headers, records):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(records)
    return output.getvalue().encode('utf-8-sig')


def update_group(request_id, decision):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT requested_date,requested_quantity,status FROM public.cop31_group_requests WHERE id=%s FOR UPDATE', (request_id,))
            record = cur.fetchone()
            if not record or record[2] != 'pending':
                raise ValueError('Only pending group requests can be reviewed.')
            day, qty, _ = record
            if decision == 'approved':
                cur.execute('SELECT total_capacity,reserved_internal,booked_individual,booked_group,is_open FROM public.cop31_meal_days WHERE meal_date=%s FOR UPDATE', (day,))
                cap = cur.fetchone()
                if not cap or not cap[4]:
                    raise ValueError('This meal day is not open in the database.')
                if cap[0] - cap[1] - cap[2] - cap[3] < qty:
                    raise ValueError('Insufficient remaining meals. No approval was made.')
                cur.execute('UPDATE public.cop31_meal_days SET booked_group=booked_group+%s WHERE meal_date=%s', (qty, day))
            cur.execute('UPDATE public.cop31_group_requests SET status=%s WHERE id=%s', (decision, request_id))


def cancel_individual(booking_id):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT meal_date,status FROM public.cop31_individual_reservations WHERE id=%s FOR UPDATE', (booking_id,))
            record = cur.fetchone()
            if not record or record[1] not in ('confirmed', 'waitlisted'):
                raise ValueError('Reservation is already cancelled or missing.')
            day, status = record
            cur.execute("UPDATE public.cop31_individual_reservations SET status='cancelled' WHERE id=%s", (booking_id,))
            if status == 'confirmed':
                cur.execute('UPDATE public.cop31_meal_days SET booked_individual=booked_individual-1 WHERE meal_date=%s', (day,))


def promote_waitlist(day):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT total_capacity,reserved_internal,booked_individual,booked_group FROM public.cop31_meal_days WHERE meal_date=%s FOR UPDATE', (day,))
            cap = cur.fetchone()
            if not cap or cap[0] <= sum(cap[1:]):
                raise ValueError('No available meal capacity for this date.')
            cur.execute("SELECT id FROM public.cop31_individual_reservations WHERE meal_date=%s AND status='waitlisted' ORDER BY created_at,id LIMIT 1 FOR UPDATE", (day,))
            record = cur.fetchone()
            if not record:
                raise ValueError('No waitlisted reservations on this date.')
            cur.execute("UPDATE public.cop31_individual_reservations SET status='confirmed' WHERE id=%s", (record[0],))
            cur.execute('UPDATE public.cop31_meal_days SET booked_individual=booked_individual+1 WHERE meal_date=%s', (day,))
            return str(record[0])


def cancel_group(request_id):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT requested_date,requested_quantity,status FROM public.cop31_group_requests WHERE id=%s FOR UPDATE', (request_id,))
            record = cur.fetchone()
            if not record or record[2] not in ('approved', 'pending'):
                raise ValueError('This request cannot be cancelled.')
            day, qty, status = record
            if status == 'approved':
                cur.execute('UPDATE public.cop31_meal_days SET booked_group=booked_group-%s WHERE meal_date=%s', (qty, day))
            cur.execute("UPDATE public.cop31_group_requests SET status='cancelled' WHERE id=%s", (request_id,))


page = st.radio('Choose page / 選擇頁面', ['Meal Reservation / 餐點預約', 'GNPA Administration / 管理後台'], horizontal=True)

if page.startswith('Meal Reservation'):
    st.subheader('Free Vegan Meal Reservation')
    st.write('Welcome to the COP31 Free Vegan Meal reservation page.')
    if PUBLIC_OPEN:
        st.success('Reservations are open. / 預約已開放')
    else:
        st.warning('Reservations are not yet open. / 尚未開放正式預約')
    test_authorized = False
    if not PUBLIC_OPEN and TEST_PASSWORD:
        with st.expander('GNPA private testing / 私人測試'):
            password = st.text_input('Testing password', type='password')
            test_authorized = bool(password) and hmac.compare_digest(password, TEST_PASSWORD)
            if test_authorized:
                st.success('Private test mode enabled. Use fictional information only.')
    reservation_type = st.radio('Reservation type / 預約類型', ['Individual Meal Reservation', 'Group Meal Request'])
    st.info('One meal per person per day.' if reservation_type.startswith('Individual') else 'Group requests require GNPA approval.')
    with st.form('meal_form'):
        name = st.text_input('Full Name *')
        title = st.text_input('Professional Position / Job Title *')
        organization = st.text_input('Organization / Institution *')
        email = st.text_input('Email Address *')
        phone = st.text_input('Phone Number *')
        country = st.text_input('Country *')
        meal_date = st.date_input('Meal Date *', value=None)
        qty, notes = 1, ''
        if reservation_type.startswith('Group'):
            qty = st.number_input('Requested Number of Meals *', min_value=1, step=1)
            notes = st.text_area('Additional Information (optional)')
        else:
            st.write('Meal Quantity: 1')
        st.info('Pickup Location: To Be Announced')
        st.caption('Your information is used for meal coordination. / 資料僅供餐點安排使用。')
        enabled = PUBLIC_OPEN or test_authorized
        submitted = st.form_submit_button('Submit reservation' if PUBLIC_OPEN else ('Submit TEST reservation' if enabled else 'Reservations Not Yet Open'), disabled=not enabled)
    if submitted and (PUBLIC_OPEN or test_authorized):
        fields = (name, title, organization, email, phone, country)
        if not all(v.strip() for v in fields) or meal_date is None:
            st.error('Please complete all required fields.')
        elif '@' not in email or '.' not in email.split('@')[-1]:
            st.error('Please enter a valid email address.')
        else:
            try:
                args = fields + (meal_date,)
                kind = 'individual' if reservation_type.startswith('Individual') else 'group'
                booking_id, status = booking(kind, args if kind == 'individual' else args + (int(qty), notes))
                st.success(f'Submission recorded. Status: {status.upper()}. Reference: {booking_id}')
                if not PUBLIC_OPEN:
                    st.caption('TEST DATA — must be deleted before public launch.')
            except Exception:
                st.error('Submission failed. Please check the date, availability, or duplicate email. Contact GNPA if needed.')

else:
    st.subheader('GNPA Administration / 管理後台')
    if not ADMIN_PASSWORD:
        st.error('Admin access is not configured. Add cop31_admin_password in Streamlit Secrets first.')
        st.stop()
    if not st.session_state.get('gnpa_admin_logged_in', False):
        with st.form('admin_login'):
            password = st.text_input('GNPA administrator password / 管理密碼', type='password')
            login = st.form_submit_button('Sign in / 登入')
        if login:
            if password and hmac.compare_digest(password, ADMIN_PASSWORD):
                st.session_state.gnpa_admin_logged_in = True
                st.rerun()
            else:
                st.error('Incorrect administrator password.')
        st.stop()
    if st.button('Sign out / 登出'):
        st.session_state.gnpa_admin_logged_in = False
        st.rerun()
    st.warning('Private GNPA records. Do not share exported files publicly. / 管理資料請勿公開。')
    try:
        days = query('SELECT meal_date,total_capacity,reserved_internal,booked_individual,booked_group,is_open FROM public.cop31_meal_days ORDER BY meal_date')
        individuals = query('SELECT id,full_name,job_title,organization,email,phone,country,meal_date,status,created_at FROM public.cop31_individual_reservations ORDER BY meal_date,created_at')
        groups = query('SELECT id,contact_name,job_title,organization,email,phone,country,requested_date,requested_quantity,notes,status,created_at FROM public.cop31_group_requests ORDER BY requested_date,created_at')
    except Exception:
        st.error('Could not load data from Supabase. Please check the connection.')
        st.stop()
    tabs = st.tabs(['Daily capacity / 每日餐量', 'Individuals / 個人名單', 'Groups / 團體審核', 'Waitlist / 候補'])
    with tabs[0]:
        st.write('Daily capacity / 每日供餐量')
        st.dataframe([{'Date': str(d[0]), 'Capacity': d[1], 'Internal': d[2], 'Confirmed individuals': d[3], 'Approved group meals': d[4], 'Remaining': d[1]-d[2]-d[3]-d[4], 'Day open': d[5]} for d in days], use_container_width=True)
        st.caption('Opening a meal day here allows private tests, but public submissions still require cop31_public_open=true in Secrets.')
        with st.form('day_settings'):
            day = st.date_input('Meal date / 日期', value=None)
            capacity = st.number_input('Total capacity / 總餐量', min_value=0, value=700, step=1)
            internal = st.number_input('Reserved for GNPA / 內部保留', min_value=0, value=0, step=1)
            is_open = st.checkbox('Accept reservations for this day / 開放該日', value=False)
            save_day = st.form_submit_button('Save day settings / 儲存')
        if save_day:
            if day is None or internal > capacity:
                st.error('Select a date and ensure internal reserved meals do not exceed capacity.')
            else:
                try:
                    with db() as conn:
                        with conn.cursor() as cur:
                            cur.execute('''INSERT INTO public.cop31_meal_days(meal_date,total_capacity,reserved_internal,is_open)
                                VALUES(%s,%s,%s,%s) ON CONFLICT(meal_date) DO UPDATE SET
                                total_capacity=EXCLUDED.total_capacity,reserved_internal=EXCLUDED.reserved_internal,is_open=EXCLUDED.is_open''', (day, int(capacity), int(internal), is_open))
                    st.success('Day settings saved. Refresh this page to see updated totals.')
                except Exception:
                    st.error('Could not save: capacity may be below existing confirmed bookings.')
    with tabs[1]:
        st.write(f'Individual reservations: {len(individuals)}')
        st.dataframe([{'ID':str(r[0]),'Name':r[1],'Title':r[2],'Organization':r[3],'Email':r[4],'Phone':r[5],'Country':r[6],'Date':str(r[7]),'Status':r[8]} for r in individuals], use_container_width=True)
        st.download_button('Download individual CSV / 下載個人名單', csv_bytes(['id','full_name','job_title','organization','email','phone','country','meal_date','status','created_at'], individuals), 'cop31_individuals.csv', 'text/csv')
        active = [r for r in individuals if r[8] in ('confirmed','waitlisted')]
        if active:
            selected = st.selectbox('Select reservation to cancel / 選擇取消預約', active, format_func=lambda r:f'{r[1]} — {r[7]} — {r[8]} — {str(r[0])[:8]}')
            confirm = st.checkbox('I confirm cancellation / 我確認取消此預約', key='cancel_i_confirm')
            if st.button('Cancel selected individual / 取消此人', disabled=not confirm):
                try:
                    cancel_individual(selected[0])
                    st.success('Cancelled. Refresh page to see the change.')
                except Exception as exc:
                    st.error(str(exc))
    with tabs[2]:
        st.write(f'Group requests: {len(groups)}')
        st.dataframe([{'ID':str(r[0]),'Contact':r[1],'Organization':r[3],'Email':r[4],'Date':str(r[7]),'Meals':r[8],'Notes':r[9],'Status':r[10]} for r in groups], use_container_width=True)
        st.download_button('Download group CSV / 下載團體名單', csv_bytes(['id','contact_name','job_title','organization','email','phone','country','requested_date','requested_quantity','notes','status','created_at'], groups), 'cop31_groups.csv', 'text/csv')
        pending = [r for r in groups if r[10] == 'pending']
        if pending:
            selected_group = st.selectbox('Pending request / 待審團體', pending, format_func=lambda r:f'{r[1]} — {r[7]} — {r[8]} meals — {str(r[0])[:8]}')
            decision = st.radio('Decision / 決定', ['approved','rejected'], horizontal=True)
            confirm_group = st.checkbox('I confirm this decision / 我確認此決定', key='group_confirm')
            if st.button('Apply group decision / 執行審核', disabled=not confirm_group):
                try:
                    update_group(selected_group[0], decision)
                    st.success('Decision saved. Refresh page to see the change.')
                except Exception as exc:
                    st.error(str(exc))
        approved = [r for r in groups if r[10] in ('approved','pending')]
        if approved:
            selected_cancel_group = st.selectbox('Group to cancel / 取消團體', approved, format_func=lambda r:f'{r[1]} — {r[7]} — {r[10]} — {str(r[0])[:8]}')
            if st.checkbox('Confirm group cancellation / 確認取消團體', key='gc') and st.button('Cancel group request / 取消團體申請'):
                try:
                    cancel_group(selected_cancel_group[0])
                    st.success('Group cancelled. Refresh page.')
                except Exception as exc:
                    st.error(str(exc))
    with tabs[3]:
        waiting = [r for r in individuals if r[8] == 'waitlisted']
        st.write(f'Waitlisted people: {len(waiting)}')
        st.dataframe([{'Name':r[1],'Email':r[4],'Date':str(r[7]),'Created':str(r[9])} for r in waiting], use_container_width=True)
        dates = sorted(set(r[7] for r in waiting))
        if dates:
            selected_day = st.selectbox('Date to promote earliest waitlisted person / 候補遞補日期', dates)
            st.caption('Only promotes one person if capacity is available. Notify the person separately.')
            confirm_promotion = st.checkbox('Confirm promotion / 確認遞補')
            if st.button('Promote next person / 遞補一人', disabled=not confirm_promotion):
                try:
                    promoted = promote_waitlist(selected_day)
                    st.success(f'Promoted: {promoted}. Please notify the person and refresh the page.')
                except Exception as exc:
                    st.error(str(exc))
