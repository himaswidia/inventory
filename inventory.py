import random
import streamlit as st

# Konfigurasi halaman
st.set_page_config(
    page_title="Ular Tangga Multiplayer (Max 4 Orang)", page_icon="🎲", layout="centered"
)

# Definisi Peta Ular dan Tangga (Papan 30 Kotak agar seru dan cepat)
# Kunci = posisi awal, Nilai = posisi tujuan (Positif = Tangga, Negatif = Ular)
SNAKES_AND_LADDERS = {
    3: 11,  # Tangga
    6: 17,  # Tangga
    9: 1,  # Ular turun ke 1
    14: 4,  # Ular turun ke 4
    20: 25,  # Tangga
    22: 16,  # Ular turun ke 16
    26: 28,  # Tangga
    29: 12,  # Ular turun ke 12
}

MAX_BOARD = 30  # Bisa diubah ke 100 jika ingin papan penuh

# Inisialisasi State Permainan
if "game_started" not in st.session_state:
  st.session_state.game_started = False
if "players" not in st.session_state:
  st.session_state.players = []
if "positions" not in st.session_state:
  st.session_state.positions = {}
if "current_turn" not in st.session_state:
  st.session_state.current_turn = 0
if "dice_roll" not in st.session_state:
  st.session_state.dice_roll = None
if "message" not in st.session_state:
  st.session_state.message = ""
if "winner" not in st.session_state:
  st.session_state.winner = None


def reset_game():
  st.session_state.game_started = False
  st.session_state.players = []
  st.session_state.positions = {}
  st.session_state.current_turn = 0
  st.session_state.dice_roll = None
  st.session_state.message = ""
  st.session_state.winner = None


# Antarmuka Utama
st.title("🎲 Ular Tangga Mini (1–4 Pemain)")
st.write(
    "Permainan papan klasik Ular Tangga interaktif berbasis web menggunakan"
    " Streamlit."
)

# --- TAHAP 1: SETUP PEMAIN ---
if not st.session_state.game_started:
  st.subheader("Pengaturan Pemain")
  num_players = st.selectbox(
      "Pilih Jumlah Pemain:", [1, 2, 3, 4], index=1
  )

  player_names = []
  for i in range(num_players):
    name = st.text_input(f"Nama Pemain {i+1}", value=f"Player {i+1}")
    player_names.append(name if name else f"Player {i+1}")

  if st.button("Mulai Permainan! 🚀", type="primary"):
    if len(set(player_names)) < len(player_names):
      st.error("Nama pemain tidak boleh sama!")
    else:
      st.session_state.players = player_names
      # Semua pemain mulai dari kotak 0
      st.session_state.positions = {p: 0 for p in player_names}
      st.session_state.current_turn = 0
      st.session_state.game_started = True
      st.session_state.winner = None
      st.session_state.message = (
          f"Permainan dimulai! Giliran pertama: {player_names[0]}"
      )
      st.rerun()

# --- TAHAP 2: ARENA PERMAINAN ---
else:
  players = st.session_state.players
  current_player = players[st.session_state.current_turn]

  # Tampilkan Status Posisi Terkini
  st.markdown("### 📊 Papan Skor / Posisi Pion")
  cols = st.columns(len(players))
  colors = ["🔴", "🔵", "🟢", "🟡"]

  for idx, player in enumerate(players):
    pos = st.session_state.positions[player]
    with cols[idx]:
      st.metric(
          label=f"{colors[idx]} {player}",
          value=f"Kotak {pos}",
          delta=(
              "Finis!" if pos == MAX_BOARD else f"Target: Kotak {MAX_BOARD}"
          ),
      )

  st.divider()

  # Cek Apakah Ada Pemenang
  if st.session_state.winner:
    st.success(
        f"🎉 SELAMAT! **{st.session_state.winner}** memenangkan permainan!"
        f" 🏆"
    )
    if st.button("🔄 Main Lagi / Reset Game"):
      reset_game()
      st.rerun()
  else:
    # Area Lempar Dadu
    st.info(
        f"🎯 Giliran Bermain: **{current_player}**"
        f" {colors[st.session_state.current_turn]}"
    )

    if st.button("🎲 Lempar Dadu!", type="primary", use_container_width=True):
      # Kocok dadu 1-6
      roll = random.randint(1, 6)
      st.session_state.dice_roll = roll

      old_pos = st.session_state.positions[current_player]
      new_pos = old_pos + roll

      msg = f"{current_player} melempar angka **{roll}**."

      # Cek batas maksimum papan
      if new_pos > MAX_BOARD:
        # Sistem pantul jika kelebihan langkah
        new_pos = MAX_BOARD - (new_pos - MAX_BOARD)
        msg += (
            f" Melebihi kotak {MAX_BOARD}, pion memantul mundur ke"
            f" kotak {new_pos}!"
        )

      # Cek Ular atau Tangga
      if new_pos in SNAKES_AND_LADDERS:
        tujuan = SNAKES_AND_LADDERS[new_pos]
        if tujuan > new_pos:
          msg += f" 🪜 Hore! Menemukan **Tangga** naik ke kotak {tujuan}!"
        else:
          msg += f" 🐍 Oh tidak! Terkena **Ular** turun ke kotak {tujuan}!"
        new_pos = tujuan

      # Update posisi pemain
      st.session_state.positions[current_player] = new_pos
      st.session_state.message = msg

      # Cek Kondisi Menang
      if new_pos == MAX_BOARD:
        st.session_state.winner = current_player
      else:
        # Pindah ke giliran pemain berikutnya
        st.session_state.current_turn = (
            st.session_state.current_turn + 1
        ) % len(players)

      st.rerun()

    # Tampilkan Pesan Aksi Terakhir
    if st.session_state.message:
      st.write(st.session_state.message)

    st.divider()
    if st.button("Reset / Keluar Permainan"):
      reset_game()
      st.rerun()

  # Visualisasi Mini Papan Grid Sederhana
  st.subheader("🗺️ Visualisasi Jalur Papan (1 sampai 30)")
  board_cols = st.columns(6)
  # Tampilkan kotak dari 30 turun ke 1 atau sebaliknya
  for i in range(MAX_BOARD, 0, -1):
    col_idx = (MAX_BOARD - i) % 6
    with board_cols[col_idx]:
      # Cari siapa saja yang ada di kotak ini
      occupants = [
          p
          for p, pos in st.session_state.positions.items()
          if pos == i
      ]
      occ_str = " ".join([f"({p[:3]})" for p in occupants])
      if i in SNAKES_AND_LADDERS:
        dest = SNAKES_AND_LADDERS[i]
        icon = "🪜" if dest > i else "🐍"
        st.markdown(
            f"**[{i}]** {icon}\n{occ_str}"
            if occ_str
            else f"**[{i}]** {icon}"
        )
      else:
        st.markdown(f"**[{i}]**\n{occ_str}" if occ_str else f"**[{i}]**")
