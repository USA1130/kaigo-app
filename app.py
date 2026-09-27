import streamlit as st
import math
import urllib.parse

# --- ページ基本設定 ---
st.set_page_config(
    page_title="介護タクシー概算料金シミュレーター",
    page_icon="🚕",
    layout="centered"
)

st.title("🚕 介護タクシー 概算料金計算")
st.caption("「距離制」と「時間制（貸切）」の料金自動比較 ＆ 渋滞考慮シミュレーター")

st.markdown("---")

# --- STEP 1: 発着地の入力（デフォルト住所を設定） ---
st.subheader("1. 発着地の入力")

col_orig, col_dest = st.columns(2)
with col_orig:
    origin = st.text_input("出発地", value="千葉県鎌ケ谷市東鎌ケ谷2丁目8-1")
with col_dest:
    destination = st.text_input("目的地", value="鎌ケ谷総合病院")

# Googleマップを開くボタン
if origin and destination:
    encoded_origin = urllib.parse.quote(origin)
    encoded_dest = urllib.parse.quote(destination)
    gmaps_url = f"https://www.google.com/maps/dir/?api=1&origin={encoded_origin}&destination={encoded_dest}"
    
    st.info("👇 下のボタンを押すと別タブでGoogleマップが開き、距離と走行時間を調べられます。")
    st.link_button("🗺️ Googleマップで距離・所要時間を確認する", gmaps_url)

st.markdown("---")

# --- STEP 2: 走行距離と利用時間の入力 ---
st.subheader("2. 距離と所要時間・待機の入力")

col_dist, col_drive_time = st.columns(2)
with col_dist:
    distance_km = st.number_input(
        "走行距離 (km)",
        min_value=0.1,
        max_value=200.0,
        value=3.0,
        step=0.1,
        format="%.1f"
    )

with col_drive_time:
    normal_drive_minutes = st.number_input(
        "マップの標準走行時間 (分)",
        min_value=1,
        max_value=300,
        value=10,
        step=1,
        help="Googleマップで表示される通常の車走行時間"
    )

col_wait, col_total_charter = st.columns(2)
with col_wait:
    stop_minutes = st.number_input(
        "乗降介助・待機時間 (分)",
        min_value=0,
        max_value=180,
        value=5,
        step=1,
        help="現地での乗り降り、介助、現場待機などの時間（90秒毎に100円加算）"
    )

with col_total_charter:
    total_duration_minutes = st.number_input(
        "時間制比較用の総利用時間 (分)",
        min_value=15,
        max_value=720,
        value=max(30, int(normal_drive_minutes + stop_minutes)),
        step=15,
        help="時間制運賃（30分毎3,650円）計算のベース時間"
    )

# 信号待ち設定 ＆ 渋滞考慮エリア
st.markdown("##### 🚦 信号待ち・渋滞シミュレーション設定")
col_signal_density, col_signal_wait, col_traffic = st.columns(3)

with col_signal_density:
    signals_per_km = st.number_input(
        "1kmあたりの信号機数 (機)",
        min_value=0.0,
        max_value=10.0,
        value=2.0,
        step=0.5,
        format="%.1f",
        help="市街地の平均信号機密度（標準2機/km）"
    )

with col_signal_wait:
    wait_sec_per_signal = st.number_input(
        "1機あたりの平均赤信号待ち (秒)",
        min_value=0,
        max_value=120,
        value=25,
        step=5,
        help="赤信号に引っかかった場合の平均停止時間（標準25秒）"
    )

with col_traffic:
    traffic_drive_minutes = st.number_input(
        "渋滞時の想定走行時間 (分)",
        min_value=int(normal_drive_minutes),
        max_value=600,
        value=max(int(normal_drive_minutes * 1.5), normal_drive_minutes + 5),
        step=1,
        help="渋滞が発生した場合の予測走行時間"
    )

st.markdown("---")

# --- STEP 3: 迎車料・予約料・基本介助料・割引 ---
st.subheader("3. 基本料金・割引")

col_b1, col_b2 = st.columns(2)
with col_b1:
    use_geisha = st.checkbox("迎車料 (+850円)", value=True, help="※時間制運賃の場合は迎車料込みとなります")
    use_yoyaku = st.checkbox("予約料 (+400円)", value=True)
