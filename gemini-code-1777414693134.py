import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF

# 1. DATABASE CONNECTION (Must be before any other code)
conn = sqlite3.connect('cricket_data.db', check_same_thread=False)
c = conn.cursor()

# 2. CREATE TABLES (Ensures the 'services' table exists)
c.execute('''CREATE TABLE IF NOT EXISTS inventory 
             (id INTEGER PRIMARY KEY, name TEXT, brand TEXT, category TEXT, sku TEXT, 
              cost REAL, vendor TEXT, p_date DATE, sell_price REAL, shipping REAL, 
              sale_date DATE, profit REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS services 
             (id INTEGER PRIMARY KEY, service_name TEXT, price REAL, 
              customer_name TEXT, sale_date DATE, pay_method TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS expenses 
             (id INTEGER PRIMARY KEY, category TEXT, amount REAL, notes TEXT, date DATE)''')
conn.commit()

def create_pdf_invoice(customer, pay_method, cart_items):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 20)
    
    # Header
    pdf.set_text_color(0, 77, 64) # British Green
    pdf.cell(0, 10, "CRICKET GEAR PRO UK", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, "Official Sales Invoice - Slough, Berkshire", ln=True, align='C')
    pdf.ln(10)
    
    # Customer Info
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Customer: {customer}", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 7, f"Date: {datetime.now().strftime('%d-%b-%Y')}", ln=True)
    pdf.cell(0, 7, f"Payment Method: {pay_method}", ln=True)
    pdf.ln(5)
    
    # Table Header
    pdf.set_fill_color(0, 77, 64)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(80, 10, " Item Description", border=1, fill=True)
    pdf.cell(25, 10, " Qty", border=1, fill=True, align='C')
    pdf.cell(30, 10, " Price", border=1, fill=True, align='C')
    pdf.cell(25, 10, " Disc", border=1, fill=True, align='C')
    pdf.cell(30, 10, " Total", border=1, fill=True, align='C')
    pdf.ln()
    
    # Table Body
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", size=10)
    total_bill = 0
    for item in cart_items:
        pdf.cell(80, 10, f" {item['name']}", border=1)
        pdf.cell(25, 10, f" {item['qty']}", border=1, align='C')
        pdf.cell(30, 10, f" £{item['price']:.2f}", border=1, align='C')
        pdf.cell(25, 10, f" -£{item['discount']:.2f}", border=1, align='C')
        pdf.cell(30, 10, f" £{item['total']:.2f}", border=1, align='C')
        pdf.ln()
        total_bill += item['total']
        
    # Grand Total
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(160, 10, "Grand Total ", border=0, align='R')
    pdf.cell(30, 10, f"£{total_bill:.2f}", border=1, align='C')
    
    # Footer
    pdf.ln(20)
    pdf.set_font("Arial", 'I', 8)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, "Thank you for your custom!", ln=True, align='C')
    pdf.cell(0, 5, "All goods remain property of Cricket Gear Pro until paid in full.", ln=True, align='C')

    # Return as bytes
    return pdf.output()



# --- CONFIG & SECURITY ---
st.set_page_config(page_title="Cricket Pro Billing", layout="wide", initial_sidebar_state="collapsed")


def check_password():
    if "authenticated" not in st.session_state:
        st.title("🔐 Cricket Billing Login")
        pwd = st.text_input("Enter Access Code", type="password")
        if st.button("Login"):
            if pwd == "cricket123": # Change this to your preferred password
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid Code")
        return False
    return True

if not check_password():
    st.stop()

