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
    brands = ["SS", "SG", "Kookaburra", "GM", "Gray-Nicolls", "Adidas", "DSC"]
    
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
page = st.sidebar.radio("Go to", ["Dashboard", "Inventory Management", "Expenses"])

if page == "Dashboard":
    st.header("📈 Profit Analytics")
    
    # Date Filtering
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
    
    st.subheader("Recent Sales")
    st.dataframe(sales[['name', 'category', 'sell_price', 'profit', 'sale_date']], use_container_width=True)

elif page == "Inventory Management":
    st.header("📦 Inventory Management")
    
    # --- FORM TO ADD NEW ITEM ---
    with st.expander("➕ Add New Stock Item", expanded=False):
        with st.form("new_item_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                item_name = st.text_input("Item Name")
                brand = st.text_input("Brand")
                # The 30 categories we discussed
                category = st.selectbox("Category", [
                    "English Willow Bats", "Kashmir Willow Bats", "Leather Balls", "Tennis Balls", 
                    "Bat Grips", "Helmets", "Batting Pads", "WK Pads", "Batting Gloves", "WK Gloves",
                    "Thigh Guards", "Chest Guards", "Arm Guards", "Abdo Guards", "Inner Gloves",
                    "Shoes (Spikes)", "Shoes (Turf)", "Jerseys", "Trousers", "Socks",
                    "Wheelie Bags", "Duffle Bags", "Stumps", "Bails", "Umpire Counters",
                    "Training Nets", "Bowling Machines", "Boundary Markers", "Bat Oil", "Grip Cones"
                ])
                sku = st.text_input("SKU / Barcode")
            
            with col2:
                cost = st.number_input("Cost Price", min_value=0.0, step=0.1)
                sell = st.number_input("Selling Price", min_value=0.0, step=0.1)
                ship = st.number_input("Shipping Cost", min_value=0.0, step=0.1)
                vendor = st.text_input("Vendor/Supplier")
                p_date = st.date_input("Purchase Date", datetime.now())

            if st.form_submit_button("Save Item to Inventory"):
                if item_name and sku:
                    try:
                        c.execute('''INSERT INTO inventory 
                                     (name, brand, category, sku, cost, vendor, p_date, sell_price, shipping) 
                                     VALUES (?,?,?,?,?,?,?,?,?)''', 
                                  (item_name, brand, category, sku, cost, vendor, p_date, sell, ship))
                        conn.commit()
                        st.success(f"Added {item_name} successfully!")
                    except sqlite3.IntegrityError:
                        st.error("Error: This SKU already exists!")
                else:
                    st.warning("Please enter at least a Name and SKU.")

    # --- SEARCH & VIEW SECTION ---
    st.divider()
    search = st.text_input("🔍 Search Stock (Name or SKU)")
    query = f"SELECT * FROM inventory WHERE name LIKE '%{search}%' OR sku LIKE '%{search}%' ORDER BY id DESC"
    df = pd.read_sql(query, conn)
    
    # Formatting for mobile display
    st.dataframe(df[['name', 'brand', 'category', 'sku', 'sell_price']], use_container_width=True)

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
