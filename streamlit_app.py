import time
import random
import streamlit as st
import graphviz

st.set_page_config(page_title="自宅ネットワーク トラブルシューティング教材", page_icon="🖧", layout="centered")

st.markdown(
    """
    <style>
    .terminal {
        background-color: #101418;
        color: #7CFC7C;
        font-family: "Consolas", "Courier New", monospace;
        font-size: 0.85rem;
        padding: 1rem;
        border-radius: 8px;
        white-space: pre-wrap;
        line-height: 1.5;
        min-height: 2rem;
        border: 1px solid #333;
    }
    .terminal .fail { color: #FF6B6B; }
    .led-box {
        display: inline-block; text-align:center; width: 90px;
        padding: 0.4rem; margin: 0.2rem; border-radius: 6px; background:#1b1f24;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 初期化
# ---------------------------------------------------------
DEFAULTS = {
    "stage": "initial",              # initial -> diagram -> trouble -> investigate -> analysis -> answered
    "ping_history": {},              # device_key -> list[str] (完了済みログ)
    "led_checked": False,
    "answer_submitted": False,
    "selected_answer": None,
    "reasoning_text": "",
    "action_log": [],                # 調査ログ（時系列）
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        if isinstance(v, dict):
            st.session_state[k] = dict(v)
        elif isinstance(v, list):
            st.session_state[k] = list(v)
        else:
            st.session_state[k] = v

# ---------------------------------------------------------
# データ定義
# ---------------------------------------------------------
DEVICES = {
    "a": {"name": "ルーター",              "ip": "192.168.1.1", "reachable": True},
    "b": {"name": "無線LANアクセスポイント", "ip": "192.168.1.2", "reachable": True},
    "c": {"name": "デスクトップPC",          "ip": "192.168.1.3", "reachable": False},
    "d": {"name": "プリンタ",               "ip": "192.168.1.4", "reachable": True},
}
LAPTOP_IP = "192.168.1.10"

HUB_PORTS = [
    {"label": "Port1: ルーター", "ok": True},
    {"label": "Port2: 無線AP", "ok": True},
    {"label": "Port3: デスクトップPC", "ok": False},
    {"label": "Port4: プリンタ", "ok": True},
]

CHOICES = {
    "①": "LANケーブルの接触不良・断線（ノートPC〜無線AP間、無線AP〜HUB間、またはHUB〜デスクトップPC間など）",
    "②": "HUBの障害（特定ポートの故障）",
    "③": "無線LANアクセスポイントの障害（無線AP本体の故障）",
    "④": "ルーターの障害（ルーター本体の故障、または特定ポートの不具合）",
}
CORRECT_ANSWER = "①"

EXPLANATION = """
**解説**

集めた証拠を整理すると次のようになります。

| 調査内容 | 結果 |
|---|---|
| a. ルーターへの ping | 成功（応答あり） |
| b. 無線LANアクセスポイントへの ping | 成功（応答あり） |
| c. デスクトップPCへの ping | 失敗（タイムアウト） |
| d. プリンタへの ping | 成功（応答あり） |
| HUBのポートランプ確認 | デスクトップPCのポートだけ消灯 |

- ルーター・無線AP・プリンタへの疎通はすべて成功 → **ルーター本体の故障（④）ではない**
- 無線APへの疎通も成功 → **無線AP本体の故障（③）ではない**
- プリンタ（HUB配下の有線機器）への疎通も成功し、HUBの他のポートランプも点灯している → **HUB自体が全面的に故障しているわけではない（②ではない）**
- デスクトップPCへの疎通だけが失敗し、該当ポートのランプだけが消灯している → **HUB〜デスクトップPC間のLANケーブルに物理的な問題がある可能性が高い**

以上から、今回の原因は **①LANケーブルの接触不良・断線（HUB〜デスクトップPC間）** と判断できます。
"""

INVESTIGATION_TASKS = [
    ("a", "ルーターに ping を送る"),
    ("b", "無線LANアクセスポイントに ping を送る"),
    ("d", "プリンタに ping を送る"),
    ("c", "デスクトップPCに ping を送る"),
]


def log(action: str):
    st.session_state.action_log.append(action)


# ---------------------------------------------------------
# 構成図の描画
# ---------------------------------------------------------
def draw_diagram(reveal_fault: bool = False):
    dot = graphviz.Digraph()
    dot.attr(rankdir="TB", bgcolor="transparent")
    dot.attr("node", shape="box", style="rounded,filled", fontname="Helvetica",
              fillcolor="#EAF2FF", color="#4C7CE0")

    def status_color(key):
        if key not in st.session_state.ping_history:
            return "#EAF2FF", "#4C7CE0"  # 未確認
        ok = DEVICES[key]["reachable"]
        return ("#DFF7DF", "#2ECC71") if ok else ("#FCE0E0", "#E74C3C")

    dot.node("ISP", "ISP")

    fc, cc = status_color("a")
    dot.node("Router", DEVICES["a"]["name"] + "\n" + DEVICES["a"]["ip"], fillcolor=fc, color=cc)

    dot.node("HUB", "HUB")

    fc, cc = status_color("b")
    dot.node("AP", DEVICES["b"]["name"] + "\n" + DEVICES["b"]["ip"], fillcolor=fc, color=cc)

    dot.node("Laptop", f"ノートPC(生徒側)\n{LAPTOP_IP}", fillcolor="#FFF3D6", color="#E0A94C")

    fc, cc = status_color("c")
    dot.node("Desktop", DEVICES["c"]["name"] + "\n" + DEVICES["c"]["ip"], fillcolor=fc, color=cc)

    fc, cc = status_color("d")
    dot.node("Printer", DEVICES["d"]["name"] + "\n" + DEVICES["d"]["ip"], fillcolor=fc, color=cc)

    dot.edge("ISP", "Router")
    dot.edge("Router", "HUB", label="有線")
    dot.edge("HUB", "AP", label="有線")
    dot.edge("AP", "Laptop", label="無線", style="dashed")

    if reveal_fault:
        dot.edge("HUB", "Desktop", label="有線（断線！）", color="red", style="dashed", penwidth="2", fontcolor="red")
    else:
        dot.edge("HUB", "Desktop", label="有線")

    dot.edge("HUB", "Printer", label="有線")
    return dot


# ---------------------------------------------------------
# ターミナル風 ping シミュレーション
# ---------------------------------------------------------
def animate_ping(key: str):
    device = DEVICES[key]
    ip = device["ip"]
    ok = device["reachable"]

    placeholder = st.empty()
    lines = [f"C:\\Users\\student&gt;ping {ip}", "", f"{ip} に ping を送信しています 32 バイトのデータ:"]

    def render():
        html = "\n".join(lines)
        placeholder.markdown(f'<div class="terminal">{html}</div>', unsafe_allow_html=True)

    render()
    time.sleep(0.3)

    for _ in range(4):
        if ok:
            latency = random.randint(1, 6)
            lines.append(f"{ip} からの応答: バイト数=32 時間={latency}ms TTL=64")
        else:
            lines.append('<span class="fail">要求がタイムアウトしました。</span>')
        render()
        time.sleep(0.35)

    lines.append("")
    lines.append(f"{ip} の ping 統計:")
    if ok:
        lines.append("    パケット数: 送信 = 4、受信 = 4、損失 = 0 (0% の損失)、")
    else:
        lines.append('    <span class="fail">パケット数: 送信 = 4、受信 = 0、損失 = 4 (100% の損失)、</span>')
    render()

    st.session_state.ping_history[key] = list(lines)
    log(f"ping {ip}（{device['name']}） → {'成功' if ok else '失敗（タイムアウト）'}")


def render_saved_ping(key: str):
    lines = st.session_state.ping_history[key]
    html = "\n".join(lines)
    st.markdown(f'<div class="terminal">{html}</div>', unsafe_allow_html=True)


# ===========================================================
# 画面本体
# ===========================================================
st.title("🖧 自宅ネットワーク トラブルシューティング教材")
st.caption("実際に ping コマンドや機器のランプを確認しながら、トラブルの原因を突き止めよう")
st.divider()

# ---- initial ----
if st.session_state.stage == "initial":
    st.write("ボタンを押すと、自宅のネットワーク構成が表示されます。")
    if st.button("▶ スタート", type="primary"):
        st.session_state.stage = "diagram"
        st.rerun()

# ---- 構成図（diagram以降は常に表示）----
if st.session_state.stage != "initial":
    reveal = st.session_state.answer_submitted
    st.graphviz_chart(draw_diagram(reveal_fault=reveal), use_container_width=True)

# ---- diagram ----
if st.session_state.stage == "diagram":
    st.info("これが自宅のネットワーク構成です。今は正常に通信できています。")
    if st.button("⚠ トラブル発生", type="primary"):
        st.session_state.stage = "trouble"
        log("トラブル発生：ノートPC → デスクトップPC の通信が途絶")
        st.rerun()

# ---- trouble ----
if st.session_state.stage in ("trouble", "investigate", "analysis", "answered"):
    st.error("**ノートPCからデスクトップPCへのネットワーク接続ができません。**")

if st.session_state.stage == "trouble":
    st.write("あなたはノートPCの前に座っています。まず現状を調査しましょう。")
    if st.button("🔎 調査を始める"):
        st.session_state.stage = "investigate"
        st.rerun()

# ---- investigate ----
if st.session_state.stage in ("investigate", "analysis", "answered"):
        st.subheader("① コマンドプロンプトで ping を実行する")
        st.write("ノートPCから、疑わしい機器に向けて ping を送ってみましょう。")

        with st.expander("🔎 調査チェックリスト", expanded=True):
            for key, task_text in INVESTIGATION_TASKS:
                done = key in st.session_state.ping_history
                checkbox = "☑" if done else "☐"
                st.markdown(f"- {checkbox} {task_text}")
            led_checkbox = "☑" if st.session_state.led_checked else "☐"
            st.markdown(f"- {led_checkbox} HUBのポートランプを確認する")

        cols = st.columns(2)
        for idx, (key, device) in enumerate(DEVICES.items()):
            with cols[idx % 2]:
                button_label = f"▶ {device['name']} ({device['ip']}) に ping"
                if st.button(button_label, key=f"ping_button_{key}", disabled=(st.session_state.stage != "investigate")):
                    animate_ping(key)

        if st.session_state.ping_history:
            latest_key = list(st.session_state.ping_history.keys())[-1]
            render_saved_ping(latest_key)
        else:
            st.caption("まずは上のボタンから調査したい機器に ping を送ってみましょう。")

        with st.expander("これまでに ping した機器の結果一覧"):
            if not st.session_state.ping_history:
                st.caption("まだ ping を実行していません。")
            else:
                rows = []
                for key, device in DEVICES.items():
                    if key in st.session_state.ping_history:
                        result = "〇（応答あり）" if device["reachable"] else "×（タイムアウト）"
                    else:
                        result = "未確認"
                    rows.append({"機器": f"{key}. {device['name']}", "IPアドレス": device["ip"], "結果": result})
                st.table(rows)

        st.write("")
        st.subheader("② HUBのポートランプを目視で確認する")
        st.write("ping だけでなく、実機のランプ（LED）も手がかりになります。HUBの前面を確認してみましょう。")

        if st.session_state.stage == "investigate":
            if not st.session_state.led_checked:
                if st.button("🔌 HUBのランプを確認する"):
                    st.session_state.led_checked = True
                    log("HUBのポートランプを確認 → デスクトップPCのポートのみ消灯")
            else:
                st.success("HUBのランプ確認が完了しました。")

        if st.session_state.led_checked:
            led_cols = st.columns(4)
            for port, col in zip(HUB_PORTS, led_cols):
                with col:
                    icon = "🟢" if port["ok"] else "⚫"
                    status = "点灯（リンクOK）" if port["ok"] else "消灯（リンクなし）"
                    st.markdown(
                        f'<div class="led-box"><div style="font-size:1.6rem">{icon}</div>'
                        f'<div style="font-size:0.75rem">{port["label"]}</div>'
                        f'<div style="font-size:0.7rem;color:#aaa">{status}</div></div>',
                        unsafe_allow_html=True,
                    )

        if st.session_state.action_log:
            with st.expander("📝 調査ログ", expanded=False):
                for i, entry in enumerate(st.session_state.action_log, 1):
                    st.write(f"{i}. {entry}")

        all_pinged = len(st.session_state.ping_history) == len(DEVICES)
        if st.session_state.stage == "investigate":
            if not all_pinged or not st.session_state.led_checked:
                remaining_devices = [DEVICES[key]['name'] for key in DEVICES if key not in st.session_state.ping_history]
                if remaining_devices:
                    st.caption(f"まだ ping していない機器: {', '.join(remaining_devices)}")
                if not st.session_state.led_checked:
                    st.caption("HUBのランプ確認も忘れずに行いましょう。")
            else:
                st.success("すべての調査が揃いました。原因を考えてみましょう。")
                if st.button("➡ 原因の推定へ進む", type="primary"):
                    st.session_state.stage = "analysis"
                    st.rerun()

# ---- analysis ----
if st.session_state.stage == "analysis":
    st.divider()
    st.subheader("③ 原因を推定しよう")

    st.session_state.reasoning_text = st.text_area(
        "集めた証拠（ping結果・ランプの状態）から、なぜそう考えたのか理由を書いてみましょう（任意）",
        value=st.session_state.reasoning_text,
        placeholder="例：ルーター・無線AP・プリンタへの ping は成功しているが、デスクトップPCだけ失敗しており…",
        height=100,
    )

    choice = st.radio(
        "考えられる原因を①〜④から選んでください",
        options=list(CHOICES.keys()),
        format_func=lambda k: f"{k} {CHOICES[k]}",
        index=None,
    )

    if st.button("✅ 解答する", type="primary", disabled=(choice is None)):
        st.session_state.selected_answer = choice
        st.session_state.answer_submitted = True
        st.session_state.stage = "answered"
        st.rerun()

# ---- answered ----
if st.session_state.stage == "answered":
    st.divider()
    if st.session_state.selected_answer == CORRECT_ANSWER:
        st.success(f"正解です！ あなたの解答：{st.session_state.selected_answer} {CHOICES[st.session_state.selected_answer]}")
    else:
        st.warning(
            f"残念、不正解です。あなたの解答：{st.session_state.selected_answer} {CHOICES[st.session_state.selected_answer]}\n\n"
            f"正解は **{CORRECT_ANSWER} {CHOICES[CORRECT_ANSWER]}** でした。"
        )

    if st.session_state.reasoning_text.strip():
        st.markdown("**あなたが書いた推論**")
        st.info(st.session_state.reasoning_text)

    st.markdown(EXPLANATION)

    with st.expander("📝 調査ログ（振り返り）"):
        for i, entry in enumerate(st.session_state.action_log, 1):
            st.write(f"{i}. {entry}")

    if st.button("🔄 最初からやり直す"):
        for k, v in DEFAULTS.items():
            if isinstance(v, dict):
                st.session_state[k] = dict(v)
            elif isinstance(v, list):
                st.session_state[k] = list(v)
            else:
                st.session_state[k] = v
        st.rerun()