# --- DATABASE SETUP ---
conn = sqlite3.connect('cricket_data.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS inventory 
                 (id INTEGER PRIMARY KEY, name TEXT, brand TEXT, category TEXT, sku TEXT UNIQUE, 
                  cost REAL, vendor TEXT, p_date DATE, sell_price REAL, shipping REAL, sale_date DATE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS expenses 
                 (id INTEGER PRIMARY KEY, desc TEXT, amount REAL, category TEXT, e_date DATE)''')
    conn.commit()

init_db()

# --- HELPER: GENERATE 300 ITEMS ---
def generate_mock_data():
    categories = [
        "English Willow Bats", "Kashmir Willow Bats", "Leather Balls", "Tennis Balls", 
        "Bat Grips", "Helmets", "Batting Pads", "WK Pads", "Batting Gloves", "WK Gloves",
        "Thigh Guards", "Chest Guards", "Arm Guards", "Abdo Guards", "Inner Gloves",
        "Shoes (Spikes)", "Shoes (Turf)", "Jerseys", "Trousers", "Socks",
        "Wheelie Bags", "Duffle Bags", "Stumps", "Bails", "Umpire Counters",
        "Training Nets", "Bowling Machines", "Boundary Markers", "Bat Oil", "Grip Cones"
    ]
    brands = ["SS", "SG", "Kookaburra", "GM", "Gray-Nicolls", "Adidas", "DSC", "NK"]
    
    for i in range(300):
        cat = random.choice(categories)
        sku = f"{cat[:3].upper()}-{1000+i}"
        cost = round(random.uniform(10, 200), 2)
        # Randomly mark some as sold in the last 30 days
        s_date = (datetime.now() - timedelta(days=random.randint(0, 30))).date() if i % 3 == 0 else None
        
        try:
            c.execute("INSERT INTO inventory (name, brand, category, sku, cost, vendor, p_date, sell_price, shipping, sale_date) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (f"{cat} {random.randint(1,5)}", random.choice(brands), cat, sku, cost, "Global Sports Ltd", "2026-01-01", cost*1.5, 5.0, s_date))
        except: pass
    conn.commit()

if st.sidebar.button("Factory Reset & Load 300 Items"):
    generate_mock_data()
    st.success("Database Reset with 300 items!")

# --- DASHBOARD LOGIC ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Sales (POS)", "Inventory Management", "Expenses"])


if page == "Dashboard":
    st.header("📈 Profit Analytics")
    
    # Date Filtering
    sales_query = "SELECT * FROM inventory WHERE sale_date IS NOT NULL"
    sales = pd.read_sql(sales_query, conn)
    
    t = st.radio("Timeframe", ["Daily", "Weekly", "Monthly"], horizontal=True)
    today = datetime.now().date()
    start_date = today if t == "Daily" else (today - timedelta(days=7) if t == "Weekly" else today.replace(day=1))
    
    # Query Data
    sales = pd.read_sql(f"SELECT * FROM inventory WHERE sale_date >= '{start_date}'", conn)
    exps = pd.read_sql(f"SELECT * FROM expenses WHERE e_date >= '{start_date}'", conn)
    
    sales['profit'] = sales['sell_price'] - sales['cost'] - sales['shipping']
    gross_profit = sales['profit'].sum()
    total_expenses = exps['amount'].sum()
    net_profit = gross_profit - total_expenses
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Gross Profit", f"${gross_profit:,.2f}")
    m2.metric("Expenses", f"-${total_expenses:,.2f}")
    m3.metric("Net Profit", f"${net_profit:,.2f}")
    
    
    st.subheader("Recent Sales & Customer History")
    # We select the 'vendor' column because that's where we saved the Customer Name
    # We rename it to 'Details' for clarity on the screen
    display_df = sales[['sale_date', 'name', 'brand', 'sku', 'vendor', 'sell_price', 'profit']].copy()
    display_df.columns = ['Date', 'Item', 'Brand', 'SKU', 'Vendor/Customer', 'Sold Price', 'Profit']
    
    st.dataframe(display_df.sort_values(by="Date", ascending=False), use_container_width=True)
   # Fetch Service Income
    services_df = pd.read_sql(f"SELECT * FROM services WHERE sale_date BETWEEN '{start_date}' AND '{end_date}'", conn)
    service_revenue = services_df['price'].sum() if not services_df.empty else 0.0

    # Metrics Layout
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Gear Profit", f"£{gross_profit:,.2f}") # From inventory
    col2.metric("Labor Income", f"£{service_revenue:,.2f}") # From services
    col3.metric("Expenses", f"-£{total_expenses:,.2f}")
    
    net_total = (gross_profit + service_revenue) - total_expenses
    col4.metric("Net Profit", f"£{net_total:,.2f}", delta=f"£{service_revenue} from labor")
    
   # --- REPLACE EVERYTHING BELOW YOUR METRIC COLUMNS WITH THIS ---
    st.divider()
    
    # --- 1. LABOR & SERVICE ANALYTICS ---
    st.subheader("🛠️ Labor & Service History")
    
    # Check if we have any service data in the current date range
    if not services_df.empty:
        col_svc1, col_svc2 = st.columns([2, 1])
        
        with col_svc1:
            st.markdown("### Recent Services")
            # Format the table for the screen
            svc_view = services_df[['sale_date', 'service_name', 'customer_name', 'price', 'pay_method']].copy()
            svc_view.columns = ['Date', 'Service Type', 'Customer', 'Fee (£)', 'Payment']
            st.dataframe(svc_view.sort_values(by="Date", ascending=False), use_container_width=True)
            
        with col_svc2:
            st.markdown("### Top Services")
            # Show which services are most popular
            svc_counts = services_df['service_name'].value_counts().reset_index()
            svc_counts.columns = ['Service', 'Times Done']
            st.table(svc_counts)
    else:
        st.info("No service data recorded for this period.")

    st.divider()

    # --- 2. GEAR SALES HISTORY ---
    st.subheader("🏏 Recent Gear Sales")
    if not sales.empty:
        # This shows the actual bats/balls sold
        gear_view = sales[['sale_date', 'name', 'brand', 'sku', 'vendor', 'sell_price', 'profit']].copy()
        gear_view.columns = ['Date', 'Item', 'Brand', 'SKU', 'Customer Info', 'Sold (£)', 'Profit (£)']
        st.dataframe(gear_view.sort_values(by="Date", ascending=False), use_container_width=True)
    else:
        st.info("No gear sales recorded for this period.")


elif page == "Inventory Management":
    st.header("📦 Warehouse & Stock Management")
    
    # --- TABBED INTERFACE FOR CLEANER MOBILE LOOK ---
    tab1, tab2 = st.tabs(["📄 Manual Entry", "📤 Bulk CSV Upload"])

    with tab1:
        with st.expander("➕ Add New Stock (Manual Entry)", expanded=False):
            with st.form("comprehensive_add_form", clear_on_submit=True):
                # ... (Keep your previous manual form code here) ...
                st.write("Use the form below for single item entry")
                # [Previous form logic from our last conversation goes here]

    with tab2:
        st.subheader("Bulk Import via CSV")
        st.write("Upload a CSV file to add multiple items at once.")
        
        # 1. Download Template Button
        template_data = {
            "name": ["English Willow Bat", "Leather Ball"],
            "brand": ["SS", "SG"],
            "category": ["Bats", "Balls"],
            "sku": ["BAT-101", "BALL-101"],
            "cost": [100.0, 10.0],
            "vendor": ["Supplier A", "Supplier B"],
            "sell_price": [150.0, 15.0],
            "shipping": [5.0, 1.0],
            "p_date": ["2026-04-29", "2026-04-29"]
        }
        template_df = pd.DataFrame(template_data)
        st.download_button("📥 Download CSV Template", template_df.to_csv(index=False), "template.csv", "text/csv")

        # 2. File Uploader
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
        
        if uploaded_file is not None:
            data = pd.read_csv(uploaded_file)
            st.write("Preview of items to be added:")
            st.dataframe(data.head())
            
            if st.button("🚀 Upload & Save to Database"):
                try:
                    count = 0
                    for index, row in data.iterrows():
                        c.execute('''INSERT INTO inventory 
                                     (name, brand, category, sku, cost, vendor, p_date, sell_price, shipping) 
                                     VALUES (?,?,?,?,?,?,?,?,?)''', 
                                  (row['name'], row['brand'], row['category'], row['sku'], 
                                   row['cost'], row['vendor'], row['p_date'], 
                                   row['sell_price'], row['shipping']))
                        count += 1
                    conn.commit()
                    st.success(f"Successfully loaded {count} items into the database!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: Make sure your CSV columns match the template. Details: {e}")

    # --- STOCK LEVELS ---
    st.divider()
    st.subheader("📋 Stock Levels (Available)")
    # [Keep the 'summary_query' and 'df_summary' logic from before]
    summary_query = """
        SELECT name, brand, category, sell_price, COUNT(*) as qty_left 
        FROM inventory 
        WHERE sale_date IS NULL 
        GROUP BY name, brand, category, sell_price
    """
    df_summary = pd.read_sql(summary_query, conn)
    st.dataframe(df_summary, use_container_width=True)

elif page == "Expenses":
    st.header("💸 Add Expense")
    with st.form("exp_form"):
        desc = st.text_input("Description (e.g. Rent, Electricity)")
        amt = st.number_input("Amount", min_value=0.0)
        cat = st.selectbox("Category", ["Utilities", "Rent", "Staff", "Marketing", "Other"])
        date = st.date_input("Date", datetime.now())
        if st.form_submit_button("Save Expense"):
            c.execute("INSERT INTO expenses (desc, amount, category, e_date) VALUES (?,?,?,?)", (desc, amt, cat, date))
            conn.commit()
            st.success("Expense Recorded!")

elif page == "Sales (POS)":
    st.header("🏪 Point of Sale")

    if 'cart' not in st.session_state:
        st.session_state.cart = []

    # --- 1. CUSTOMER & PAYMENT INFO ---
    c1, c2 = st.columns(2)
    with c1:
        cust_name = st.text_input("👤 Customer Name")
    with c2:
        pay_method = st.selectbox("💳 Payment Method", ["Cash", "Card", "Bank Transfer", "UPI/QR"])
    
    # --- 2. ADD SERVICES (NEW SECTION) ---
    with st.expander("🛠️ Add a Service (Repair, Knocking, etc.)"):
        col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
        service_name = col_s1.text_input("Service Name", placeholder="e.g. Bat Knocking")
        service_price = col_s2.number_input("Price (£)", min_value=0.0)
        if col_s3.button("Add Service"):
            if service_name:
                st.session_state.cart.append({
                    'ids': [9999], # Dummy ID for services
                    'name': f"SERVICE: {service_name}",
                    'price': service_price,
                    'qty': 1,
                    'discount': 0.0,
                    'total': service_price
                })
                st.rerun()

    # --- 3. SEARCH & ADD PRODUCTS ---
    search_item = st.text_input("🔍 Search Stock (Name or SKU)")
    if search_item:
        query = f"SELECT * FROM inventory WHERE (name LIKE '%{search_item}%' OR sku LIKE '%{search_item}%') AND sale_date IS NULL LIMIT 5"
        results = pd.read_sql(query, conn)
        
        for index, row in results.iterrows():
            with st.expander(f"➕ Add {row['name']} ({row['sku']})"):
                col_q, col_d, col_b = st.columns([1, 1, 1])
                qty = col_q.number_input("Qty", min_value=1, value=1, key=f"q_{row['id']}")
                disc = col_d.number_input("Disc (£)", min_value=0.0, value=0.0, key=f"d_{row['id']}")
                
                if col_b.button("Add to Basket", key=f"btn_{row['id']}"):
                    find_others = pd.read_sql(f"SELECT id FROM inventory WHERE name = '{row['name']}' AND sale_date IS NULL LIMIT {qty}", conn)
                    if len(find_others) < qty:
                        st.error("Insufficient stock!")
                    else:
                        st.session_state.cart.append({
                            'ids': find_others['id'].tolist(),
                            'name': row['name'],
                            'price': row['sell_price'],
                            'qty': qty,
                            'discount': disc,
                            'total': (row['sell_price'] * qty) - disc
                        })
                        st.rerun()

    # --- 4. THE BASKET & CHECKOUT ---
    if st.session_state.cart:
        st.divider()
        st.subheader("🛒 Basket Summary")
        for i, item in enumerate(st.session_state.cart):
            c_a, c_b, c_c = st.columns([3, 1, 1])
            c_a.write(f"**{item['name']}** (x{item['qty']})")
            c_b.write(f"£{item['total']:.2f}")
            if c_c.button("❌", key=f"del_{i}"):
                st.session_state.cart.pop(i)
                st.rerun()
        
        grand_total = sum(item['total'] for item in st.session_state.cart)
        st.markdown(f"## Total: **£{grand_total:,.2f}**")

if st.button("🏁 Finalize Sale & Generate Invoice", use_container_width=True):
            if cust_name:
                today = datetime.now().strftime('%Y-%m-%d')
                
                # THIS IS THE LINE THAT WAS CAUSING THE ERROR
                for item in st.session_state.cart:
                    if item['ids'][0] != 9999: # It's a PRODUCT
                        for item_id in item['ids']:
                            note = f"Cust: {cust_name} | Pay: {pay_method}"
                            c.execute("UPDATE inventory SET sale_date = ?, vendor = ? WHERE id = ?", 
                                      (today, note, item_id))
                    else: # It's a SERVICE
                        c.execute('''INSERT INTO services (service_name, price, customer_name, sale_date, pay_method) 
                                     VALUES (?,?,?,?,?)''', 
                                  (item['name'].replace("SERVICE: ", ""), item['price'], cust_name, today, pay_method))
                
                conn.commit()
                
                # PDF Generation
                pdf_bytes = create_pdf_invoice(cust_name, pay_method, st.session_state.cart)
                st.download_button(
                    label="📥 Download PDF Invoice",
                    data=bytes(pdf_bytes),
                    file_name=f"Invoice_{cust_name}.pdf",
                    mime="application/pdf"
                )
                
                st.session_state.cart = []
                st.success("Sale Completed Successfully!")
            else:
                st.error("Please enter a Customer Name")
