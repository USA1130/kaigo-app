import math
from urllib.parse import quote

import streamlit as st


# =========================================================
# ページ設定
# =========================================================
st.set_page_config(
    page_title="介護タクシー概算料金シミュレーター",
    page_icon="🚕",
    layout="centered",
)

st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        word-break: break-word;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🚕 介護タクシー 概算料金計算")
st.caption("距離制・時間制（貸切）の料金比較と、渋滞を考慮した概算シミュレーター")
st.markdown("---")


# =========================================================
# Googleマップで確認した距離・時間を手入力
# =========================================================
# =========================================================
# セッション状態の初期化
# =========================================================
DEFAULTS = {
    "origin_address": "千葉県鎌ケ谷市東鎌ケ谷2丁目8-1",
    "destination_address": "千葉県鎌ケ谷市初富929-6",
    "distance_km": 3.0,
    "normal_drive_minutes": 10,
    "traffic_drive_minutes": 15,
    "stop_minutes": 5,
    "total_duration_minutes": 30,
    "signals_per_km": 2.0,
    "wait_sec_per_signal": 25,
    "use_geisha": True,
    "use_yoyaku": True,
    "need_care": True,
    "disability_discount": False,
    "equipment_choice": "なし / 普通車椅子 (0円)",
    "indoor_care_checked": False,
    "stairs_floors": 0,
    "hospital_accompany_minutes": 0,
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def keep_traffic_time_valid():
    """標準走行時間を変更した際、渋滞時間が標準時間を下回らないようにする。"""
    standard = int(st.session_state.get("normal_drive_minutes", 1))
    current = int(st.session_state.get("traffic_drive_minutes", standard))
    st.session_state["traffic_drive_minutes"] = min(600, max(standard, math.ceil(standard * 1.5)))


def on_equipment_change():
    """リクライニング・ストレッチャー選択時は室内介助を自動選択する。"""
    selected = st.session_state.get("equipment_choice", "")
    if "リクライニング" in selected or "ストレッチャー" in selected:
        st.session_state["indoor_care_checked"] = True
    else:
        st.session_state["indoor_care_checked"] = False


# =========================================================
# STEP 1: 発着地・Googleマップ経路確認
# =========================================================
st.subheader("1. 発着地の入力")

col_orig, col_dest = st.columns(2)
with col_orig:
    st.text_input("出発地", key="origin_address")
with col_dest:
    st.text_input("目的地", key="destination_address")

origin_q = quote(st.session_state["origin_address"])
destination_q = quote(st.session_state["destination_address"])
google_maps_url = (
    "https://www.google.com/maps/dir/?api=1"
    f"&origin={origin_q}&destination={destination_q}&travelmode=driving"
)
st.markdown(f"[Googleマップで経路を確認する]({google_maps_url})")
st.caption("Googleマップで車の経路を確認し、道路距離と標準所要時間を下の欄に入力してください。")
st.markdown("---")
# =========================================================
# STEP 2: 距離・時間・待機・渋滞
# =========================================================
st.subheader("2. 距離と所要時間・待機の入力")

col_dist, col_drive_time = st.columns(2)
with col_dist:
    distance_km = st.number_input(
        "走行距離 (km)",
        min_value=0.1,
        max_value=200.0,
        step=0.1,
        format="%.1f",
        key="distance_km",
    )
with col_drive_time:
    normal_drive_minutes = st.number_input(
        "標準走行時間 (分)",
        min_value=1,
        max_value=300,
        step=1,
        key="normal_drive_minutes",
        on_change=keep_traffic_time_valid,
        help="Googleマップで確認した通常時の所要時間を入力してください。",
    )

col_wait, col_total = st.columns(2)
with col_wait:
    stop_minutes = st.number_input(
        "乗降介助・待機時間 (分)",
        min_value=0,
        max_value=180,
        step=1,
        key="stop_minutes",
        help="現地での乗り降り、介助、現場待機などの時間です。",
    )
with col_total:
    total_duration_minutes = st.number_input(
        "時間制比較用の総利用時間 (分)",
        min_value=15,
        max_value=720,
        step=15,
        key="total_duration_minutes",
        help="時間制運賃（30分ごと3,650円）の計算に使う総利用時間です。",
    )

st.markdown("##### 渋滞シミュレーション")
traffic_drive_minutes = st.number_input(
    "渋滞時の想定走行時間 (分)",
    min_value=int(normal_drive_minutes),
    max_value=600,
    step=1,
    key="traffic_drive_minutes",
    help="標準時間の1.5倍を初期値とし、必要に応じて手動調整できます。",
)

st.markdown("##### 🚦 信号待ちの想定")
col_signal_density, col_signal_wait = st.columns(2)
with col_signal_density:
    signals_per_km = st.number_input(
        "1kmあたりの信号機数 (機)",
        min_value=0.0,
        max_value=10.0,
        step=0.5,
        format="%.1f",
        key="signals_per_km",
        help="市街地の平均信号機密度の想定値です（初期値2機/km）。",
    )
with col_signal_wait:
    wait_sec_per_signal = st.number_input(
        "1機あたりの平均赤信号待ち (秒)",
        min_value=0,
        max_value=120,
        step=5,
        key="wait_sec_per_signal",
        help="赤信号に遭遇した場合の平均停止時間です（初期値25秒）。",
    )

st.markdown("---")


# =========================================================
# STEP 3: 基本料金・割引
# =========================================================
st.subheader("3. 基本料金・割引")

col_b1, col_b2 = st.columns(2)
with col_b1:
    use_geisha = st.checkbox(
        "迎車料 (+850円)",
        key="use_geisha",
        help="時間制運賃の場合は迎車料込みとして別途加算しません。",
    )
    use_yoyaku = st.checkbox("予約料 (+400円)", key="use_yoyaku")
with col_b2:
    need_care = st.checkbox("基本介助料 (+1,100円)", key="need_care")
    disability_discount = st.checkbox(
        "身体障害者割引 (-10%)",
        key="disability_discount",
        help="メーター運賃・時間制運賃から1割引します。",
    )

st.markdown("---")


# =========================================================
# STEP 4: 機材・介助オプション
# =========================================================
st.subheader("4. 機材・介助オプション")

equipment = st.radio(
    "利用機材",
    [
        "なし / 普通車椅子 (0円)",
        "リクライニング車椅子 (+2,000円)",
        "ストレッチャー (+4,000円)",
    ],
    key="equipment_choice",
    on_change=on_equipment_change,
    horizontal=True,
)

col_op1, col_op2, col_op3 = st.columns(3)
with col_op1:
    need_indoor_care = st.checkbox(
        "室内介助料 (+1,100円)",
        key="indoor_care_checked",
    )
with col_op2:
    stairs_floors = st.number_input(
        "階段介助 (1フロア1,100円)",
        min_value=0,
        max_value=10,
        step=1,
        key="stairs_floors",
    )
with col_op3:
    hospital_accompany_minutes = st.number_input(
        "病院付添 (分)",
        min_value=0,
        max_value=600,
        step=30,
        key="hospital_accompany_minutes",
        help="最初の60分4,000円、以降30分ごとに2,000円です。",
    )

st.markdown("---")


# =========================================================
# STEP 5: 運賃計算ロジック
# ※単価・計算方式は元ファイルの設定を維持
# =========================================================

# 距離制：初乗り2.0kmまで850円、以後239mごと100円
def calculate_distance_fare(dist):
    initial_dist = 2.0
    initial_fare = 850
    unit_dist = 0.239
    unit_fare = 100

    if dist <= initial_dist:
        return initial_fare

    remaining_dist = dist - initial_dist
    steps = math.ceil(remaining_dist / unit_dist)
    return initial_fare + (steps * unit_fare)


# 時間加算：90秒ごと100円
def calculate_time_fare(minutes):
    if minutes <= 0:
        return 0
    seconds = minutes * 60
    steps = math.ceil(seconds / 90)
    return steps * 100


# 時間制：30分ごと3,650円（迎車料込み）
def calculate_charter_fare(total_minutes):
    steps = math.ceil(total_minutes / 30)
    return steps * 3650


# 病院付添：最初の60分4,000円、以降30分ごと2,000円
def calculate_hospital_accompany(minutes):
    if minutes <= 0:
        return 0
    if minutes <= 60:
        return 4000

    extra_minutes = minutes - 60
    extra_steps = math.ceil(extra_minutes / 30)
    return 4000 + (extra_steps * 2000)


# 共通オプション
yoyaku_fare = 400 if use_yoyaku else 0
care_fare = 1100 if need_care else 0
indoor_care_fare = 1100 if need_indoor_care else 0

equipment_fare = 0
if "リクライニング" in equipment:
    equipment_fare = 2000
elif "ストレッチャー" in equipment:
    equipment_fare = 4000

stairs_fare = stairs_floors * 1100
hospital_fare = calculate_hospital_accompany(hospital_accompany_minutes)

common_options = (
    yoyaku_fare
    + care_fare
    + indoor_care_fare
    + equipment_fare
    + stairs_fare
    + hospital_fare
)
geisha_fare = 850 if use_geisha else 0

# 通常走行時の信号待ち時間（遭遇率50%）
total_signals = distance_km * signals_per_km
normal_signal_minutes = (
    total_signals * wait_sec_per_signal * 0.5
) / 60.0

# 通常時の時間加算対象 = 信号待ち + 乗降介助・待機
normal_add_target_minutes = normal_signal_minutes + stop_minutes

# 渋滞による遅延の80%を10km/h以下の時間とみなす
traffic_delay_minutes = max(
    0.0,
    traffic_drive_minutes - normal_drive_minutes,
)
traffic_low_speed_minutes = traffic_delay_minutes * 0.8

# 渋滞時の時間加算対象
traffic_add_target_minutes = (
    normal_add_target_minutes + traffic_low_speed_minutes
)

# A-1. 通常時の距離制運賃
dist_fare_raw = calculate_distance_fare(distance_km)
normal_time_add_fare = calculate_time_fare(normal_add_target_minutes)

normal_meter_total = dist_fare_raw + normal_time_add_fare
if disability_discount:
    normal_meter_after_disc = math.floor(normal_meter_total * 0.9)
else:
    normal_meter_after_disc = normal_meter_total

dist_total_normal = (
    normal_meter_after_disc + geisha_fare + common_options
)

# A-2. 渋滞考慮時の距離制運賃
traffic_time_add_fare = calculate_time_fare(traffic_add_target_minutes)

traffic_meter_total = dist_fare_raw + traffic_time_add_fare
if disability_discount:
    traffic_meter_after_disc = math.floor(traffic_meter_total * 0.9)
else:
    traffic_meter_after_disc = traffic_meter_total

dist_total_traffic = (
    traffic_meter_after_disc + geisha_fare + common_options
)

# B. 時間制運賃（迎車料込み）
charter_raw = calculate_charter_fare(total_duration_minutes)
if disability_discount:
    charter_after_disc = math.floor(charter_raw * 0.9)
else:
    charter_after_disc = charter_raw

charter_total_final = charter_after_disc + common_options


# =========================================================
# STEP 6: 結果表示
# =========================================================
st.subheader("5. 見積もり比較結果")

st.markdown("#### 📏 距離制運賃")
st.metric(
    "概算合計",
    f"{dist_total_normal:,} 円 〜 {dist_total_traffic:,} 円（渋滞時）",
)
if dist_total_normal <= charter_total_final:
    st.success("通常時は距離制の方がお得な試算です。")

st.markdown("---")

st.markdown("#### ⏱️ 時間制運賃（貸切）")
st.metric("概算合計", f"{charter_total_final:,} 円")
if charter_total_final < dist_total_normal:
    st.success("通常時は時間制の方がお得な試算です。")

with st.expander("詳細内訳を確認する"):
    st.write(
        f"**共通オプション費用:** {common_options:,} 円 "
        f"(予約料: {yoyaku_fare:,}円、基本介助: {care_fare:,}円、"
        f"室内介助: {indoor_care_fare:,}円、機材: {equipment_fare:,}円、"
        f"階段: {stairs_fare:,}円、付添: {hospital_fare:,}円)"
    )
    st.markdown("---")

    col_d_detail, col_t_detail = st.columns(2)
    with col_d_detail:
        st.write("**距離制（通常時）の内訳**")
        st.write(f"- 距離運賃（{distance_km:.1f}km）: {dist_fare_raw:,} 円")
        st.write(
            f"- 時間加算（{normal_add_target_minutes:.1f}分相当）: "
            f"{normal_time_add_fare:,} 円"
        )
        st.caption(
            f"信号待ち {normal_signal_minutes:.1f}分 + "
            f"乗降介助・待機 {stop_minutes}分"
        )
        if disability_discount:
            st.write(
                f"- 障害者割引: -{normal_meter_total - normal_meter_after_disc:,} 円"
            )
        st.write(f"- 迎車料: {geisha_fare:,} 円")
        st.write(f"- 共通オプション: {common_options:,} 円")

    with col_t_detail:
        st.write("**距離制（渋滞時）の内訳**")
        st.write(f"- 距離運賃（{distance_km:.1f}km）: {dist_fare_raw:,} 円")
        st.write(
            f"- 時間加算（{traffic_add_target_minutes:.1f}分相当）: "
            f"{traffic_time_add_fare:,} 円"
        )
        st.caption(
            f"信号待ち {normal_signal_minutes:.1f}分 + "
            f"乗降介助・待機 {stop_minutes}分 + "
            f"渋滞遅延80% {traffic_low_speed_minutes:.1f}分"
        )
        if disability_discount:
            st.write(
                f"- 障害者割引: -{traffic_meter_total - traffic_meter_after_disc:,} 円"
            )
        st.write(f"- 迎車料: {geisha_fare:,} 円")
        st.write(f"- 共通オプション: {common_options:,} 円")

    st.markdown("---")
    st.write("**時間制（貸切）の内訳**")
    st.write(
        f"- 時間制運賃（{total_duration_minutes}分）: {charter_raw:,} 円"
    )
    if disability_discount:
        st.write(
            f"- 障害者割引: -{charter_raw - charter_after_disc:,} 円"
        )
    st.write(f"- 共通オプション: {common_options:,} 円")

st.caption(
    "※表示金額は概算です。実際の道路状況、信号待ち、渋滞、"
    "現地での待機・介助内容により変動する場合があります。"
    "距離と標準時間はGoogleマップを参照して入力してください。"
)