with col_b2:
    need_care = st.checkbox("基本介助料 (+1,100円)", value=True)
    disability_discount = st.checkbox("身体障害者割引 (-10%)", help="メーター/時間制運賃から1割引")

st.markdown("---")

# --- STEP 4: 機材・介助オプション・付添 ---
st.subheader("4. 機材・介助オプション")

# 機材変更時に「室内介助」のチェックを連動させるコールバック関数
def on_equipment_change():
    selected = st.session_state.equipment_choice
    if "リクライニング" in selected or "ストレッチャー" in selected:
        st.session_state.indoor_care_checked = True
    else:
        st.session_state.indoor_care_checked = False

# 初期状態のセッションステート設定
if "indoor_care_checked" not in st.session_state:
    st.session_state.indoor_care_checked = False

equipment = st.radio(
    "利用機材",
    ["なし / 普通車椅子 (0円)", "リクライニング車椅子 (+2,000円)", "ストレッチャー (+4,000円)"],
    key="equipment_choice",
    on_change=on_equipment_change,
    horizontal=True
)

col_op1, col_op2, col_op3 = st.columns(3)

with col_op1:
    need_indoor_care = st.checkbox(
        "室内介助料 (+1,100円)",
        key="indoor_care_checked"
    )

with col_op2:
    stairs_floors = st.number_input(
        "階段介助 (1フロア1,100円)",
        min_value=0,
        max_value=10,
        value=0,
        step=1
    )

with col_op3:
    hospital_accompany_minutes = st.number_input(
        "病院付添 (時間指定)",
        min_value=0,
        max_value=600,
        value=0,
        step=30,
        help="最初の1時間4,000円、以降30分ごとに2,000円"
    )

st.markdown("---")

# --- STEP 5: 運賃計算ロジック ---

# 【距離制】1. 距離運賃（初乗り2.0kmまで850円、以後239m毎に100円）
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

# 【距離制】2. 時間加算運賃（10km/h以下の走行・停車時間：90秒毎に100円）
def calculate_time_fare(minutes):
    if minutes <= 0:
        return 0
    seconds = minutes * 60
    steps = math.ceil(seconds / 90)
    return steps * 100

# 【時間制】3. 時間制運賃（30分毎に3,650円・迎車料込）
def calculate_charter_fare(total_minutes):
    steps = math.ceil(total_minutes / 30)
    return steps * 3650

# 病院付添料（最初の1時間 4,000円、以降30分ごとに 2,000円）
def calculate_hospital_accompany(minutes):
    if minutes <= 0:
        return 0
    if minutes <= 60:
        return 4000
    
    extra_minutes = minutes - 60
    extra_steps = math.ceil(extra_minutes / 30)
    return 4000 + (extra_steps * 2000)

# 共通オプション計算
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

common_options = yoyaku_fare + care_fare + indoor_care_fare + equipment_fare + stairs_fare + hospital_fare
geisha_fare = 850 if use_geisha else 0

# --------------------------------------------------
# 時間加算対象分数の算出（信号8機＋渋滞8割）
# --------------------------------------------------
# 1. 通常走行時の信号待ち時間（分）： 距離 × 信号機数/km × 平均秒数 / 60
total_signals = distance_km * signals_per_km
normal_signal_minutes = (total_signals * wait_sec_per_signal) / 60.0

# 2. 通常時の時間加算対象 ＝ 信号待ち時間 ＋ 乗降介助・待機時間
normal_add_target_minutes = normal_signal_minutes + stop_minutes

# 3. 渋滞によるロス時間（分）の 80% を 10km/h 以下とみなす
traffic_delay_minutes = max(0.0, traffic_drive_minutes - normal_drive_minutes)
traffic_low_speed_minutes = traffic_delay_minutes * 0.8

# 4. 渋滞時の時間加算対象 ＝ 通常時の加算対象 ＋ 渋滞ロスの80%
traffic_add_target_minutes = normal_add_target_minutes + traffic_low_speed_minutes

