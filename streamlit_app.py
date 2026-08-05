import streamlit as st
import random

st.set_page_config(page_title="じゃんけんゲーム", page_icon="✊", layout="centered")

# 手の定義（絵文字・勝敗ルール）
HANDS = {
    "グー": "✊",
    "チョキ": "✌️",
    "パー": "✋",
}

# 各手が勝つ相手の手
WIN_MAP = {
    "グー": "チョキ",
    "チョキ": "パー",
    "パー": "グー",
}

# セッション状態の初期化
if "win" not in st.session_state:
    st.session_state.win = 0
if "lose" not in st.session_state:
    st.session_state.lose = 0
if "draw" not in st.session_state:
    st.session_state.draw = 0
if "history" not in st.session_state:
    st.session_state.history = []


def judge(player, cpu):
    """プレイヤーとCPUの手から勝敗を判定する"""
    if player == cpu:
        return "あいこ"
    elif WIN_MAP[player] == cpu:
        return "勝ち"
    else:
        return "負け"


def play(player_hand):
    cpu_hand = random.choice(list(HANDS.keys()))
    result = judge(player_hand, cpu_hand)

    if result == "勝ち":
        st.session_state.win += 1
    elif result == "負け":
        st.session_state.lose += 1
    else:
        st.session_state.draw += 1

    st.session_state.history.insert(0, (player_hand, cpu_hand, result))
    st.session_state.last_result = (player_hand, cpu_hand, result)


def reset_score():
    st.session_state.win = 0
    st.session_state.lose = 0
    st.session_state.draw = 0
    st.session_state.history = []
    st.session_state.pop("last_result", None)


# ---------- 画面表示 ----------
st.title("✊✌️✋ じゃんけんゲーム")
st.write("好きな手を選んでボタンを押してください。")

# 手を選ぶボタン
cols = st.columns(3)
for col, (name, emoji) in zip(cols, HANDS.items()):
    with col:
        if st.button(f"{emoji} {name}", use_container_width=True):
            play(name)

st.divider()

# 直前の結果表示
if "last_result" in st.session_state:
    p, c, r = st.session_state.last_result
    st.subheader("結果")
    r1, r2 = st.columns(2)
    with r1:
        st.metric("あなた", f"{HANDS[p]} {p}")
    with r2:
        st.metric("CPU", f"{HANDS[c]} {c}")

    if r == "勝ち":
        st.success("🎉 あなたの勝ちです！")
        st.balloons()
    elif r == "負け":
        st.error("😢 あなたの負けです…")
    else:
        st.info("🤝 あいこです")
else:
    st.write("まだ対戦していません。")

st.divider()

# スコア表示
st.subheader("戦績")
s1, s2, s3 = st.columns(3)
s1.metric("勝ち", st.session_state.win)
s2.metric("負け", st.session_state.lose)
s3.metric("あいこ", st.session_state.draw)

total = st.session_state.win + st.session_state.lose + st.session_state.draw
if total > 0:
    win_rate = st.session_state.win / total * 100
    st.write(f"勝率: {win_rate:.1f}%（全{total}回）")

if st.button("スコアをリセット"):
    reset_score()
    st.rerun()

# 対戦履歴
if st.session_state.history:
    st.divider()
    st.subheader("対戦履歴（直近10件）")
    for i, (p, c, r) in enumerate(st.session_state.history[:10], start=1):
        st.write(f"{i}. あなた: {HANDS[p]}{p} vs CPU: {HANDS[c]}{c} → **{r}**")