import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import random

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

    # Session state for the cart
    if 'cart' not in st.session_state:
        st.session_state.cart = []

    # 1. Customer Info
    cust_name = st.text_input("👤 Customer Name")
    
    # 2. Search & Add
    search_item = st.text_input("🔍 Search Item (Name or SKU)")
    if search_item:
        query = f"SELECT * FROM inventory WHERE (name LIKE '%{search_item}%' OR sku LIKE '%{search_item}%') AND sale_date IS NULL LIMIT 5"
        results = pd.read_sql(query, conn)
        
        for index, row in results.iterrows():
            col1, col2 = st.columns([3, 1])
            col1.write(f"**{row['name']}** - ${row['sell_price']}")
            if col2.button("➕ Add", key=f"pos_{row['id']}"):
                st.session_state.cart.append({
                    'id': row['id'], 'name': row['name'], 'sku': row['sku'], 
                    'price': row['sell_price'], 'brand': row['brand']
                })
                st.rerun()

    # 3. Checkout Basket
    if st.session_state.cart:
        st.subheader("🛒 Basket")
        for i, item in enumerate(st.session_state.cart):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"{item['name']}")
            c2.write(f"${item['price']}")
            if c3.button("❌", key=f"rem_{i}"):
                st.session_state.cart.pop(i)
                st.rerun()
        
        total = sum(item['price'] for item in st.session_state.cart)
        st.markdown(f"### Total Bill: **${total:,.2f}**")

        if st.button("🏁 Finalize & Print Receipt", use_container_width=True):
            if cust_name:
                today = datetime.now().strftime('%Y-%m-%d')
                for item in st.session_state.cart:
                    c.execute("UPDATE inventory SET sale_date = ?, vendor = vendor || ' | Customer: ' || ? WHERE id = ?", 
                              (today, cust_name, item['id']))
                conn.commit()
                st.session_state.cart = []
                st.success(f"Sale recorded for {cust_name}!")
                st.balloons() # Fun effect for mobile!
            else:
                st.error("Please enter Customer Name")