# --------------------------------------------------
# A-1. 通常時の距離制運賃計算
# --------------------------------------------------
dist_fare_raw = calculate_distance_fare(distance_km)
normal_time_add_fare = calculate_time_fare(normal_add_target_minutes)

normal_meter_total = dist_fare_raw + normal_time_add_fare
if disability_discount:
    normal_meter_after_disc = math.floor(normal_meter_total * 0.9)
else:
    normal_meter_after_disc = normal_meter_total

dist_total_normal = normal_meter_after_disc + geisha_fare + common_options

# --------------------------------------------------
# A-2. 渋滞考慮時の距離制運賃計算
# --------------------------------------------------
traffic_time_add_fare = calculate_time_fare(traffic_add_target_minutes)

traffic_meter_total = dist_fare_raw + traffic_time_add_fare
if disability_discount:
    traffic_meter_after_disc = math.floor(traffic_meter_total * 0.9)
else:
    traffic_meter_after_disc = traffic_meter_total

dist_total_traffic = traffic_meter_after_disc + geisha_fare + common_options

# --------------------------------------------------
# B. 時間制運賃の計算（迎車料込み）
# --------------------------------------------------
charter_raw = calculate_charter_fare(total_duration_minutes)

if disability_discount:
    charter_after_disc = math.floor(charter_raw * 0.9)
else:
    charter_after_disc = charter_raw

charter_total_final = charter_after_disc + common_options

# --- STEP 6: 結果表示と比較 ---
st.subheader("5. 見積もり比較結果")

# 縦並び配置で全画面サイズに対応
st.markdown("#### 📏 距離制運賃")
st.metric("概算合計", f"{dist_total_normal:,} 円 〜 {dist_total_traffic:,} 円 (渋滞時)")
if dist_total_normal <= charter_total_final:
    st.success("💡 通常時は距離制がお得です")

st.markdown("---")

st.markdown("#### ⏱️ 時間制運賃 ")
st.metric("概算合計", f"{charter_total_final:,} 円")
if charter_total_final < dist_total_normal:
    st.success("💡 時間制がお得です")

# 内訳詳細
with st.expander("詳細内訳を確認する"):
    st.write(f"**共通オプション費用:** {common_options:,} 円 (予約料: {yoyaku_fare}円, 基本介助: {care_fare}円, 室内介助: {indoor_care_fare}円, 機材: {equipment_fare}円, 階段: {stairs_fare}円, 付添: {hospital_fare}円)")
    st.markdown("---")
    
    col_d_detail, col_t_detail = st.columns(2)
    with col_d_detail:
        st.write("**距離制（通常時）の内訳:**")
        st.write(f"- 距離運賃 ({distance_km:.1f}km): {dist_fare_raw:,} 円")
        st.write(f"- 時間加算運賃 ({normal_add_target_minutes:.1f}分相当 [信号待ち{normal_signal_minutes:.1f}分+待機{stop_minutes}分]): {normal_time_add_fare:,} 円")
        if disability_discount:
            st.write(f"- 障害者割引 (-10%): -{(normal_meter_total - normal_meter_after_disc):,} 円")
        st.write(f"- 迎車料: {geisha_fare:,} 円")
        st.write(f"- 共通オプション: {common_options:,} 円")
        
    with col_t_detail:
        st.write("**距離制（渋滞時）の内訳:**")
        st.write(f"- 距離運賃 ({distance_km:.1f}km): {dist_fare_raw:,} 円")
        st.write(f"- 時間加算運賃 ({traffic_add_target_minutes:.1f}分相当 [信号待ち{normal_signal_minutes:.1f}分+待機{stop_minutes}分+渋滞遅延80%{traffic_low_speed_minutes:.1f}分]): {traffic_time_add_fare:,} 円")
        if disability_discount:
            st.write(f"- 障害者割引 (-10%): -{(traffic_meter_total - traffic_meter_after_disc):,} 円")
        st.write(f"- 迎車料: {geisha_fare:,} 円")
        st.write(f"- 共通オプション: {common_options:,} 円")

st.caption("※表示金額は概算です。実際の道路状況（信号待ち・渋滞等）や現地での待機・介助内容により変動する場合があります。")