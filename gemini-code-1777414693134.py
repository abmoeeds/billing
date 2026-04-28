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
    
    
    st.subheader("Recent Sales & Customer History")
    # We select the 'vendor' column because that's where we saved the Customer Name
    # We rename it to 'Details' for clarity on the screen
    display_df = sales[['sale_date', 'name', 'brand', 'sku', 'vendor', 'sell_price', 'profit']].copy()
    display_df.columns = ['Date', 'Item', 'Brand', 'SKU', 'Vendor/Customer', 'Sold Price', 'Profit']
    
    st.dataframe(display_df.sort_values(by="Date", ascending=False), use_container_width=True)


elif page == "Inventory Management":
    st.header("🛒 Sales & Inventory")

    # Initialize a 'Cart' in the mobile session if it doesn't exist
    if 'cart' not in st.session_state:
        st.session_state.cart = []

    # --- SECTION 1: CUSTOMER & SEARCH ---
    with st.container():
        st.subheader("Create New Sale")
        cust_name = st.text_input("👤 Customer Name", placeholder="Enter customer name")
        
        search_item = st.text_input("🔍 Search Item to Add (Name or SKU)")
        
        if search_item:
            # Search available stock
            query = f"SELECT * FROM inventory WHERE (name LIKE '%{search_item}%' OR sku LIKE '%{search_item}%') AND sale_date IS NULL LIMIT 5"
            results = pd.read_sql(query, conn)
            
            for index, row in results.iterrows():
                col1, col2 = st.columns([3, 1])
                col1.write(f"**{row['name']}** ({row['sku']}) - ${row['sell_price']}")
                if col2.button("➕ Add", key=f"add_{row['id']}"):
                    # Add item details to session cart
                    st.session_state.cart.append({
                        'id': row['id'],
                        'name': row['name'],
                        'sku': row['sku'],
                        'price': row['sell_price'],
                        'brand': row['brand'],
                        'vendor': row['vendor']
                    })
                    st.toast(f"Added {row['name']} to cart!")

    # --- SECTION 2: THE SHOPPING CART (Basket) ---
    if st.session_state.cart:
        st.divider()
        st.subheader("🛍️ Current Basket")
        for i, item in enumerate(st.session_state.cart):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"{item['name']} ({item['sku']})")
            c2.write(f"${item['price']}")
            if c3.button("❌", key=f"remove_{i}"):
                st.session_state.cart.pop(i)
                st.rerun()
        
        total_bill = sum(item['price'] for item in st.session_state.cart)
        st.write(f"### Total: ${total_bill:,.2f}")

        if st.button("✅ Confirm & Finalize Sale", use_container_width=True):
            if not cust_name:
                st.error("Please enter a Customer Name before finalizing.")
            else:
                sale_date_today = datetime.now().strftime('%Y-%m-%d')
                # Process every item in the cart
                for item in st.session_state.cart:
                    # Note: We are using the 'vendor' field to store customer name for sold items 
                    # OR you can alter your DB to add a customer column.
                    # For now, let's update sale_date and we can use a custom query for reports.
                    c.execute('''UPDATE inventory 
                                 SET sale_date = ?, vendor = vendor || ' | Customer: ' || ? 
                                 WHERE id = ?''', 
                              (sale_date_today, cust_name, item['id']))
                
                conn.commit()
                st.session_state.cart = [] # Clear cart
                st.success(f"Sale completed for {cust_name}!")
                st.rerun()

    # --- SECTION 3: ADD NEW STOCK ---
    st.divider()
    with st.expander("➕ Add New Stock to Shop", expanded=False):
        with st.form("manual_add"):
            c1, c2 = st.columns(2)
            with c1:
                name = st.text_input("Item Name")
                brd = st.text_input("Brand")
                cat = st.selectbox("Category", ["Bats", "Balls", "Pads", "Gloves", "Helmets", "Shoes", "Bags", "Other"])
                sku_code = st.text_input("SKU")
            with c2:
                cp = st.number_input("Cost Price")
                sp = st.number_input("Sell Price")
                sh = st.number_input("Shipping")
                vn = st.text_input("Vendor Name")
            if st.form_submit_button("Save to Inventory"):
                c.execute("INSERT INTO inventory (name, brand, category, sku, cost, vendor, sell_price, shipping) VALUES (?,?,?,?,?,?,?,?)",
                          (name, brd, cat, sku_code, cp, vn, sp, sh))
                conn.commit()
                st.success("Added!")

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
