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
    
    # --- FULL DATA ENTRY FORM ---
    with st.expander("➕ Add New Stock (Manual Entry)", expanded=True):
        with st.form("comprehensive_add_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                new_name = st.text_input("Item Name (e.g. Master-5000 Bat)")
                new_brand = st.text_input("Brand (e.g. SS, SG, Kookaburra)")
                new_cat = st.selectbox("Category", [
                    "English Willow Bats", "Kashmir Willow Bats", "Leather Balls", "Tennis Balls", 
                    "Batting Pads", "WK Pads", "Batting Gloves", "WK Gloves", "Helmets", 
                    "Shoes (Spikes)", "Shoes (Turf)", "Kit Bags", "Stumps", "Other"
                ])
                new_sku = st.text_input("SKU / Barcode Base")
                new_vendor = st.text_input("Vendor / Supplier Name")
            
            with col2:
                new_cost = st.number_input("Cost Price (Per Item)", min_value=0.0, format="%.2f")
                new_sell = st.number_input("Selling Price (Per Item)", min_value=0.0, format="%.2f")
                new_ship = st.number_input("Shipping Cost (Per Item)", min_value=0.0, format="%.2f")
                new_qty = st.number_input("Quantity to Add", min_value=1, max_value=100, value=1)
                new_date = st.date_input("Purchase Date", datetime.now())

            submit_btn = st.form_submit_button("📥 Save to Inventory")

            if submit_btn:
                if new_name and new_sku:
                    try:
                        # Loop to handle Quantity
                        for i in range(new_qty):
                            # If quantity > 1, we append a number to the SKU to keep them unique
                            final_sku = f"{new_sku}-{i+1}" if new_qty > 1 else new_sku
                            
                            c.execute('''INSERT INTO inventory 
                                         (name, brand, category, sku, cost, vendor, p_date, sell_price, shipping) 
                                         VALUES (?,?,?,?,?,?,?,?,?)''', 
                                      (new_name, new_brand, new_cat, final_sku, new_cost, new_vendor, new_date, new_sell, new_ship))
                        
                        conn.commit()
                        st.success(f"Successfully added {new_qty} items of '{new_name}' to stock!")
                    except sqlite3.IntegrityError:
                        st.error("Error: This SKU already exists in the database. Please use a unique SKU.")
                else:
                    st.warning("Item Name and SKU are required fields.")

# --- STOCK VISUALIZATION ---
    st.divider()
    st.subheader("📋 Stock Levels (Available)")
    
    # This query groups identical items by Name and Brand to show you the count
    summary_query = """
        SELECT name, brand, category, sell_price, COUNT(*) as qty_left 
        FROM inventory 
        WHERE sale_date IS NULL 
        GROUP BY name, brand, category, sell_price
    """
    df_summary = pd.read_sql(summary_query, conn)
    
    if not df_summary.empty:
        # Highlight low stock (optional)
        st.dataframe(df_summary, use_container_width=True)
        st.info(f"💡 You have {df_summary['qty_left'].sum()} total items across {len(df_summary)} different products.")
    else:
        st.warning("⚠️ Warehouse is empty! Add new stock above.")

    # --- DETAILED SKU LIST ---
    with st.expander("View Individual SKUs (Serial Numbers)"):
        df_all = pd.read_sql("SELECT name, sku, vendor, p_date FROM inventory WHERE sale_date IS NULL", conn)
        st.dataframe(df_all, use_container_width=True)

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
