import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.title("📏 Warpage Data Correlation Tool")

st.write("""
품질팀 & 개발팀 warpage 데이터를 비교하여 Δ값, 통계, Cpk를 자동 계산합니다.
""")

# --- Spec 입력 ---
spec = st.number_input("📌 제품 Warpage Spec (um 단위)", min_value=0.0, value=30.0)

# --- 파일 업로드 ---
st.subheader("1️⃣ 품질팀 데이터 업로드")
quality_file = st.file_uploader("품질팀 Excel 파일 업로드 (.xlsx, 컬럼: part no / warpage(um))", type="xlsx", key="q")

st.subheader("2️⃣ 개발팀 데이터 업로드")
dev_file = st.file_uploader("개발팀 Excel 파일 업로드 (.xlsx, 컬럼: part no / warpage(um))", type="xlsx", key="d")

if quality_file and dev_file:
    q_df = pd.read_excel(quality_file)
    d_df = pd.read_excel(dev_file)

    # 컬럼 이름 통일
    q_df.columns = q_df.columns.str.lower().str.strip()
    d_df.columns = d_df.columns.str.lower().str.strip()

    # 절댓값 변환
    q_df["warpage(um)"] = q_df["warpage(um)"].abs()
    d_df["warpage(um)"] = d_df["warpage(um)"].abs()

    # inner join
    merged = pd.merge(q_df, d_df, on="part no", suffixes=("_품질", "_개발"), how="outer")

    # 비교불가 표시
    merged["비교가능여부"] = np.where(
        merged["warpage(um)_품질"].notna() & merged["warpage(um)_개발"].notna(), "비교가능", "비교불가"
    )

    # Δ값 계산
    merged["Δ(개발-품질)"] = merged["warpage(um)_개발"] - merged["warpage(um)_품질"]

    # 통계 계산
    comp_df = merged[merged["비교가능여부"] == "비교가능"]
    deltas = comp_df["Δ(개발-품질)"]

    if not deltas.empty:
        mean = deltas.mean()
        std = deltas.std()
        min_v = deltas.min()
        max_v = deltas.max()
        cpk = (spec - abs(mean)) / (3 * std) if std > 0 else np.nan

        st.write("### 📊 Δ(개발-품질) 통계 결과")
        st.metric("평균 Δ", round(mean, 2))
        st.metric("표준편차", round(std, 2))
        st.metric("최댓값", round(max_v, 2))
        st.metric("최솟값", round(min_v, 2))
        st.metric("Cpk (Spec 기준)", round(cpk, 3))

    # 표 보기
    st.write("### 🔍 비교 결과 테이블")
    st.dataframe(merged)

    # Δ값 분포 그래프
    st.write("### 📈 Δ 분포 그래프")
    st.bar_chart(deltas)

    # 다운로드 기능
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        merged.to_excel(writer, index=False, sheet_name="결과")
    st.download_button(
        label="📥 비교 결과 Excel 다운로드",
        data=output.getvalue(),
        file_name="warpage_comparison.xlsx"
    )

else:
    st.info("👆 품질팀 및 개발팀 데이터를 업로드해주세요.")
