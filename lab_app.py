import streamlit as st
import pandas as pd
import re
import plotly.express as px

# ল্যাবের নাম ক্লিন করার ফাংশন
def clean_lab_name(name):
    if pd.isna(name) or str(name).strip().upper() in ["SELF", "NaN", ""]:
        return "OTHERS"
    return str(name).strip().upper()

st.set_page_config(page_title="Lab Referral Calculator", layout="wide")
st.title("🔬 Lab Referral Payout System")
st.markdown("---")

uploaded_file = st.file_uploader("Upload your 'Procedure.xlsx' file", type=["xlsx"])

if uploaded_file:
    try:
        # ৩য় শিট (Other Lab Ref.) লোড করা
        df = pd.read_excel(uploaded_file, sheet_name=2) 
        
        # কলাম ক্লিনআপ
        df.columns = [str(c).strip() for c in df.columns]
        
        # আপনার শিট অনুযায়ী কলামের নাম সেট করা
        lab_col = "Other Lab Refer"
        gross_col = "Gross Amount"
        disc_col = "Discount"
        
        if lab_col in df.columns and gross_col in df.columns:
            # ডাটা টাইপ ঠিক করা
            df[gross_col] = pd.to_numeric(df[gross_col], errors='coerce').fillna(0)
            df[disc_col] = pd.to_numeric(df[disc_col], errors='coerce').fillna(0)
            
            # ল্যাবের নাম ক্লিন করা এবং SELF/Empty ডাটা বাদ দেওয়া
            df['Cleaned_Lab'] = df[lab_col].apply(clean_lab_name)
            df = df[df['Cleaned_Lab'] != "OTHERS"]
            
            # ১. ক্যালকুলেশন লজিক
            df['Net Amount'] = df[gross_col] - df[disc_col]
            df['Discount_Pct'] = (df[disc_col] / df[gross_col].replace(0, 1)) * 100
            
            def calculate_referral(row):
                # ডক্টর রেফারালের মতো একই লজিক (২৫% এর বেশি হলে ০)
                if row['Discount_Pct'] > 25:
                    return 0.0
                else:
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
            c1.metric("Total Gross Billing", f"₹ {display_df[gross_col].sum():,.2f}")
            c2.metric("Total Net Billing", f"₹ {display_df['Net Amount'].sum():,.2f}")
            c3.metric("Final Payable Referral", f"₹ {display_df['Referral Amount'].sum():,.2f}")

            # চার্ট
            st.divider()
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.subheader("Top Labs by Referral")
                top_labs = df.groupby('Cleaned_Lab')['Referral Amount'].sum().nlargest(10).reset_index()
                st.plotly_chart(px.bar(top_labs, x='Referral Amount', y='Cleaned_Lab', orientation='h', color='Referral Amount'), use_container_width=True)
            with col_chart2:
                st.subheader("Referral Breakdown")
                st.plotly_chart(px.pie(display_df, values='Referral Amount', names='Cleaned_Lab', hole=0.4), use_container_width=True)

            # বিস্তারিত ডাটা টেবিল
            st.subheader(f"Detailed Logs: {selected_lab}")
            st.dataframe(
                display_df[['Cleaned_Lab', gross_col, disc_col, 'Net Amount', 'Discount_Pct', 'Referral Amount']]
                .style.format(precision=2), 
                use_container_width=True
            )

            # ডাউনলোড
            summary = df.groupby('Cleaned_Lab').agg({gross_col:'sum', 'Net Amount':'sum', 'Referral Amount':'sum'}).reset_index().sort_values('Referral Amount', ascending=False)
            st.download_button("📥 Download Lab Referral Report (CSV)", summary.to_csv(index=False).encode('utf-8'), "Lab_Referral_Summary.csv", "text/csv")

        else:
            st.error(f"কলাম খুঁজে পাওয়া যায়নি! নিশ্চিত করুন ৩য় শিটে '{lab_col}' কলামটি আছে।")
            
    except Exception as e:
        st.error(f"Error: {e}")
