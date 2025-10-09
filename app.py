# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Warpage Comparison", layout="wide")
st.title("Warpage 데이터 비교 (품질팀 vs D.sol)")

# -----------------------------
# 1️⃣ Spec 입력
# -----------------------------
spec_value = st.number_input("제품별 Warpage Spec 값 (um):", min_value=0, value=30, step=1)

# -----------------------------
# 2️⃣ 파일 업로드
# -----------------------------
st.subheader("CSV 파일 업로드")
quality_file = st.file_uploader("품질팀 CSV 파일 업로드 (part no / warpage(um))", type="csv", key="q")
dsol_file = st.file_uploader("D.sol CSV 파일 업로드 (part no / warpage(um))", type="csv", key="d")

# -----------------------------
# 3️⃣ 파일 처리
# -----------------------------
if quality_file and dsol_file:
    try:
        # CSV 인코딩 대응 (UTF-8 BOM, 일반 UTF-8, ANSI)
        try:
            q_df = pd.read_csv(quality_file, encoding='utf-8-sig')
            d_df = pd.read_csv(dsol_file, encoding='utf-8-sig')
        except:
            q_df = pd.read_csv(quality_file, encoding='latin1')
            d_df = pd.read_csv(dsol_file, encoding='latin1')

        # 컬럼명 공백 제거 + 소문자 변환
        q_df.columns = q_df.columns.str.strip().str.lower()
        d_df.columns = d_df.columns.str.strip().str.lower()

        # 컬럼명 체크
        if 'part no' not in q_df.columns or 'warpage(um)' not in q_df.columns:
            st.error("품질팀 CSV 컬럼명을 확인하세요: part no / warpage(um)")
        elif 'part no' not in d_df.columns or 'warpage(um)' not in d_df.columns:
            st.error("D.sol CSV 컬럼명을 확인하세요: part no / warpage(um)")
        else:
            # warpage 절댓값 처리
            q_df['warpage(um)'] = q_df['warpage(um)'].abs()
            d_df['warpage(um)'] = d_df['warpage(um)'].abs()

            # -----------------------------
            # 4️⃣ 통계값 계산
            # -----------------------------
            def calc_stats(df, spec):
                mean = df['warpage(um)'].mean()
                std = df['warpage(um)'].std()
                max_val = df['warpage(um)'].max()
                min_val = df['warpage(um)'].min()
                cpk = min((spec - mean)/(3*std), mean/(3*std)) if std != 0 else np.nan
                return pd.Series([mean, std, max_val, min_val, cpk], index=['평균','표준편차','최댓값','최솟값','CpK'])

            q_stats = calc_stats(q_df, spec_value)
            d_stats = calc_stats(d_df, spec_value)

            st.subheader("품질팀 / D.sol 통계값")
            stats_df = pd.DataFrame({'품질팀': q_stats, 'D.sol': d_stats})
            st.dataframe(stats_df)

            # -----------------------------
            # 5️⃣ Spec 초과 시료
            # -----------------------------
            q_over = q_df[q_df['warpage(um)']>spec_value]
            d_over = d_df[d_df['warpage(um)']>spec_value]

            st.subheader("Spec 초과 시료")
            st.write("품질팀")
            st.dataframe(q_over)
            st.write("D.sol")
            st.dataframe(d_over)

            # -----------------------------
            # 6️⃣ 데이터 합치기 & Δ값, 비교 가능/불가
            # -----------------------------
            merged = pd.merge(q_df, d_df, on='part no', how='outer', suffixes=('_품질','_Dsol'))
            merged['비교 가능'] = np.where(merged['warpage(um)_품질'].isna() | merged['warpage(um)_Dsol'].isna(), '비교불가', '비교가능')
            merged['Δ(D.sol-품질)'] = np.where(
                merged['비교 가능']=='비교가능',
                merged['warpage(um)_Dsol'] - merged['warpage(um)_품질'],
                np.nan
            )

            comp_df = merged[merged['비교 가능']=='비교가능']

            # -----------------------------
            # 7️⃣ Part No별 이중막대 그래프 (Spec 초과 시 빨강)
            # -----------------------------
            colors_q = ['red' if val > spec_value else 'blue' for val in merged['warpage(um)_품질']]
            colors_d = ['red' if val > spec_value else 'green' for val in merged['warpage(um)_Dsol']]

            fig = go.Figure(data=[
                go.Bar(
                    x=merged['part no'],
                    y=merged['warpage(um)_품질'],
                    name='품질팀',
                    marker_color=colors_q
                ),
                go.Bar(
                    x=merged['part no'],
                    y=merged['warpage(um)_Dsol'],
                    name='D.sol',
                    marker_color=colors_d
                )
            ])
            fig.add_hline(y=spec_value, line_dash="dash", line_color="black", annotation_text="Spec", annotation_position="top left")
            fig.update_layout(title="Part No별 Warpage 비교", xaxis_title="Part No", yaxis_title="Warpage (um)", barmode='group')
            st.plotly_chart(fig, use_container_width=True)

            # -----------------------------
            # 8️⃣ Δ값 히스토그램
            # -----------------------------
            st.subheader("Δ값 히스토그램 (D.sol - 품질팀)")
            fig_delta = px.histogram(
                comp_df,
                x='Δ(D.sol-품질)',
                nbins=20,
                title="Δ값 분포 (D.sol - 품질팀)",
                labels={'Δ(D.sol-품질)': 'Δ Warpage (um)'}
            )
            fig_delta.add_vline(x=0, line_dash="dash", line_color="black", annotation_text="Δ=0", annotation_position="top left")
            st.plotly_chart(fig_delta, use_container_width=True)

            # -----------------------------
            # 9️⃣ 상관도 산점도
            # -----------------------------
            corr = comp_df[['warpage(um)_품질','warpage(um)_Dsol']].corr().iloc[0,1]

            st.subheader("품질팀 vs D.sol 상관도")
            fig_corr = px.scatter(
                comp_df,
                x='warpage(um)_품질',
                y='warpage(um)_Dsol',
                labels={'warpage(um)_품질':'품질팀 Warpage (um)', 'warpage(um)_Dsol':'D.sol Warpage (um)'},
                title=f"상관도 산점도 (corr={corr:.3f})"
            )
            fig_corr.add_shape(
                type="line",
                x0=0, y0=0,
                x1=comp_df[['warpage(um)_품질','warpage(um)_Dsol']].max().max(),
                y1=comp_df[['warpage(um)_품질','warpage(um)_Dsol']].max().max(),
                line=dict(color="red", dash="dash")
            )
            st.plotly_chart(fig_corr, use_container_width=True)

            # -----------------------------
            # 10️⃣ 데이터 정합성 판단
            # -----------------------------
            delta_mean = comp_df['Δ(D.sol-품질)'].mean()
            delta_std = comp_df['Δ(D.sol-품질)'].std()

            st.subheader("데이터 정합성 판단")
            st.write(f"Δ값 평균: {delta_mean:.2f}, Δ값 표준편차: {delta_std:.2f}, 품질 vs D.sol 상관계수: {corr:.3f}")

            if corr >= 0.9 and abs(delta_mean) < spec_value*0.05:
                st.success("두 팀 데이터 정합성 높음: 신뢰 가능")
            elif corr >= 0.7:
                st.warning("데이터 일부 편차 존재: 일부 재측정 권장")
            else:
                st.error("데이터 편차 큼: 재측정 필요")

    except Exception as e:
        st.error(f"파일 처리 중 오류 발생: {e}")
