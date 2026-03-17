import streamlit as st
import pandas as pd
import re
import plotly.express as px

# ল্যাবের নাম ক্লিন করার ফাংশন
def clean_lab_name(name):
    if pd.isna(name) or str(name).strip().upper() in ["SELF", "NAN", ""]:
        return "OTHERS"
    return str(name).strip().upper()

# নাম একদম নিখুঁতভাবে এক করার ফাংশন (Exclusion এর জন্য)
def super_clean(text):
    if pd.isna(text): return ""
    text = re.sub(r'^(dr\.|dr|dr )', '', str(text), flags=re.IGNORECASE)
    cleaned = re.sub(r'[^A-Z]', '', text.upper()) 
    return cleaned

st.set_page_config(page_title="Lab Referral Calculator", layout="wide")
st.title("🔬 Lab Referral Payout System")
st.markdown("---")

uploaded_file = st.file_uploader("Upload your 'Other Lab Ref..xlsx' file", type=["xlsx"])

if uploaded_file:
    try:
        # শিট লোড করা (আপনার নতুন ফাইলে ১ম শিটেই ডাটা আছে)
        df = pd.read_excel(uploaded_file) 
        
        # কলাম ক্লিনআপ
        df.columns = [str(c).strip() for c in df.columns]
        
        # আপনার শিট অনুযায়ী কলামের নাম খোঁজা
        lab_col = next((c for c in df.columns if 'other lab refer' in c.lower()), None)
        gross_col = next((c for c in df.columns if 'gross amount' in c.lower()), None)
        disc_col = next((c for c in df.columns if 'discount' in c.lower()), None)
        
        if lab_col and gross_col:
            # ডাটা টাইপ ঠিক করা
            df[gross_col] = pd.to_numeric(df[gross_col], errors='coerce').fillna(0)
            df[disc_col] = pd.to_numeric(df[disc_col], errors='coerce').fillna(0)
            
            # ল্যাবের নাম ক্লিন করা
            df['Cleaned_Lab'] = df[lab_col].apply(clean_lab_name)
            df['Lab_ID'] = df[lab_col].apply(super_clean)
            
            # রোহিত রুংটা ও রোহিত ঘুটগুটিয়াকে বাদ দেওয়া
            exclude_ids = ["ROHITGHUTGUTIYA", "ROHITRUNGTA", "ROHITRUNQTA"]
            df = df[~df['Lab_ID'].isin(exclude_ids)]
            df = df[df['Cleaned_Lab'] != "OTHERS"]
            
            # ১. ক্যালকুলেশন লজিক
            df['Net Amount'] = df[gross_col] - df[disc_col]
            df['Discount_Pct'] = (df[disc_col] / df[gross_col].replace(0, 1)) * 100
            
            def calculate_referral(row):
                # আপনার দেওয়া লজিক: ২৫% এর বেশি ডিসকাউন্ট হলে ০
                if row['Discount_Pct'] > 25:
                    return 0.0
                else:
                    # ব্যালেন্স পার্সেন্টেজ লজিক
                    balance_pct = (25 - row['Discount_Pct']) / 100
                    return row['Net Amount'] * balance_pct

            df['Referral Amount'] = df.apply(calculate_referral, axis=1)

            # --- ড্যাশবোর্ড ---
            st.sidebar.header("Filter Options")
            lab_list = ["Show All Labs"] + sorted(df['Cleaned_Lab'].unique().tolist())
            selected_lab = st.sidebar.selectbox("🔍 Select Lab Name:", lab_list)

            if selected_lab == "Show All Labs":
                display_df = df
            else:
                display_df = df[df['Cleaned_Lab'] == selected_lab]

            # মেট্রিক্স কার্ড
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Gross Amount", f"₹ {display_df[gross_col].sum():,.2f}")
            c2.metric("Total Net Billing", f"₹ {display_df['Net Amount'].sum():,.2f}")
            c3.metric("Final Payable Referral", f"₹ {display_df['Referral Amount'].sum():,.2f}")

            # চার্ট
            st.divider()
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.subheader("Top Labs by Referral")
                top_labs = df.groupby('Cleaned_Lab')['Referral Amount'].sum().nlargest(10).reset_index()
                fig = px.bar(top_labs, x='Referral Amount', y='Cleaned_Lab', orientation='h', color='Referral Amount')
                st.plotly_chart(fig, use_container_width=True)
            with col_chart2:
                st.subheader("Referral Distribution")
                pie_data = display_df.groupby('Cleaned_Lab')['Referral Amount'].sum().reset_index()
                fig2 = px.pie(pie_data, values='Referral Amount', names='Cleaned_Lab', hole=0.4)
                st.plotly_chart(fig2, use_container_width=True)

            # বিস্তারিত ডাটা টেবিল
            st.subheader(f"Detailed Logs: {selected_lab}")
            st.dataframe(
                display_df[['Cleaned_Lab', gross_col, disc_col, 'Net Amount', 'Discount_Pct', 'Referral Amount']]
                .style.format(precision=2), 
                use_container_width=True
            )

            # ডাউনলোড
            summary = df.groupby('Cleaned_Lab').agg({gross_col:'sum', 'Net Amount':'sum', 'Referral Amount':'sum'}).reset_index().sort_values('Referral Amount', ascending=False)
            st.download_button("📥 Download Report (CSV)", summary.to_csv(index=False).encode('utf-8'), "Lab_Summary.csv", "text/csv")

        else:
            st.error("ফাইলে প্রয়োজনীয় কলাম পাওয়া যায়নি। দয়া করে কলামের নাম চেক করুন।")
            
    except Exception as e:
        st.error(f"Error: {e}")
