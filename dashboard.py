import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ── 페이지 설정 ──────────────────────────────────────────
st.set_page_config(
    page_title="개인정보위 보도자료 분석",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS (다크모드) ────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #e6edf3; }
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] p { color: #c9d1d9 !important; }

    /* 입력 필드 */
    .stTextInput input, .stSelectbox select {
        background-color: #21262d !important;
        color: #e6edf3 !important;
        border: 1px solid #30363d !important;
    }

    /* KPI 카드 */
    .kpi-card {
        background: #161b22;
        border-radius: 12px;
        padding: 20px 24px;
        border: 1px solid #30363d;
        border-left: 4px solid #388bfd;
    }
    .kpi-label { font-size: 12px; color: #8b949e; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.05em; }
    .kpi-value { font-size: 26px; font-weight: 700; color: #e6edf3; }
    .kpi-delta { font-size: 13px; margin-top: 6px; }
    .kpi-delta.up   { color: #f85149; }
    .kpi-delta.down { color: #3fb950; }
    .kpi-delta.neu  { color: #8b949e; }

    /* 섹션 타이틀 */
    .section-title {
        font-size: 15px; font-weight: 700;
        color: #e6edf3;
        margin: 16px 0 12px 0;
        padding-left: 10px;
        border-left: 3px solid #388bfd;
    }

    /* 키워드 배지 */
    .badge {
        display: inline-block;
        background: #1c2333;
        color: #79c0ff;
        border: 1px solid #388bfd44;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 12px;
        margin: 2px;
    }

    /* 보도자료 테이블 */
    .table { width: 100%; border-collapse: collapse; font-size: 13px; color: #c9d1d9; }
    .table th { background: #1c2333; padding: 9px 12px; text-align: left; color: #8b949e; font-weight: 600; border-bottom: 1px solid #30363d; }
    .table td { padding: 8px 12px; border-bottom: 1px solid #21262d; vertical-align: top; }
    .table tr:hover td { background: #1c2333; }
    .table a { color: #388bfd; text-decoration: none; }
    .table a:hover { text-decoration: underline; }

    /* 구분선 */
    hr { border-color: #30363d !important; }

    /* 탭 */
    .stTabs [data-baseweb="tab-list"] { background: #161b22; border-bottom: 1px solid #30363d; }
    .stTabs [data-baseweb="tab"] { color: #8b949e; }
    .stTabs [aria-selected="true"] { color: #e6edf3 !important; border-bottom: 2px solid #388bfd !important; }

    h1, h2, h3 { color: #e6edf3 !important; }
    p, li { color: #c9d1d9; }
</style>
""", unsafe_allow_html=True)

# ── Plotly 다크 테마 기본값 ───────────────────────────────
DARK_LAYOUT = dict(
    plot_bgcolor="#0d1117",
    paper_bgcolor="#161b22",
    font_color="#c9d1d9",
    xaxis=dict(gridcolor="#21262d", linecolor="#30363d", tickcolor="#8b949e"),
    yaxis=dict(gridcolor="#21262d", linecolor="#30363d", tickcolor="#8b949e"),
    legend=dict(
        bgcolor="#1c2333",
        bordercolor="#30363d",
        borderwidth=1,
        font_color="#c9d1d9",
    ),
)

# ── 데이터 로드 ───────────────────────────────────────────
@st.cache_data
def load_data_from_source(src, _cache_key):
    """파일경로(str) 또는 BytesIO 모두 처리"""
    import io
    if isinstance(src, str):
        df = pd.read_csv(src)
    else:
        src.seek(0)
        df = pd.read_csv(src)
    df["date"]       = pd.to_datetime(df["date"], errors="coerce")
    df["year"]       = df["year"].astype(int)
    df["year_month"] = df["year_month"].astype(str)
    df["views"]      = pd.to_numeric(df["views"], errors="coerce").fillna(0).astype(int)
    df["kw_list"]    = df["cluster_top_keywords"].apply(
        lambda x: [k.strip() for k in str(x).split(",")][:3]
    )
    kw_map = (
        df.groupby("cluster")["cluster_top_keywords"]
        .first()
        .apply(lambda x: " · ".join([k.strip() for k in str(x).split(",")][:2]))
    )
    df["cluster_label"] = df["cluster"].map(kw_map)
    return df

# ── 사이드바 ──────────────────────────────────────────────
ORIGINAL_PATH = "pipc_analysis_result.csv"

with st.sidebar:
    st.markdown("### ⚙️ 설정")

    # ── 데이터 업로드 & 이력 ─────────────────────────────
    # session_state 초기화
    if "data_history" not in st.session_state:
        # [(표시명, 파일경로_or_bytes, 설명)] 리스트
        st.session_state.data_history = [
            ("기본 데이터", ORIGINAL_PATH, "최초 로드")
        ]
    if "current_idx" not in st.session_state:
        st.session_state.current_idx = 0

    # 파일 업로더
    uploaded = st.file_uploader(
        "📂 데이터 업데이트",
        type=["csv"],
        help="분석이 완료된 CSV 파일을 업로드하면 대시보드에 즉시 반영됩니다.",
    )
    if uploaded is not None:
        import io
        # 같은 파일 중복 추가 방지
        existing_names = [h[0] for h in st.session_state.data_history]
        if uploaded.name not in existing_names:
            bytes_data = uploaded.read()
            st.session_state.data_history.append(
                (uploaded.name, io.BytesIO(bytes_data), f"업로드: {uploaded.name}")
            )
            st.session_state.current_idx = len(st.session_state.data_history) - 1
            st.cache_data.clear()
            st.rerun()

    # 업데이트 이력 표시 & 선택
    st.markdown(
        "<div style='font-size:11px;color:#8b949e;margin:8px 0 4px 0;'>📋 데이터 이력</div>",
        unsafe_allow_html=True,
    )
    for i, (name, _, desc) in enumerate(st.session_state.data_history):
        is_cur = (i == st.session_state.current_idx)
        label  = f"{'✅ ' if is_cur else ''}{name}"
        if st.button(label, key=f"hist_{i}", use_container_width=True,
                     type="primary" if is_cur else "secondary"):
            if not is_cur:
                st.session_state.current_idx = i
                st.cache_data.clear()
                st.rerun()

    # 현재 선택된 데이터 로드
    cur_name, cur_src, _ = st.session_state.data_history[st.session_state.current_idx]
    st.markdown("---")

    df_all = load_data_from_source(cur_src, st.session_state.current_idx)

    years = sorted(df_all["year"].unique())
    sel_years = st.multiselect("연도 필터", years, default=years)

    clusters = sorted(df_all["cluster"].unique())
    cluster_labels = {
        r["cluster"]: r["cluster_label"]
        for _, r in df_all[["cluster", "cluster_label"]].drop_duplicates().iterrows()
    }
    sel_clusters = st.multiselect(
        "클러스터 필터",
        options=clusters,
        default=clusters,
        format_func=lambda c: f"C{c}: {cluster_labels[c]}",
    )

    top_n = st.slider("상위 N개 유형 표시", 3, 10, 6)

    st.markdown("---")
    st.markdown("#### 🏷️ 클러스터 레이블 수정")
    custom_labels = {}
    for c in clusters:
        custom_labels[c] = st.text_input(
            f"C{c}", value=cluster_labels[c], key=f"lbl_{c}"
        )
    df_all["cluster_label"] = df_all["cluster"].map(custom_labels)

df = df_all[df_all["year"].isin(sel_years) & df_all["cluster"].isin(sel_clusters)].copy()

# ── 빈 필터 가드 ──────────────────────────────────────────
if not sel_years or not sel_clusters:
    st.markdown("## 🔐 개인정보위 보도자료 분석 대시보드")
    st.warning("연도 또는 유형 필터를 1개 이상 선택해주세요.")
    st.stop()

# ── 헤더 ──────────────────────────────────────────────────
st.markdown("## 🔐 개인정보위 보도자료 분석 대시보드")
st.markdown(
    f"<span style='color:#8b949e'><b>{min(sel_years)}–{max(sel_years)}</b> | 총 <b style='color:#e6edf3'>{len(df):,}건</b> 분석</span>",
    unsafe_allow_html=True,
)
st.markdown("---")

# ── KPI 카드 ──────────────────────────────────────────────
cur_year  = df["year"].max()
prev_year = cur_year - 1
n_cur     = len(df[df["year"] == cur_year])
n_prev    = len(df[df["year"] == prev_year]) if prev_year in df["year"].values else 0
yoy       = ((n_cur - n_prev) / n_prev * 100) if n_prev > 0 else None
top_article = df.loc[df["views"].idxmax()] if len(df) > 0 else None
avg_views   = int(df["views"].mean()) if len(df) > 0 else 0

def kpi(col, label, value, delta_html=""):
    col.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'{delta_html}</div>',
        unsafe_allow_html=True,
    )

c1, c2, c3, c4 = st.columns(4)
with c1:
    delta_cls = "up" if (yoy or 0) > 0 else ("down" if (yoy or 0) < 0 else "neu")
    arrow     = "▲" if (yoy or 0) > 0 else "▼"
    delta_str = (
        f'<div class="kpi-delta {delta_cls}">{arrow} 전년 대비 {abs(yoy):.1f}%</div>'
        if yoy is not None else '<div class="kpi-delta neu">전년 데이터 없음</div>'
    )
    kpi(c1, "총 보도자료 건수", f"{len(df):,}건", delta_str)
with c2:
    kpi(c2, "식별된 사고 유형", f"{df['cluster'].nunique()}개 클러스터",
        '<div class="kpi-delta neu">K-Means 군집화 결과</div>')
with c3:
    kpi(c3, "건당 평균 조회수", f"{avg_views:,}회",
        '<div class="kpi-delta neu">사회적 관심도 지표</div>')
with c4:
    if top_article is not None:
        short_title = top_article["title"][:28] + "…" if len(top_article["title"]) > 28 else top_article["title"]
        kpi(c4, "최다 조회 사고", f"{top_article['views']:,}회",
            f'<div class="kpi-delta neu">{short_title}</div>')

st.markdown("<br>", unsafe_allow_html=True)

# ── 시계열 트렌드 ─────────────────────────────────────────
st.markdown('<div class="section-title">📈 시계열 트렌드</div>', unsafe_allow_html=True)
tab1, tab2 = st.tabs(["📅 월별 발생 건수", "📊 연도별 유형 비중"])

COLORS = px.colors.qualitative.Bold

with tab1:
    monthly = (
        df.groupby(["year_month", "cluster_label"])
        .size().reset_index(name="count").sort_values("year_month")
    )
    fig_monthly = px.bar(
        monthly, x="year_month", y="count", color="cluster_label",
        labels={"year_month": "연월", "count": "건수", "cluster_label": "유형"},
        color_discrete_sequence=COLORS,
    )
    fig_monthly.update_layout(
        barmode="stack", height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    bgcolor="#1c2333", bordercolor="#30363d", borderwidth=1, font_color="#c9d1d9"),
        margin=dict(t=40, b=40),
        xaxis=dict(tickangle=-45, gridcolor="#21262d", linecolor="#30363d", tickcolor="#8b949e"),
        yaxis=dict(gridcolor="#21262d", linecolor="#30363d"),
        **{k: v for k, v in DARK_LAYOUT.items() if k not in ("xaxis", "yaxis", "legend")},
    )
    st.plotly_chart(fig_monthly, use_container_width=True)

with tab2:
    yearly = df.groupby(["year", "cluster_label"]).size().reset_index(name="count")
    yearly["pct"] = (yearly["count"] / yearly.groupby("year")["count"].transform("sum") * 100).round(1)
    fig_yearly = px.bar(
        yearly, x="year", y="pct", color="cluster_label",
        labels={"year": "연도", "pct": "비중 (%)", "cluster_label": "유형"},
        color_discrete_sequence=COLORS, text="pct",
    )
    fig_yearly.update_traces(texttemplate="%{text:.0f}%", textposition="inside")
    fig_yearly.update_layout(
        barmode="stack", height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    bgcolor="#1c2333", bordercolor="#30363d", borderwidth=1, font_color="#c9d1d9"),
        margin=dict(t=40, b=40),
        yaxis=dict(range=[0, 105], gridcolor="#21262d", linecolor="#30363d"),
        xaxis=dict(gridcolor="#21262d", linecolor="#30363d", dtick=1),
        **{k: v for k, v in DARK_LAYOUT.items() if k not in ("xaxis", "yaxis", "legend")},
    )
    st.plotly_chart(fig_yearly, use_container_width=True)

# 현재 연도 (완전 집계 연도 판단 기준)
current_year = pd.Timestamp.now().year

# ── 분포 & 라인차트 ───────────────────────────────────────
col_left, col_right = st.columns([1.1, 0.9])

with col_left:
    st.markdown('<div class="section-title">🗂️ 유형별 발생 건수 & 평균 조회수</div>', unsafe_allow_html=True)
    dist = (
        df.groupby("cluster_label")
        .agg(건수=("cluster", "count"), 평균조회수=("views", "mean"))
        .reset_index().sort_values("건수", ascending=False).head(top_n)
    )
    dist["평균조회수"] = dist["평균조회수"].round(0).astype(int)

    fig_dist = make_subplots(
        rows=1, cols=2,
        subplot_titles=("발생 건수", "평균 조회수"),
        horizontal_spacing=0.12,
    )
    # subplot_titles 색상 패치
    for ann in fig_dist.layout.annotations:
        ann.font.color = "#8b949e"

    bar_colors = COLORS[:top_n]
    fig_dist.add_trace(go.Bar(
        x=dist["건수"], y=dist["cluster_label"], orientation="h",
        marker_color=bar_colors, text=dist["건수"], textposition="outside",
        textfont_color="#c9d1d9", name="건수",
    ), row=1, col=1)
    fig_dist.add_trace(go.Bar(
        x=dist["평균조회수"], y=dist["cluster_label"], orientation="h",
        marker_color=bar_colors, opacity=0.75,
        text=dist["평균조회수"].apply(lambda v: f"{v:,}"),
        textposition="outside", textfont_color="#c9d1d9", name="평균조회수",
    ), row=1, col=2)
    fig_dist.update_layout(
        height=320, showlegend=False,
        plot_bgcolor="#0d1117", paper_bgcolor="#161b22", font_color="#c9d1d9",
        margin=dict(t=40, b=10, l=10, r=20),
    )
    fig_dist.update_xaxes(showgrid=False, linecolor="#30363d", tickcolor="#8b949e")
    fig_dist.update_yaxes(showgrid=False, linecolor="#30363d", tickcolor="#8b949e")
    st.plotly_chart(fig_dist, use_container_width=True)

with col_right:
    st.markdown('<div class="section-title">📉 유형별 연도 추이 (라인차트)</div>', unsafe_allow_html=True)

    # 완전한 연도만 사용 (현재 연도 제외 — 반년치 왜곡 방지)
    current_year = pd.Timestamp.now().year
    line_df = df[df["year"] < current_year].copy()
    if line_df.empty:
        line_df = df.copy()

    line_data = (
        line_df.groupby(["year", "cluster_label"])
        .size().reset_index(name="count")
    )
    # 상위 top_n 유형만 표시 (전체 기간 합산 기준)
    top_clusters = (
        line_data.groupby("cluster_label")["count"]
        .sum().nlargest(top_n).index.tolist()
    )
    line_data = line_data[line_data["cluster_label"].isin(top_clusters)]

    fig_line = px.line(
        line_data, x="year", y="count", color="cluster_label",
        markers=True,
        labels={"year": "연도", "count": "건수", "cluster_label": "유형"},
        color_discrete_sequence=COLORS,
    )
    fig_line.update_traces(line_width=2, marker_size=7)
    fig_line.update_layout(
        height=320,
        plot_bgcolor="#0d1117", paper_bgcolor="#161b22", font_color="#c9d1d9",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    bgcolor="#1c2333", bordercolor="#30363d", borderwidth=1, font_color="#c9d1d9"),
        margin=dict(t=40, b=10, l=10, r=10),
        xaxis=dict(gridcolor="#21262d", linecolor="#30363d", tickcolor="#8b949e", dtick=1),
        yaxis=dict(gridcolor="#21262d", linecolor="#30363d", tickcolor="#8b949e"),
    )
    note_yr = f"※ {current_year}년은 데이터 미완성으로 제외"
    st.caption(note_yr)
    st.plotly_chart(fig_line, use_container_width=True)

# ── 트렌드 인사이트 ───────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-title">🔍 트렌드 인사이트 — 클러스터별 핵심 키워드</div>', unsafe_allow_html=True)

kw_data = (
    df[["cluster", "cluster_label", "cluster_top_keywords"]]
    .drop_duplicates("cluster").sort_values("cluster")
)
badge_cols = st.columns(2)
for i, (_, row) in enumerate(kw_data.iterrows()):
    keywords = [k.strip() for k in str(row["cluster_top_keywords"]).split(",")][:5]
    badges = " ".join([f'<span class="badge">{k}</span>' for k in keywords])
    with badge_cols[i % 2]:
        st.markdown(
            f"<div style='margin-bottom:12px;padding:10px 14px;background:#161b22;"
            f"border:1px solid #30363d;border-radius:8px;'>"
            f"<span style='font-size:13px;font-weight:600;color:#79c0ff'>"
            f"C{int(row['cluster'])}: {row['cluster_label']}</span><br>"
            f"<div style='margin-top:6px'>{badges}</div></div>",
            unsafe_allow_html=True,
        )

# ── 연도별 키워드 빈도 변화 ───────────────────────────────
st.markdown("---")
st.markdown('<div class="section-title">🔑 연도별 키워드 빈도 변화</div>', unsafe_allow_html=True)

@st.cache_data
def build_keyword_freq(df: pd.DataFrame) -> pd.DataFrame:
    """tokens_str 컬럼에서 연도별 키워드 빈도 집계 (공백 구분 단어)"""
    rows = []
    for _, r in df.iterrows():
        # tokens_str은 공백으로 구분된 단어열
        tokens = [t.strip() for t in str(r.get("tokens_str", "")).split() if len(t.strip()) >= 2]
        for tok in tokens:
            rows.append({"year": r["year"], "keyword": tok})
    if not rows:
        return pd.DataFrame(columns=["year", "keyword", "count"])
    kf = pd.DataFrame(rows)
    return kf.groupby(["year", "keyword"]).size().reset_index(name="count")

kw_freq = build_keyword_freq(df)

top_kw_n = st.slider("상위 키워드 수", 5, 30, 15, key="kw_slider")

# 표시할 키워드 결정
if kw_freq.empty:
    display_keywords = []
else:
    kw_sum = kw_freq.groupby("keyword")["count"].sum()
    kw_sum = pd.to_numeric(kw_sum, errors="coerce").dropna()
    display_keywords = kw_sum.nlargest(top_kw_n).index.tolist()

kw_plot = kw_freq[kw_freq["keyword"].isin(display_keywords)].copy()

kw_tab1, kw_tab2 = st.tabs(["📈 라인 (키워드별 추이)", "🔥 막대 (연도별 Top N)"])

with kw_tab1:
    if kw_plot.empty:
        st.info("표시할 키워드 데이터가 없습니다.")
    else:
        fig_kw_line = px.line(
            kw_plot.sort_values("year"),
            x="year", y="count", color="keyword",
            markers=True,
            labels={"year": "연도", "count": "등장 횟수", "keyword": "키워드"},
            color_discrete_sequence=px.colors.qualitative.Alphabet,
        )
        fig_kw_line.update_traces(line_width=2, marker_size=6)
        fig_kw_line.update_layout(
            height=400,
            plot_bgcolor="#0d1117", paper_bgcolor="#161b22", font_color="#c9d1d9",
            legend=dict(orientation="v", x=1.01, bgcolor="#1c2333",
                        bordercolor="#30363d", borderwidth=1, font_color="#c9d1d9"),
            margin=dict(t=20, b=20, l=10, r=10),
            xaxis=dict(gridcolor="#21262d", linecolor="#30363d", dtick=1),
            yaxis=dict(gridcolor="#21262d", linecolor="#30363d"),
        )
        st.plotly_chart(fig_kw_line, use_container_width=True)

with kw_tab2:
    # 연도 선택 → 해당 연도 Top N 막대
    avail_years = sorted(kw_freq["year"].unique())
    sel_yr_kw = st.select_slider(
        "연도 선택",
        options=avail_years,
        value=max(avail_years),
        key="kw_year_slider",
    )
    yr_top = (
        kw_freq[kw_freq["year"] == sel_yr_kw]
        .nlargest(top_kw_n, "count")
        .sort_values("count", ascending=True)
    )
    if yr_top.empty:
        st.info(f"{sel_yr_kw}년 키워드 데이터가 없습니다.")
    else:
        fig_kw_bar = go.Figure(go.Bar(
            x=yr_top["count"],
            y=yr_top["keyword"],
            orientation="h",
            marker=dict(
                color=yr_top["count"],
                colorscale=[[0, "#1c2333"], [0.4, "#1158c7"], [1.0, "#388bfd"]],
                showscale=False,
            ),
            text=yr_top["count"],
            textposition="outside",
            textfont_color="#c9d1d9",
        ))
        fig_kw_bar.update_layout(
            height=420,
            plot_bgcolor="#0d1117", paper_bgcolor="#161b22", font_color="#c9d1d9",
            margin=dict(t=20, b=20, l=10, r=40),
            xaxis=dict(gridcolor="#21262d", linecolor="#30363d"),
            yaxis=dict(gridcolor="#21262d", linecolor="#30363d", tickfont_color="#c9d1d9"),
            title=dict(text=f"{sel_yr_kw}년 Top {top_kw_n} 키워드", font_color="#8b949e", font_size=13),
        )
        st.plotly_chart(fig_kw_bar, use_container_width=True)

# ── 보도자료 목록 ─────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="section-title">📋 보도자료 목록</div>', unsafe_allow_html=True)

flt_col1, flt_col2, flt_col3 = st.columns([1, 1, 2])
with flt_col1:
    sel_year_tbl = st.selectbox("연도", ["전체"] + [str(y) for y in sorted(df["year"].unique(), reverse=True)])
with flt_col2:
    sel_cluster_tbl = st.selectbox(
        "유형", ["전체"] + [f"C{c}: {custom_labels[c]}" for c in sorted(df["cluster"].unique())]
    )
with flt_col3:
    keyword_search = st.text_input("제목 검색", placeholder="키워드를 입력하세요...")

tbl_df = df.copy()
if sel_year_tbl != "전체":
    tbl_df = tbl_df[tbl_df["year"] == int(sel_year_tbl)]
if sel_cluster_tbl != "전체":
    c_num = int(sel_cluster_tbl.split(":")[0].replace("C", ""))
    tbl_df = tbl_df[tbl_df["cluster"] == c_num]
if keyword_search:
    tbl_df = tbl_df[tbl_df["title"].str.contains(keyword_search, na=False)]

tbl_df = tbl_df.sort_values("date", ascending=False).reset_index(drop=True)
total_rows = len(tbl_df)

# ── 페이지네이션 ──────────────────────────────────────────
PAGE_SIZE = 10
total_pages = max(1, -(-total_rows // PAGE_SIZE))

filter_key = f"{sel_year_tbl}_{sel_cluster_tbl}_{keyword_search}"
if st.session_state.get("_tbl_filter_key") != filter_key:
    st.session_state["_tbl_filter_key"] = filter_key
    st.session_state["tbl_page"] = 1
if "tbl_page" not in st.session_state:
    st.session_state["tbl_page"] = 1

cur_page  = st.session_state["tbl_page"]
start_idx = (cur_page - 1) * PAGE_SIZE
end_idx   = min(start_idx + PAGE_SIZE, total_rows)
page_df   = tbl_df.iloc[start_idx:end_idx]

if total_rows == 0:
    st.info("조건에 맞는 보도자료가 없습니다.")
else:
    display_df = page_df[["date", "title", "cluster_label", "views", "detail_url"]].copy()
    display_df.columns = ["날짜", "제목", "유형", "조회수", "링크"]
    display_df["날짜"] = pd.to_datetime(display_df["날짜"]).dt.strftime("%Y-%m-%d")
    display_df["링크"] = display_df["링크"].apply(
        lambda u: f'<a href="{u}" target="_blank">🔗 원문</a>' if pd.notna(u) else "-"
    )
    st.markdown(display_df.to_html(escape=False, index=False, classes="table"), unsafe_allow_html=True)

    st.markdown(
        "<style>"
        ".pagination-wrap { display:flex; justify-content:center; align-items:center; gap:8px; margin-top:8px; }"
        ".stButton button { padding: 2px 14px !important; font-size:13px !important; }"
        "</style>",
        unsafe_allow_html=True,
    )
    _, pc1, pc2, pc3, _ = st.columns([2, 1, 1, 1, 2])
    with pc1:
        if st.button("◀ 이전", disabled=(cur_page <= 1), use_container_width=True):
            st.session_state["tbl_page"] -= 1
            st.rerun()
    with pc2:
        st.markdown(
            f"<div style='text-align:center;padding-top:6px;font-size:13px;color:#c9d1d9;'>"
            f"{cur_page} / {total_pages}</div>",
            unsafe_allow_html=True,
        )
    with pc3:
        if st.button("다음 ▶", disabled=(cur_page >= total_pages), use_container_width=True):
            st.session_state["tbl_page"] += 1
            st.rerun()

# ── 푸터 ──────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#484f58;font-size:12px;line-height:2;'>"
    "개인정보보호위원회 보도자료 분석 대시보드<br>"
    "데이터 출처: <a href='https://www.pipc.go.kr' target='_blank' "
    "style='color:#388bfd;text-decoration:none;'>개인정보보호위원회 (pipc.go.kr)</a> · "
    "분석 기준일: 2026-06"
    "</div>",
    unsafe_allow_html=True,
)