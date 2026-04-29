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

    if 'cart' not in st.session_state:
        st.session_state.cart = []

    # --- 1. CUSTOMER & PAYMENT INFO ---
    with st.container():
        c1, c2 = st.columns(2)
        with c1:
            cust_name = st.text_input("👤 Customer Name")
        with c2:
            pay_method = st.selectbox("💳 Payment Method", ["Cash", "Card", "Bank Transfer", "UPI/QR"])
    
    # --- 2. SEARCH & ADD TO BASKET ---
    search_item = st.text_input("🔍 Search Item (Name or SKU)")
    if search_item:
        # We find available items
        query = f"SELECT * FROM inventory WHERE (name LIKE '%{search_item}%' OR sku LIKE '%{search_item}%') AND sale_date IS NULL LIMIT 5"
        results = pd.read_sql(query, conn)
        
        for index, row in results.iterrows():
            with st.expander(f"➕ Add {row['name']} ({row['sku']})"):
                col_q, col_d, col_b = st.columns([1, 1, 1])
                qty = col_q.number_input("Qty", min_value=1, value=1, key=f"q_{row['id']}")
                disc = col_d.number_input("Discount ($)", min_value=0.0, value=0.0, key=f"d_{row['id']}")
                
                if col_b.button("Add to Basket", key=f"btn_{row['id']}"):
                    # Logic: We find 'qty' number of items with the same name/sku that are unsold
                    find_others = pd.read_sql(f"SELECT id FROM inventory WHERE name = '{row['name']}' AND sale_date IS NULL LIMIT {qty}", conn)
                    
                    if len(find_others) < qty:
                        st.error(f"Only {len(find_others)} in stock!")
                    else:
                        st.session_state.cart.append({
                            'ids': find_others['id'].tolist(),
                            'name': row['name'],
                            'price': row['sell_price'],
                            'qty': qty,
                            'discount': disc,
                            'total': (row['sell_price'] * qty) - disc
                        })
                        st.toast("Added to basket!")
                        st.rerun()

    # --- 3. THE BASKET (RECEIPT PREVIEW) ---
    if st.session_state.cart:
        st.divider()
        st.subheader("🛒 Basket Summary")
        
        for i, item in enumerate(st.session_state.cart):
            col_a, col_b, col_c = st.columns([3, 1, 1])
            col_a.write(f"**{item['name']}** \n{item['qty']} x ${item['price']} (Disc: -${item['discount']})")
            col_b.write(f"**${item['total']:,.2f}**")
            if col_c.button("❌", key=f"del_{i}"):
                st.session_state.cart.pop(i)
                st.rerun()
        
        grand_total = sum(item['total'] for item in st.session_state.cart)
        st.markdown(f"## Total to Pay: **${grand_total:,.2f}**")
        st.info(f"Payment via: {pay_method}")

        if st.button("🏁 Finalize Sale & Deduct Stock", use_container_width=True):
            if cust_name:
                sale_date_today = datetime.now().strftime('%Y-%m-%d')
                for item in st.session_state.cart:
                    for item_id in item['ids']:
                        # We store Customer + Payment + Discount info in the vendor field for tracking
                        note = f"Cust: {cust_name} | Pay: {pay_method} | Disc: {item['discount']/item['qty']}"
                        c.execute("UPDATE inventory SET sale_date = ?, vendor = ? WHERE id = ?", 
                                  (sale_date_today, note, item_id))
                conn.commit()
                st.session_state.cart = []
                st.success("Sale Completed Successfully!")
                st.balloons()
            else:
                st.error("Please enter a Customer Name")
